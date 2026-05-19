"""
fetch_antares.py — runs in GitHub Actions, writes JSON to /data/

Usage (called by workflows):
    python scripts/fetch_antares.py --tier sp500
    python scripts/fetch_antares.py --tier russell3000
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


# ----- UNIVERSE BUILDERS -----

def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    tickers = [t.replace(".", "-") for t in df["Symbol"].tolist()]
    sectors = dict(zip(tickers, df["GICS Sector"].tolist()))
    print(f"[universe] S&P 500: {len(tickers)} tickers")
    return tickers, sectors


def get_russell3000():
    universe = set()
    sectors = {}
    sources = [
        ("S&P 500", "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 0, "Symbol", "GICS Sector"),
        ("S&P 400", "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies", 0, "Symbol", "GICS Sector"),
        ("S&P 600", "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies", 0, "Symbol", "GICS Sector"),
        ("NASDAQ-100", "https://en.wikipedia.org/wiki/Nasdaq-100", 4, "Symbol", "GICS Sector"),
    ]
    for name, url, idx, sym, sec in sources:
        try:
            df = pd.read_html(url)[idx]
            scol = sym if sym in df.columns else "Ticker"
            tks = [str(t).replace(".", "-") for t in df[scol].tolist()]
            for t in tks:
                universe.add(t)
            if sec in df.columns:
                for t, s in zip(tks, df[sec].tolist()):
                    sectors[t] = s
            print(f"[universe] {name}: +{len(tks)}")
        except Exception as e:
            print(f"[universe] {name} failed: {e}")
    tickers = sorted(universe)
    print(f"[universe] Combined: {len(tickers)} unique tickers")
    return tickers, sectors


# ----- METRIC HELPERS -----

def calc_relative_strength(stock_hist, spy_hist):
    if stock_hist is None or spy_hist is None or len(stock_hist) < 20 or len(spy_hist) < 20:
        return 50
    try:
        s_ret = (stock_hist["Close"].iloc[-1] / stock_hist["Close"].iloc[0]) - 1
        m_ret = (spy_hist["Close"].iloc[-1] / spy_hist["Close"].iloc[0]) - 1
        excess = s_ret - m_ret
        score = 50 + (excess * 100 / 0.6 * 50)
        return max(0, min(100, round(score)))
    except Exception:
        return 50


def calc_return_pct(hist, days):
    if hist is None or len(hist) < days + 1:
        return None
    try:
        last = hist["Close"].iloc[-1]
        prior = hist["Close"].iloc[-days - 1]
        return round(((last / prior) - 1) * 100, 1)
    except Exception:
        return None


def calc_pct_from_52high(hist):
    if hist is None or len(hist) < 20:
        return None
    try:
        return round(((hist["High"].max() - hist["Close"].iloc[-1]) / hist["High"].max()) * 100, 1)
    except Exception:
        return None


def calc_price_vs_200dma(hist):
    if hist is None or len(hist) < 200:
        return None
    try:
        dma = hist["Close"].rolling(200).mean().iloc[-1]
        return round(((hist["Close"].iloc[-1] - dma) / dma) * 100, 1)
    except Exception:
        return None


def calc_atr_pct(hist, period=14):
    if hist is None or len(hist) < period + 1:
        return None
    try:
        hl = hist["High"] - hist["Low"]
        hc = (hist["High"] - hist["Close"].shift()).abs()
        lc = (hist["Low"] - hist["Close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return round((atr / hist["Close"].iloc[-1]) * 100, 2)
    except Exception:
        return None


def calc_volume_surge(hist, lookback=50):
    if hist is None or len(hist) < lookback + 1 or "Volume" not in hist.columns:
        return None
    try:
        avg = hist["Volume"].iloc[-lookback - 1:-1].mean()
        return round(hist["Volume"].iloc[-1] / avg, 2) if avg > 0 else None
    except Exception:
        return None


def calc_avg_dollar_volume(hist, lookback=20):
    if hist is None or len(hist) < lookback or "Volume" not in hist.columns:
        return None
    try:
        dv = (hist["Volume"].iloc[-lookback:] * hist["Close"].iloc[-lookback:]).mean()
        return round(dv / 1e6, 1)
    except Exception:
        return None


def calc_rev_acceleration(ticker_obj):
    try:
        qf = ticker_obj.quarterly_financials
        if qf is None or qf.empty or "Total Revenue" not in qf.index:
            return None
        rev = qf.loc["Total Revenue"].dropna()
        if len(rev) < 3:
            return None
        latest, prev, prev_prev = rev.iloc[0], rev.iloc[1], rev.iloc[2]
        if prev <= 0 or prev_prev <= 0:
            return None
        return round(((latest / prev - 1) - (prev / prev_prev - 1)) * 100, 1)
    except Exception:
        return None


def fetch_one(ticker, sector_map, spy_hist):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            return None
        hist = t.history(period="1y", auto_adjust=True)
        if hist.empty:
            return None
        mcap = info.get("marketCap")
        pe = info.get("trailingPE")
        rg = info.get("revenueGrowth")
        eg = info.get("earningsGrowth")
        nm = info.get("profitMargins")
        fcf = info.get("freeCashflow")
        de = info.get("debtToEquity")
        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": sector_map.get(ticker) or info.get("sector") or "Unknown",
            "price": round(price, 2),
            "marketCap": round(mcap / 1e9, 2) if mcap else None,
            "peRatio": round(pe, 1) if pe else None,
            "revGrowth": round(rg * 100, 1) if rg is not None else None,
            "epsGrowth": round(eg * 100, 1) if eg is not None else None,
            "netMargin": round(nm * 100, 1) if nm is not None else None,
            "fcfYield": round((fcf / mcap) * 100, 2) if fcf and mcap else None,
            "debtToEquity": round(de / 100, 2) if de else None,
            "relStrength": calc_relative_strength(hist, spy_hist),
            "pctFrom52High": calc_pct_from_52high(hist),
            "priceVs200dma": calc_price_vs_200dma(hist),
            "atrPct": calc_atr_pct(hist),
            "return1m": calc_return_pct(hist, 21),
            "return3m": calc_return_pct(hist, 63),
            "volumeSurge": calc_volume_surge(hist),
            "avgDollarVolume": calc_avg_dollar_volume(hist),
            "revAccel": calc_rev_acceleration(t),
        }
    except Exception as e:
        print(f"  [skip] {ticker}: {type(e).__name__}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["sp500", "russell3000"], default="sp500")
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    print(f"[start] {datetime.now(timezone.utc).isoformat(timespec='seconds')}")

    if args.tier == "russell3000":
        tickers, sectors = get_russell3000()
    else:
        tickers, sectors = get_sp500()
    if args.limit:
        tickers = tickers[: args.limit]

    print("[benchmark] Fetching SPY...")
    try:
        spy = yf.Ticker("SPY").history(period="6mo", auto_adjust=True)
    except Exception:
        spy = None

    print(f"[fetch] {len(tickers)} tickers, {args.max_workers} workers")
    results = []
    start = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futs = {pool.submit(fetch_one, t, sectors, spy): t for t in tickers}
        for fut in as_completed(futs):
            done += 1
            r = fut.result()
            if r:
                results.append(r)
            if done % 50 == 0:
                elapsed = time.time() - start
                rate = done / elapsed
                eta = (len(tickers) - done) / rate
                print(f"  {done}/{len(tickers)} ({rate:.1f}/s, ETA {eta:.0f}s, kept {len(results)})")

    print(f"[done] {len(results)}/{len(tickers)} in {time.time() - start:.1f}s")

    results.sort(key=lambda r: r["ticker"])
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"antares-{args.tier}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"[write] {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
