# Setup Guide

## 0. The repo itself
This has to live in a repo named **exactly** `YashRaut24/YashRaut24` — that's
the special repo GitHub renders on your profile page. If you haven't made it
yet: create a new **public** repo called `YashRaut24`, then drop everything
from this folder (`README.md`, `assets/`, `.github/`) into it and push to
`main`.

```bash
git init
git add .
git commit -m "Set up profile README"
git branch -M main
git remote add origin https://github.com/YashRaut24/YashRaut24.git
git push -u origin main
```

## 1. Pac-Man contribution graph (works out of the box)
`.github/workflows/pacman.yml` needs nothing extra — it uses the default
`GITHUB_TOKEN` GitHub already provides. After your first push to `main`:

1. Go to the **Actions** tab → you should see "generate pacman contribution
   graph" running (or run it manually via **Run workflow**).
2. It creates/updates an `output` branch with the generated SVGs.
3. Within a few minutes, the Pac-Man section in your README will go live.
4. It also re-runs automatically every 24 hours to reflect new commits.

If it 404s after running once, double check the repo is **public** — private
repos need `github_token` with extra scopes, public ones don't.

## 2. GitHub Metrics (`metrics.yml`) — needs one secret
The default token can't pull cross-repo/profile-level stats, so:

1. Create a **Personal Access Token**: GitHub → Settings → Developer settings
   → Personal access tokens → generate new (classic) → scopes: `repo`,
   `read:user`.
2. In your `YashRaut24/YashRaut24` repo → Settings → Secrets and variables →
   Actions → **New repository secret**:
   - Name: `METRICS_TOKEN`
   - Value: the token you just generated
3. Run the workflow manually once (Actions tab → "generate github metrics" →
   Run workflow) to confirm it works, then let the schedule take over.
4. Optional: add `<img src="./metrics.svg" width="100%" />` to the README
   once it's generated, if you want it visible (it's scaffolded but not
   wired into the README by default, since it can get busy alongside the
   other stat widgets — your call).

## 3. WakaTime stats (`wakatime.yml`) — needs two secrets
Only do this if you actually want live coding-time stats:

1. Make a free account at [wakatime.com](https://wakatime.com/).
2. Install the WakaTime plugin for your editor (VS Code, JetBrains, etc.) and
   log in — it starts tracking automatically in the background.
3. Copy your API key from wakatime.com/settings/api-key.
4. Add two repo secrets (same path as above):
   - `WAKATIME_API_KEY` → the key from step 3
   - `GH_TOKEN` → same PAT you made for metrics (needs `repo` scope so the
     action can commit the updated README back)
5. Run the workflow once manually. It'll rewrite the block between
   `<!--START_SECTION:waka-->` and `<!--END_SECTION:waka-->` in `README.md`.
6. Give it a day or two of actual coding before the numbers look meaningful.

## 4. Widgets that just work (zero setup)
These all read your **public** username directly, no token needed:
- `github-readme-stats` (main stats card)
- `github-readme-streak-stats`
- `github-readme-activity-graph`
- `github-profile-trophy`
- `komarev` visitor badge

If any of them ever go down (they occasionally rate-limit or have outages),
that's on the widget's side, not your repo — check the linked project's
GitHub issues page.

## 5. Swapping colors
Every stat-widget URL in `README.md` has color params in the query string
(`bg_color`, `title_color`, `text_color`, `icon_color`, `border_color`, etc.)
— all hex, no `#`. Palette used throughout:
- Background: `000000`
- Text: `FFFFFF`
- Accent: `FFD400`

Change those three values consistently across every widget URL and the whole
profile re-themes in one pass.
