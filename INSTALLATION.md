# Setup Guide

## 0. The Repository
This profile README lives in a repository named **exactly** `YashRaut24/YashRaut24` — the special repository GitHub renders on your profile page.

```bash
git init
git add .
git commit -m "feat: modern flat aesthetic profile upgrade"
git branch -M main
git remote add origin https://github.com/YashRaut24/YashRaut24.git
git push -u origin main
```

## 1. Snake Contribution Graph (`snake.yml`)
`.github/workflows/snake.yml` runs automatically using the standard `GITHUB_TOKEN`. After your first push to `main`:

1. Go to the **Actions** tab → select **generate snake contribution graph** → click **Run workflow**.
2. It generates the light and dark snake animations and commits them to the `output` branch.
3. Your README's `<picture>` element will automatically display the live animated graph matching the viewer's theme.
4. The workflow is scheduled to re-run automatically twice a day.

## 2. GitHub Metrics (`metrics.yml`)
1. Create a **Personal Access Token (Classic)**: GitHub → Settings → Developer Settings → Personal access tokens → Generate new (classic) with `repo` and `read:user` scopes.
2. In your `YashRaut24/YashRaut24` repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - Name: `METRICS_TOKEN`
   - Value: `<your-token>`
3. Run the workflow manually once from the Actions tab.

## 3. WakaTime Coding Stats (`wakatime.yml`)
1. Sign up at [wakatime.com](https://wakatime.com/) and install the plugin for your editor (VS Code, JetBrains, etc.).
2. Copy your Secret API Key from [wakatime.com/settings/api-key](https://wakatime.com/settings/api-key).
3. Add two repository secrets:
   - `WAKATIME_API_KEY`: your WakaTime API key
   - `GH_TOKEN`: Personal Access Token with `repo` scope
4. Run the workflow once manually. It will update the block between `<!--START_SECTION:waka-->` and `<!--END_SECTION:waka-->`.

## 4. Flat Design System &amp; Palette
All SVGs and remote stat widgets are calibrated to a zero-gradient, zero-glow flat palette:
- **Base Background**: `#0B0F17` (Deep Obsidian Matte)
- **Card Background**: `#111726`
- **Border**: `#232D3F`
- **Primary Accent**: `#38BDF8` (Sky Cyan)
- **Primary Text**: `#F8FAFC`
- **Muted Text**: `#94A3B8`
- **Status Dot**: `#10B981` (Emerald)
