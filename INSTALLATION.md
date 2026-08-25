# Setup Guide // Cyber-Architect Profile

## 0. The Repository
This profile README lives in a repository named **exactly** `YashRaut24/YashRaut24` — the special repository GitHub renders on your profile page.

```bash
git init
git add .
git commit -m "feat: cyber-architect bento profile upgrade"
git branch -M main
git remote add origin https://github.com/YashRaut24/YashRaut24.git
git push -u origin main
```

## 1. 3D Isometric Contribution City Graph (`profile-3d.yml`)
`.github/workflows/profile-3d.yml` uses GitHub's built-in `GITHUB_TOKEN` to generate the 3D isometric city graph of your contributions.

1. Go to the **Actions** tab in your repo.
2. Select **generate-github-profile-3d-contrib** → click **Run workflow**.
3. It will generate `profile-3d-contrib/profile-night-rainbow.svg` directly in your repo.
4. It is scheduled to re-run automatically every day at 18:00 UTC.

## 2. Snake Contribution Graph (`snake.yml`)
`.github/workflows/snake.yml` runs automatically using `GITHUB_TOKEN`.
1. Go to the **Actions** tab → select **generate snake contribution graph** → click **Run workflow**.
2. It generates light & dark snake animations and commits them to the `output` branch.
3. It re-runs automatically twice a day.

## 3. GitHub Metrics (`metrics.yml`)
1. Create a **Personal Access Token (Classic)**: GitHub → Settings → Developer Settings → Personal access tokens → Generate new (classic) with `repo` and `read:user` scopes.
2. In your `YashRaut24/YashRaut24` repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - Name: `METRICS_TOKEN`
   - Value: `<your-token>`
3. Run the workflow manually once from the Actions tab.

## 4. WakaTime Coding Stats (`wakatime.yml`)
1. Sign up at [wakatime.com](https://wakatime.com/) and install the plugin for your editor.
2. Copy your Secret API Key from [wakatime.com/settings/api-key](https://wakatime.com/settings/api-key).
3. Add two repository secrets:
   - `WAKATIME_API_KEY`: your WakaTime API key
   - `GH_TOKEN`: Personal Access Token with `repo` scope
4. Run the workflow once manually. It will update the block between `<!--START_SECTION:waka-->` and `<!--END_SECTION:waka-->`.

## 5. Design System Specifications
All custom SVGs and remote widgets are calibrated to a zero-gradient, zero-glow flat Cyber-Architect palette:
- **Base Background**: `#0B0F17` (Deep Obsidian Matte)
- **Bento Card Surface**: `#111726`
- **Architectural Border**: `#232D3F` / `#1E293B`
- **Primary Accent**: `#38BDF8` (Sky Cyan)
- **Neural/AI Accent**: `#818CF8` (Indigo)
- **Success/Live Dot**: `#10B981` (Emerald)
- **Primary Text**: `#F8FAFC`
- **Muted Text**: `#94A3B8`
