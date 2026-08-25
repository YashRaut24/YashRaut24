# Setup Guide // Linear / Vercel Minimalist Profile

## 0. The Repository
This profile README lives in a repository named **exactly** `YashRaut24/YashRaut24` — the special repository GitHub renders on your profile page.

```bash
git init
git add .
git commit -m "feat: ultra-minimalist linear vercel profile"
git branch -M main
git remote add origin https://github.com/YashRaut24/YashRaut24.git
git push -u origin main
```

## 1. Snake Contribution Graph (`snake.yml`)
`.github/workflows/snake.yml` generates the animated snake contribution matrix.

1. Go to the **Actions** tab in your repository.
2. Select **generate snake contribution graph** → click **Run workflow**.
3. It will generate the SVG files and push them to the `output` branch. Once it finishes (takes ~30 seconds), the snake animation in your README goes live!
4. It re-runs automatically twice a day.

## 2. GitHub Metrics (`metrics.yml`)
1. Create a **Personal Access Token (Classic)**: GitHub → Settings → Developer Settings → Personal access tokens → Generate new (classic) with `repo` and `read:user` scopes.
2. In your `YashRaut24/YashRaut24` repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - Name: `METRICS_TOKEN`
   - Value: `<your-token>`
3. Run the workflow manually once from the Actions tab.

## 3. WakaTime Coding Stats (`wakatime.yml`)
1. Sign up at [wakatime.com](https://wakatime.com/) and install the plugin for your editor.
2. Copy your Secret API Key from [wakatime.com/settings/api-key](https://wakatime.com/settings/api-key).
3. Add two repository secrets:
   - `WAKATIME_API_KEY`: your WakaTime API key
   - `GH_TOKEN`: Personal Access Token with `repo` scope
4. Run the workflow once manually. It will update the block between `<!--START_SECTION:waka-->` and `<!--END_SECTION:waka-->`.

## 4. Design System Specifications
All SVGs and remote stat widgets are calibrated to a zero-gradient, zero-glow Linear/Vercel palette:
- **Base Canvas**: `#08090A` (Deep Obsidian Slate)
- **Bento Tiles**: `#0F1115` with 1px border (`#1F242C`)
- **Primary Accent**: `#5E6AD2` (Linear Indigo)
- **Primary Text**: `#F7F8F8` (Crisp Optical White)
- **Secondary Text**: `#8A8F98` (Muted Slate)
- **Status Dot**: `#10B981` (Emerald)
