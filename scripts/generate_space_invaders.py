#!/usr/bin/env python3
import urllib.request
import json
import re
import os
import datetime
import time

USERNAME = "YashRaut24"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_contributions(username, token=""):
    """
    Fetch real GitHub contributions calendar and last-year total contributions for user.
    Priority 1: Community contributions API endpoint (accurate rolling last year with private/public total)
    Priority 2: GitHub GraphQL API (if token provided)
    Priority 3: GitHub HTML contributions endpoint
    """
    # 1. Primary: Real last-year contributions API
    try:
        url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
        req = urllib.request.Request(url, headers={"User-Agent": "Space-Invaders-Generator"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
            raw_contribs = data.get("contributions", [])
            total_last_year = data.get("total", {}).get("lastYear", 0)
            
            records = {}
            for item in raw_contribs:
                d_str = item["date"]
                cnt = item.get("count", 0)
                lvl = item.get("level", 0)
                records[d_str] = {
                    "date": d_str,
                    "contributions": cnt,
                    "level": lvl,
                    "initial_level": lvl
                }
            
            sum_total = sum(r["contributions"] for r in records.values())
            total_contribs = total_last_year if total_last_year > 0 else sum_total
            if records and total_contribs > 0:
                print(f"Fetched {len(records)} days via Primary Contributions API. Total last-year contributions: {total_contribs}")
                return records, total_contribs
    except Exception as e:
        print(f"Primary API fetch failed: {e}. Trying GraphQL API...")

    # 2. GraphQL API (if token present)
    if token:
        try:
            cal_query = """
            query($username: String!) {
              user(login: $username) {
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
                    weeks {
                      contributionDays {
                        date
                        contributionCount
                        contributionLevel
                      }
                    }
                  }
                  totalCommitContributions
                  restrictedContributionsCount
                }
              }
            }
            """
            req_data = json.dumps({"query": cal_query, "variables": {"username": username}}).encode('utf-8')
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Space-Invaders-Generator",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                col = res["data"]["user"]["contributionsCollection"]
                calendar = col["contributionCalendar"]
                level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
                records = {}
                for week in calendar["weeks"]:
                    for day in week["contributionDays"]:
                        lvl = level_map.get(day["contributionLevel"], 0)
                        cnt = int(day.get("contributionCount", 0))
                        d_str = day["date"]
                        records[d_str] = {
                            "date": d_str,
                            "contributions": cnt,
                            "level": lvl,
                            "initial_level": lvl
                        }
                
                cal_total = int(calendar.get("totalContributions", 0))
                sum_total = sum(r["contributions"] for r in records.values())
                total_contribs = cal_total if cal_total > 0 else sum_total
                if records and total_contribs > 0:
                    print(f"Fetched {len(records)} days via GitHub GraphQL API. Total: {total_contribs}")
                    return records, total_contribs
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Falling back to calendar endpoint...")

    # 3. Fallback to contributions calendar endpoint
    try:
        url = f"https://github.com/users/{username}/contributions?_={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
        
        tooltips = {}
        for match in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', html, re.DOTALL):
            tooltips[match.group(1)] = match.group(2).strip()
        
        records = {}
        day_matches = re.finditer(r'<td[^>]*data-date="([^"]+)"[^>]*>', html)
        for m in day_matches:
            td_tag = m.group(0)
            date_m = re.search(r'data-date="([^"]+)"', td_tag)
            level_m = re.search(r'data-level="([^"]+)"', td_tag)
            id_m = re.search(r'id="([^"]+)"', td_tag)
            if date_m:
                date_val = date_m.group(1)
                level_val = int(level_m.group(1)) if level_m else 0
                comp_id = id_m.group(1) if id_m else ""
                tt_text = tooltips.get(comp_id, "")
                cnt_m = re.search(r'(\d+)\s+contribution', tt_text)
                cnt_val = int(cnt_m.group(1)) if cnt_m else 0
                records[date_val] = {
                    "date": date_val,
                    "contributions": cnt_val,
                    "level": level_val,
                    "initial_level": level_val
                }
        
        h2_m = re.search(r'([0-9,]+)\s+contributions?\s+in', html)
        h2_total = int(h2_m.group(1).replace(",", "")) if h2_m else 0
        sum_total = sum(r["contributions"] for r in records.values())
        
        total_contribs = h2_total if h2_total > 0 else sum_total
        print(f"Fetched {len(records)} dates from GitHub HTML endpoint. Total: {total_contribs}")
        return records, total_contribs
    except Exception as e:
        print(f"Calendar fetch failed: {e}")
        return {}, 0

def sync_other_svgs(total_contribs):
    """
    Keep assets/space-portal-stats.svg and assets/space-portal-telemetry.svg in sync with total_contribs.
    """
    if total_contribs <= 0:
        return
    formatted_total = f"{total_contribs:,}"
    
    # Update space-portal-stats.svg
    stats_path = "assets/space-portal-stats.svg"
    if os.path.exists(stats_path):
        with open(stats_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'<text x="0" y="0" text-anchor="middle" class="num-val">[0-9,]+</text>',
                         f'<text x="0" y="0" text-anchor="middle" class="num-val">{formatted_total}</text>', content)
        with open(stats_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Synced {stats_path} with {formatted_total}")

    # Update space-portal-telemetry.svg
    telemetry_path = "assets/space-portal-telemetry.svg"
    if os.path.exists(telemetry_path):
        with open(telemetry_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'<text x="14" y="42" class="metric-val">[0-9,]+ COMMITS</text>',
                         f'<text x="14" y="42" class="metric-val">{formatted_total} COMMITS</text>', content)
        with open(telemetry_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Synced {telemetry_path} with {formatted_total} COMMITS")

def generate_svg(date_records, total_contribs, output_path="assets/space-invaders-commits.svg"):
    """Generate a compact, browser-friendly arcade SVG from real GitHub data."""
    if not date_records:
        raise ValueError("No contribution records provided")

    total_contribs = int(total_contribs or sum(int(r.get("contributions", 0)) for r in date_records.values()))
    if total_contribs <= 0:
        raise ValueError("No positive contribution total provided")

    sorted_dates = sorted(datetime.date.fromisoformat(d) for d in date_records)
    first_date, last_date = sorted_dates[0], sorted_dates[-1]
    first_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)

    grid = {}
    for d_str, rec in date_records.items():
        d = datetime.date.fromisoformat(d_str)
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < 52 and 0 <= row < 7:
            lvl = max(0, min(4, int(rec.get("level", 0))))
            cnt = max(0, int(rec.get("contributions", 0)))
            grid[(col, row)] = {"date": d_str, "contributions": cnt, "level": lvl,
                                "cx": col * 15 + 5, "cy": row * 13 + 5}

    active = [c for c in grid.values() if c["contributions"] > 0 and c["level"] > 0]
    if not active:
        raise ValueError("No active contribution cells found")

    import random
    random.Random(2405).shuffle(active)

    # One visual hit per real active cell. The day's real contribution count is
    # added to the HUD at impact, so the final HUD is the real rolling total.
    INTERVAL = 0.35
    MOVE = 0.18
    HIT = 0.25
    TOTAL = len(active) * INTERVAL
    cannon_y = 126

    def pct(t):
        return max(0.0, min(100.0, (t / TOTAL) * 100.0))

    colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]

    # SVG SMIL is used instead of hundreds of CSS @keyframes blocks. There is
    # exactly one animated rocket, one laser, one impact and one HUD text node.
    rocket_values, rocket_times = [], []
    laser_transform_values, laser_times, laser_opacity = [], [], []
    impact_values, impact_times, impact_opacity = [], [], []
    counter_values, counter_times = [], []
    cumulative = 0

    for i, cell in enumerate(active):
        start = i * INTERVAL
        fire = start + MOVE
        hit = start + HIT
        end = start + INTERVAL
        x, y = cell["cx"], cell["cy"]

        rocket_values.append(f"{x} {cannon_y}")
        rocket_times.append(f"{pct(start):.3f}%")

        # Laser is a vertical line; scaleY changes its length to the target.
        length = (y - (cannon_y - 10)) / 18.0
        laser_transform_values += [
            f"translate({x} {cannon_y - 10}) scale(1 0)",
            f"translate({x} {cannon_y - 10}) scale(1 {length:.3f})",
            f"translate({x} {cannon_y - 10}) scale(1 {length:.3f})",
            f"translate({x} {cannon_y - 10}) scale(1 0)",
        ]
        laser_times += [f"{pct(start):.3f}%", f"{pct(fire):.3f}%", f"{pct(hit):.3f}%", f"{pct(hit + .06):.3f}%"]
        laser_opacity += ["0", "1", "1", "0"]

        impact_values += [f"translate({x} {y}) scale(.15)", f"translate({x} {y}) scale(1.6)",
                          f"translate({x} {y}) scale(.15)"]
        impact_times += [f"{pct(start):.3f}%", f"{pct(hit):.3f}%", f"{pct(hit + .10):.3f}%"]
        impact_opacity += ["0", "1", "0"]

        cumulative += cell["contributions"]
        counter_values.append(f"DESTROYED: [ {min(cumulative, total_contribs):,} / {total_contribs:,} ]")
        counter_times.append(f"{pct(hit):.3f}%")

    # Add an explicit initial counter value and guarantee the exact API total at the end.
    counter_values.insert(0, f"DESTROYED: [ 0 / {total_contribs:,} ]")
    counter_times.insert(0, "0%")
    if cumulative != total_contribs:
        counter_values[-1] = f"DESTROYED: [ {total_contribs:,} / {total_contribs:,} ]"

    # Static cells are plain rects. Active cells have one tiny SMIL fill animation.
    rects = []
    for col in range(52):
        for row in range(7):
            cell = grid.get((col, row))
            x, y = col * 15, row * 13
            if not cell or cell["contributions"] <= 0 or cell["level"] <= 0:
                lvl = cell["level"] if cell else 0
                rects.append(f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colors[lvl]}"/>')

    # Map active cells by coordinate for their individual one-time damage animation.
    for i, cell in enumerate(active):
        original = colors[cell["level"]]
        hit = i * INTERVAL + HIT
        end = hit + .08
        rects.append(
            f'<rect x="{cell["cx"] - 5}" y="{cell["cy"] - 5}" width="10" height="10" rx="2" fill="{original}">'
            f'<animate attributeName="fill" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" '
            f'values="{original};#FDFBF7;#161B22" keyTimes="{pct(0):.3f}%;{pct(hit):.3f}%;{pct(end):.3f}%" calcMode="discrete"/>'
            f'</rect>'
        )

    formatted = f"{total_contribs:,}"
    svg = f'''<svg width="850" height="275" viewBox="0 0 850 275" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect width="850" height="275" rx="4" fill="#0B0C10" stroke="#1F2430" stroke-width="1.5"/>
<style>
.tag{{font-family:'JetBrains Mono',Consolas,monospace;font-size:11px;font-weight:700;fill:#00F0FF;letter-spacing:2px}}
.month{{font-family:'JetBrains Mono',Consolas,monospace;font-size:9px;fill:#71737E}}
.score{{font-family:'JetBrains Mono',Consolas,monospace;font-size:9px;fill:#8B949E}}
.counter{{font-family:'JetBrains Mono',Consolas,monospace;font-size:10px;font-weight:800;fill:#39D353;letter-spacing:.5px}}
</style>
<g transform="translate(24,22)"><circle cx="0" cy="5" r="3.5" fill="#39D353"/><text x="14" y="9" class="tag">PORTAL GATEWAY // SECTOR 03: RETRO LASER CANNON COMMIT ARCADE</text></g>
<g transform="translate(565,10)"><rect width="260" height="26" rx="3" fill="#111216" stroke="#2563EB" stroke-width="1.2"/>
<text x="130" y="17" text-anchor="middle" class="counter">DESTROYED: [ 0 / {formatted} ]<animate attributeName="textContent" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(counter_values)}" keyTimes="{' ; '.join(counter_times)}"/></text></g>
<line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B"/>
<g transform="translate(36,62)">
<text x="0" y="-8" class="month">JAN</text><text x="64" y="-8" class="month">FEB</text><text x="128" y="-8" class="month">MAR</text><text x="192" y="-8" class="month">APR</text><text x="256" y="-8" class="month">MAY</text><text x="320" y="-8" class="month">JUN</text><text x="384" y="-8" class="month">JUL</text><text x="448" y="-8" class="month">AUG</text><text x="512" y="-8" class="month">SEP</text><text x="576" y="-8" class="month">OCT</text><text x="640" y="-8" class="month">NOV</text><text x="704" y="-8" class="month">DEC</text>
<g>{''.join(rects)}</g>
<line x1="0" y1="0" x2="0" y2="18" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round" opacity="0">
<animateTransform attributeName="transform" type="translate" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(rocket_values)}" keyTimes="{' ; '.join(rocket_times)}"/>
<animate attributeName="opacity" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" values="0;1;0" keyTimes="0%;50%;100%"/>
</line>
<line x1="0" y1="0" x2="0" y2="18" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round">
<animateTransform attributeName="transform" type="translate" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(laser_transform_values)}" keyTimes="{' ; '.join(laser_times)}"/>
<animate attributeName="opacity" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(laser_opacity)}" keyTimes="{' ; '.join(laser_times)}"/>
</line>
<g><animateTransform attributeName="transform" type="translate" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(impact_values)}" keyTimes="{' ; '.join(impact_times)}"/><animate attributeName="opacity" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" calcMode="discrete" values="{' ; '.join(impact_opacity)}" keyTimes="{' ; '.join(impact_times)}"/><circle r="4" fill="#FDFBF7"/><path d="M0 -7V7 M-7 0H7 M-5 -5L5 5 M5 -5L-5 5" stroke="#F59E0B" stroke-width="1.5"/></g>
<g><animateTransform attributeName="transform" type="translate" dur="{TOTAL:.2f}s" repeatCount="1" fill="freeze" values="{' ; '.join(rocket_values)}" keyTimes="{' ; '.join(rocket_times)}"/><polygon points="0,-10 7,6 0,2 -7,6" fill="#FDFBF7"/><polygon points="0,2 7,6 7,12 0,9 -7,12 -7,6" fill="#2563EB"/><rect x="-3" y="4" width="6" height="6" fill="#E11D48"/><polygon points="-7,8 -11,14 -7,12" fill="#00F0FF"/><polygon points="7,8 11,14 7,12" fill="#00F0FF"/><polygon points="-4,12 0,18 4,12" fill="#F59E0B"/><circle cx="0" cy="-2" r="1.5" fill="#00F0FF"/></g>
</g>
<g transform="translate(36,252)"><rect width="9" height="9" rx="2" fill="#161B22"/><text x="14" y="8" class="score">LEVEL 0 (DEPLETED)</text><rect x="140" width="9" height="9" rx="2" fill="#0E4429"/><text x="154" y="8" class="score">LEVEL 1</text><rect x="240" width="9" height="9" rx="2" fill="#006D32"/><text x="254" y="8" class="score">LEVEL 2</text><rect x="350" width="9" height="9" rx="2" fill="#26A641"/><text x="364" y="8" class="score">LEVEL 3</text><rect x="450" width="9" height="9" rx="2" fill="#39D353"/><text x="464" y="8" class="score" style="fill:#39D353;font-weight:bold">LEVEL 4 (FULL LIGHT)</text><text x="630" y="8" font-family="'JetBrains Mono',monospace" font-size="10.5px" font-weight="700" fill="#2563EB">{formatted} TOTAL COMMITS</text></g>
</svg>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active)} active contribution cells in authentic layout.")
    print(f"Real rolling one-year contribution total: {total_contribs:,}")
    print(f"Animation mode: ultra-light SMIL — one rocket + one laser + one impact + one counter.")
    print(f"Visual attack cadence: {INTERVAL:.2f}s per real active cell ({len(active)} visual hits).")
    print(f"Visual duration: {TOTAL:.2f}s ({TOTAL/60:.1f} minutes)")
    print(f"Final HUD total: {total_contribs:,}")
    print(f"Successfully wrote {output_path}")
    sync_other_svgs(total_contribs)

if __name__ == "__main__":
    records, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if records:
        generate_svg(records, total_contribs)
    else:
        print("Error: Could not retrieve contribution records.")
