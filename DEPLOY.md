# Antares — Live Deploy Guide

End-to-end setup: from these files to a live website at your own domain with auto-refreshing data. Total time: ~45 minutes, one-time.

## What you're building

```
┌────────────────────────────────────────────────────────────────┐
│  GITHUB (private repo)                                         │
│                                                                │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ GitHub Actions  │───▶│ data/antares-sp500.json          │   │
│  │ (free, schedul.)│    │ data/antares-russell3000.json    │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│         │                          │                           │
│         │ runs nightly/weekly      │ auto-published to:        │
│         ▼                          ▼                           │
│  scripts/fetch_antares.py    GitHub Pages (public URL)         │
└────────────────────────────────────────────────────────────────┘
                                     │
                                     │ fetched on page load
                                     ▼
┌────────────────────────────────────────────────────────────────┐
│  NETLIFY (your domain)                                         │
│  index.html ──── live dashboard, auto-refreshes data ────────  │
└────────────────────────────────────────────────────────────────┘
```

You pay nothing. GitHub Actions has 2,000 free minutes/month — daily fetches use ~15.

---

## Project files

```
antares-project/
├── index.html                          # the dashboard (drag to Netlify)
├── scripts/
│   └── fetch_antares.py                # data fetcher (runs in GitHub Actions)
├── .github/
│   └── workflows/
│       ├── fetch-sp500.yml             # daily 6pm ET
│       ├── fetch-russell3000.yml       # weekly Saturday 4am ET
│       └── publish-pages.yml           # auto-publishes JSON
├── data/                               # auto-populated by Actions
├── .gitignore
└── DEPLOY.md                           # this file
```

---

# Part 1 — Create the GitHub repo (5 min)

1. Go to **github.com/new**
2. Repo name: `antares` (or whatever you want)
3. Set to **Private**
4. Don't initialize with README — we'll push our files in.
5. Click **Create repository**

GitHub shows you push instructions. Keep that page open; you'll need the URL.

---

# Part 2 — Push the code (5 min)

1. Download the `antares-project` folder to your computer (likely already on your Desktop).
2. Open Terminal (Mac) or Command Prompt (Windows).
3. Navigate to the folder:

   **Mac:** `cd ~/Desktop/antares-project`
   **Windows:** `cd %USERPROFILE%\Desktop\antares-project`

4. Initialize git and push (replace `YOURUSERNAME` and `antares`):

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOURUSERNAME/antares.git
git push -u origin main
```

If git asks you to log in, GitHub will guide you through it the first time (probably wants a Personal Access Token — there's a link in the error message).

Refresh your GitHub repo page. You should see all the files.

---

# Part 3 — Enable GitHub Pages (3 min)

This is what makes your JSON publicly accessible to the Netlify-hosted dashboard.

1. On your repo, click **Settings** (top tabs)
2. Left sidebar → **Pages**
3. Under "Build and deployment", set **Source** to **GitHub Actions**
4. Save (it may save automatically)

That's it. The first time the `publish-pages.yml` workflow runs, it'll create your URL.

---

# Part 4 — Run the first fetch manually (10 min)

You don't want to wait until 6pm for the cron — let's trigger one now.

1. Go to your repo → **Actions** tab
2. You should see three workflows in the left sidebar. Click **Fetch S&P 500 (Daily)**
3. Right side: click **Run workflow** → **Run workflow** (confirms with default settings)
4. Wait 4–6 minutes. The workflow runs, fetches data, and commits `data/antares-sp500.json` to your repo.
5. When it goes green ✓, click **Publish Data to GitHub Pages** in the sidebar — it should have auto-triggered from the commit. Wait for it to finish too.

Then run **Fetch Russell 3000 (Weekly)** the same way. This one takes 25–35 minutes — go do something else.

**To find your data URL:**
1. Settings → Pages → look at the URL at the top: `https://YOURUSERNAME.github.io/antares/`
2. Your data files are at:
   - `https://YOURUSERNAME.github.io/antares/antares-sp500.json`
   - `https://YOURUSERNAME.github.io/antares/antares-russell3000.json`

Open one in your browser — you should see a wall of JSON. That means it's working.

---

# Part 5 — Wire the dashboard to your data (3 min)

1. On your computer, open `index.html` in any text editor (TextEdit, Notepad, VS Code — anything)
2. Find these two lines near the top of the `<script>` block:

   ```javascript
   DATA_URL_SP500: 'https://YOURUSERNAME.github.io/antares-data/antares-sp500.json',
   DATA_URL_R3K: 'https://YOURUSERNAME.github.io/antares-data/antares-russell3000.json',
   ```

3. Replace `YOURUSERNAME` with your GitHub username, and `antares-data` with your actual repo name (probably `antares`). Final result looks like:

   ```javascript
   DATA_URL_SP500: 'https://janedoe.github.io/antares/antares-sp500.json',
   DATA_URL_R3K: 'https://janedoe.github.io/antares/antares-russell3000.json',
   ```

4. Save the file.

---

# Part 6 — Deploy to Netlify (5 min)

1. Go to **netlify.com**, sign up (use your GitHub account for one-click signup)
2. On the Netlify dashboard, drag-and-drop your `index.html` file onto the page. **That's literally it.**
3. Netlify gives you a random URL like `https://elegant-curie-abc123.netlify.app`. Open it. Your dashboard should appear with **real data** auto-loaded from GitHub Pages.

If you only see the seed data (12 tickers), the data URL isn't correct in `index.html` — recheck Part 5.

---

# Part 7 — Connect your custom domain (5 min)

1. Netlify dashboard → click your site
2. **Domain management** → **Add a domain**
3. Type your domain (e.g., `antares.yourname.com` or `yourname.com`)
4. Netlify shows DNS records you need to add at your domain registrar (GoDaddy, Namecheap, Google Domains, etc.)
5. Log into your registrar, add the CNAME / A records as Netlify instructs
6. Wait 5–60 minutes for DNS to propagate. Netlify auto-provisions a free SSL certificate.

Your dashboard is now live at your domain, with auto-refreshing data.

---

# Part 8 — Verify the schedule is running (2 min)

Go to your repo → Settings → **Actions** → **General** → confirm "Allow all actions" is checked.

Then back to **Actions** tab and check that the workflows are listed with future schedule indicators.

**Important**: GitHub disables Actions schedules on repos with no activity for 60 days. As long as you push commits occasionally (or anyone visits the repo's API), it stays active.

---

# Maintenance

## If yfinance breaks

GitHub Actions will email you when a workflow fails. To fix:

1. Edit `scripts/fetch_antares.py`
2. The fix is usually just updating yfinance — change nothing in the script, but Actions installs the latest yfinance every run anyway. So if it's broken globally, just wait a day or two for the maintainers to push an update.
3. Or pin a specific version: edit the `.github/workflows/fetch-*.yml` files and change `pip install yfinance` to `pip install yfinance==0.2.40` (or whatever version is known-good).

## Manual re-fetch anytime

GitHub repo → Actions → pick a workflow → "Run workflow" button. Useful if you want fresh data right before market open.

## Updating the dashboard later

Edit `index.html` on your computer → drag onto Netlify again. Done. Or set up Netlify to auto-deploy from your GitHub repo (Site settings → Build & deploy → link to repo).

---

# Daily workflow (after setup)

1. Open your dashboard URL on your phone or computer
2. Data is already fresh (auto-fetched on page load)
3. Filter to **BUY** in Screener mode
4. Click top 3–5 candidates, review trade plans
5. For more aggressive picks: switch to **Rocket Mode**, look at IGNITE signals
6. Verify each pick on **stockanalysis.com** before trading
7. Place orders: limit buy, stop-loss, optional target sell

That's it. No more importing JSON files. No more manual fetches.

---

# Troubleshooting

| Problem | Solution |
|---|---|
| Dashboard shows "Configure DATA_URL" warning | You didn't update the URLs in `index.html` — see Part 5 |
| Dashboard shows "Using seed data" with an HTTP error | GitHub Pages not enabled, or wrong URL. Try opening the URL in your browser directly. |
| GitHub Action failed | Click the failed run → read the logs. Most common: yfinance temporarily failing on too many tickers. Re-run the workflow. |
| Pages URL returns 404 | First-time setup takes 2–3 minutes. If it persists, ensure GitHub Pages is set to "GitHub Actions" source (Part 3). |
| Schedule stopped working | Push any commit to wake up the repo (edit README, push). GitHub auto-suspends after 60 days inactivity. |
| Netlify domain not working | DNS propagation can take up to 24 hours. Use `dnschecker.org` to verify your records are live. |

---

# Cost summary

| Service | Cost |
|---|---|
| GitHub (private repo) | Free |
| GitHub Actions (2,000 min/mo) | Free — we use ~30 min/mo |
| GitHub Pages | Free |
| Netlify static hosting | Free |
| SSL certificate | Free (Netlify auto-provisions) |
| **Total** | **$0/month** |

The only thing you pay for is your domain (~$12/year from any registrar).

---

# A final note

Not financial advice. The tool screens; it doesn't predict. Rocket Mode is intentionally aggressive and will produce losing trades. Diversify, size positions properly (1–2% account risk per trade), never invest money you need within 6 months.

Run the screener, but think for yourself.
