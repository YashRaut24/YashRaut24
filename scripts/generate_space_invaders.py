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
    # Lightweight one-shot renderer: one rocket, one laser, one impact burst.
    # Real GitHub cells remain the source of truth. Each active cell is hit once
    # per contribution level so its visual state progresses to LEVEL 0.
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
            grid[(col, row)] = {
                "date": d_str,
                "contributions": int(rec.get("contributions", 0)),
                "lvl": lvl,
                "initial_level": max(0, min(4, int(rec.get("initial_level", lvl))))
            }

    active_cells = []
    for (col, row), cell in grid.items():
        if cell["contributions"] > 0 and cell["lvl"] > 0:
            active_cells.append({
                "col": col, "row": row, "lvl": cell["lvl"],
                "initial_level": cell["initial_level"],
                "contributions": cell["contributions"], "date": cell["date"],
                "cx": col * 15 + 5, "cy": row * 13 + 5
            })
    if not active_cells:
        raise ValueError("No active contribution cells found")

    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")
    print(f"Real rolling one-year contribution total: {total_contribs:,}")

    import random
    route_cells = active_cells[:]
    random.Random(20260827).shuffle(route_cells)

    # One event per visual level reduction, not one SVG object per contribution.
    # This keeps the animation responsive while still taking every real cell to 0.
    attacks = []
    for cell in route_cells:
        levels = max(1, min(4, cell["initial_level"]))
        base = cell["contributions"] // levels
        rem = cell["contributions"] % levels
        for hit_idx in range(levels):
            attacks.append({
                **cell,
                "start_lvl": max(1, cell["initial_level"] - hit_idx),
                "damaged_lvl": max(0, cell["initial_level"] - hit_idx - 1),
                "counter_add": base + (1 if hit_idx < rem else 0)
            })

    delta = total_contribs - sum(a["counter_add"] for a in attacks)
    if delta:
        attacks[-1]["counter_add"] += delta

    # Keep the requested one-second attack cadence.
    ATTACK_INTERVAL = 1.0
    TOTAL_DURATION = max(ATTACK_INTERVAL, len(attacks) * ATTACK_INTERVAL)
    cannon_y = 126
    events = []
    cumulative = 0
    previous_x = 425 - 36
    for i, a in enumerate(attacks):
        start = i * ATTACK_INTERVAL
        dx = abs(a["cx"] - previous_x)
        travel = min(0.34, max(0.10, 0.10 + dx / 1500.0))
        impact = start + travel + 0.16
        cumulative += max(0, a["counter_add"])
        events.append({**a, "start": start, "travel": travel, "impact": impact, "cumulative": cumulative})
        previous_x = a["cx"]
    events[-1]["cumulative"] = total_contribs

    print(f"Attack route: {len(attacks):,} level hits across {len(active_cells)} real active cells.")
    print("Animation mode: lightweight ONE-SHOT — one rocket + one laser + one impact; no reset.")
    print(f"Attack cadence: exactly {ATTACK_INTERVAL:.2f}s per level hit.")
    print(f"Total one-shot attack duration: {TOTAL_DURATION:.2f}s ({TOTAL_DURATION/60:.1f} minutes)")

    def pct(t):
        return f"{max(0.0, min(100.0, t / TOTAL_DURATION * 100.0)):.4f}%"

    colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
    keyframes = []

    # Single rocket route.
    route = []
    for e in events:
        route.append(f'  {pct(e["start"])} {{ transform: translate({e["cx"]}px,{cannon_y}px); }}')
        route.append(f'  {pct(e["start"] + e["travel"])} {{ transform: translate({e["cx"]}px,{cannon_y}px); }}')
    keyframes.append("@keyframes shipRoute {\n" + "\n".join(route) + "\n}")

    # Single laser. It is repositioned for each event, so there are never hundreds
    # of simultaneously animated laser elements.
    laser = []
    for e in events:
        s, fire, hit = e["start"], e["start"] + e["travel"], e["impact"]
        laser += [
            f'  {pct(s)} {{ opacity:0; transform:translate({e["cx"]}px,{cannon_y-10}px) scaleY(0); }}',
            f'  {pct(fire)} {{ opacity:1; transform:translate({e["cx"]}px,{cannon_y-10}px) scaleY(.25); }}',
            f'  {pct(hit)} {{ opacity:1; transform:translate({e["cx"]}px,{e["cy"]}px) scaleY(1); }}',
            f'  {pct(hit+.035)} {{ opacity:0; transform:translate({e["cx"]}px,{e["cy"]}px) scaleY(0); }}'
        ]
    keyframes.append("@keyframes laserRoute {\n" + "\n".join(laser) + "\n}")

    # Single impact burst, always located at the exact cell being hit.
    impact = []
    for e in events:
        s, hit = e["start"], e["impact"]
        impact += [
            f'  {pct(s)} {{ opacity:0; transform:translate({e["cx"]}px,{e["cy"]}px) scale(.15); }}',
            f'  {pct(hit)} {{ opacity:1; transform:translate({e["cx"]}px,{e["cy"]}px) scale(1.8); }}',
            f'  {pct(hit+.10)} {{ opacity:0; transform:translate({e["cx"]}px,{e["cy"]}px) scale(.25); }}'
        ]
    keyframes.append("@keyframes impactRoute {\n" + "\n".join(impact) + "\n}")

    # One animation per real cell for the persistent damage state.
    cell_events = {}
    for e in events:
        cell_events.setdefault((e["col"], e["row"]), []).append(e)
    cell_css, cell_classes = [], {}
    for idx, ((col, row), evs) in enumerate(cell_events.items(), 1):
        cls = f"cell-damage-{idx}"
        cell_classes[(col, row)] = cls
        kf = [f'  0% {{ fill:{colors[evs[0]["start_lvl"]]}; }}']
        for e in evs:
            kf += [
                f'  {pct(e["impact"]-.01)} {{ fill:{colors[e["start_lvl"]]}; }}',
                f'  {pct(e["impact"])} {{ fill:#FDFBF7; }}',
                f'  {pct(e["impact"]+.055)} {{ fill:{colors[e["damaged_lvl"]]}; }}'
            ]
        kf.append(f'  100% {{ fill:{colors[evs[-1]["damaged_lvl"]]}; }}')
        keyframes.append(f"@keyframes {cls}-kf {{\n" + "\n".join(kf) + "\n}")
        cell_css.append(f".{cls} {{ animation:{cls}-kf {TOTAL_DURATION:.2f}s linear 1 forwards; }}")

    # Compact HUD: show the exact cumulative value after every real level hit.
    # Only one text node is visible at a time; there is no 1,951-node overlap.
    hud_keyframes = []
    hud_texts = []
    for i, e in enumerate(events):
        start = 0 if i == 0 else events[i-1]["impact"]
        end = e["impact"]
        value = e["cumulative"]
        kf_name = f"hudStep{i}"
        hud_keyframes.append(
            f"@keyframes {kf_name} {{ 0%{{opacity:0}} {pct(start)}{{opacity:0}} "
            f"{pct(end-.001)}{{opacity:1}} {pct(end)}{{opacity:0}} 100%{{opacity:0}} }}"
        )
        hud_texts.append(f'      <text x="130" y="17" text-anchor="middle" class="hud hud-{i}">DESTROYED: [ {value:,} / {total_contribs:,} ]</text>')

    hud_css = [f".hud {{ font-family:'JetBrains Mono',Consolas,monospace; font-size:10px; font-weight:800; fill:#39D353; letter-spacing:.7px; }}"]
    for i in range(len(events)):
        hud_css.append(f".hud-{i} {{ opacity:0; animation:hudStep{i} {TOTAL_DURATION:.2f}s linear 1 forwards; }}")

    grid_rects = []
    for col in range(52):
        for row in range(7):
            x, y = col*15, row*13
            cell = grid.get((col,row), {"lvl":0})
            lvl = max(0,min(4,int(cell.get("lvl",0))))
            cls = cell_classes.get((col,row))
            if cls:
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" class="{cls}"/>')
            else:
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colors[lvl]}"/>')

    full_css = "\n".join([
        ".bh-bg{fill:#0B0C10;stroke:#1F2430;stroke-width:1.5}",
        ".tag-txt{font-family:'JetBrains Mono',Consolas,monospace;font-size:11px;font-weight:700;fill:#00F0FF;letter-spacing:2px}",
        ".month-lbl{font-family:'JetBrains Mono',Consolas,monospace;font-size:9px;fill:#71737E}",
        ".score-lbl{font-family:'JetBrains Mono',Consolas,monospace;font-size:9px;fill:#8B949E}",
        ".live-beacon{animation:beaconBlink .8s steps(2,start) infinite}",
        ".counter-frame{fill:#111216;stroke:#2563EB;stroke-width:1.2}",
        ".counter-title{font-family:'JetBrains Mono',Consolas,monospace;font-size:10px;font-weight:800;fill:#39D353;letter-spacing:.7px}",
        f".ship-patrol{{animation:shipRoute {TOTAL_DURATION:.2f}s cubic-bezier(.2,0,.1,1) 1 forwards}}",
        f".laser-main{{animation:laserRoute {TOTAL_DURATION:.2f}s linear 1 forwards}}",
        f".impact-main{{animation:impactRoute {TOTAL_DURATION:.2f}s ease-out 1 forwards}}",
        *cell_css, *hud_css, *hud_keyframes, *keyframes,
        "@keyframes beaconBlink{0%,100%{opacity:1}50%{opacity:.2}}"
    ])

    formatted_total = f"{total_contribs:,}"
    svg_output = f'''<svg width="850" height="275" viewBox="0 0 850 275" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs><style>{full_css}</style></defs>
  <rect width="850" height="275" rx="4" class="bh-bg"/>
  <g transform="translate(24,22)">
    <circle cx="0" cy="5" r="3.5" fill="#39D353" class="live-beacon"/>
    <text x="14" y="9" class="tag-txt">PORTAL GATEWAY // SECTOR 03: RETRO LASER CANNON COMMIT ARCADE</text>
  </g>
  <g transform="translate(565,10)">
    <rect width="260" height="26" rx="3" class="counter-frame"/>
    <text x="130" y="17" text-anchor="middle" class="hud hud-initial">DESTROYED: [ 0 / {total_contribs:,} ]</text>
{chr(10).join(hud_texts)}
  </g>
  <line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B"/>
  <g transform="translate(36,62)">
    <text x="0" y="-8" class="month-lbl">JAN</text><text x="64" y="-8" class="month-lbl">FEB</text>
    <text x="128" y="-8" class="month-lbl">MAR</text><text x="192" y="-8" class="month-lbl">APR</text>
    <text x="256" y="-8" class="month-lbl">MAY</text><text x="320" y="-8" class="month-lbl">JUN</text>
    <text x="384" y="-8" class="month-lbl">JUL</text><text x="448" y="-8" class="month-lbl">AUG</text>
    <text x="512" y="-8" class="month-lbl">SEP</text><text x="576" y="-8" class="month-lbl">OCT</text>
    <text x="640" y="-8" class="month-lbl">NOV</text><text x="704" y="-8" class="month-lbl">DEC</text>
    <g>{chr(10).join(grid_rects)}</g>
    <line x1="0" y1="0" x2="0" y2="18" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round" class="laser-main"/>
    <g class="impact-main"><circle r="4" fill="#FDFBF7"/><line x1="-6" y1="-6" x2="6" y2="6" stroke="#F59E0B" stroke-width="1.6"/><line x1="6" y1="-6" x2="-6" y2="6" stroke="#F59E0B" stroke-width="1.6"/><line x1="-7" y1="0" x2="7" y2="0" stroke="#E11D48" stroke-width="1.2"/><line x1="0" y1="-7" x2="0" y2="7" stroke="#E11D48" stroke-width="1.2"/></g>
    <g class="ship-patrol"><polygon points="0,-10 7,6 0,2 -7,6" fill="#FDFBF7"/><polygon points="0,2 7,6 7,12 0,9 -7,12 -7,6" fill="#2563EB"/><rect x="-3" y="4" width="6" height="6" fill="#E11D48"/><polygon points="-7,8 -11,14 -7,12" fill="#00F0FF"/><polygon points="7,8 11,14 7,12" fill="#00F0FF"/><polygon points="-4,12 0,18 4,12" fill="#F59E0B"/><circle cx="0" cy="-2" r="1.5" fill="#00F0FF"/></g>
  </g>
  <g transform="translate(36,252)">
    <rect width="9" height="9" rx="2" fill="#161B22"/><text x="14" y="8" class="score-lbl">LEVEL 0 (DEPLETED)</text>
    <rect x="140" width="9" height="9" rx="2" fill="#0E4429"/><text x="154" y="8" class="score-lbl">LEVEL 1</text>
    <rect x="240" width="9" height="9" rx="2" fill="#006D32"/><text x="254" y="8" class="score-lbl">LEVEL 2</text>
    <rect x="350" width="9" height="9" rx="2" fill="#26A641"/><text x="364" y="8" class="score-lbl">LEVEL 3</text>
    <rect x="450" width="9" height="9" rx="2" fill="#39D353"/><text x="464" y="8" class="score-lbl" style="fill:#39D353;font-weight:bold">LEVEL 4 (FULL LIGHT)</text>
    <text x="630" y="8" font-family="'JetBrains Mono',monospace" font-size="10.5px" font-weight="700" fill="#2563EB">{formatted_total} TOTAL COMMITS</text>
  </g>
</svg>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_output)
    print(f"Successfully wrote {output_path}")
    sync_other_svgs(total_contribs)

if __name__ == "__main__":
    records, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if records:
        generate_svg(records, total_contribs)
    else:
        print("Error: Could not retrieve contribution records.")
