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
    """
    Generate a lightweight one-shot SVG animation from real GitHub contribution data.

    Important design:
    - The 52x7 grid is always rendered with a real fill, so it never disappears.
    - Every real contribution is represented by one attack event.
    - Each active cell is guaranteed to receive enough early hits to deplete its
      GitHub level (4 -> 3 -> 2 -> 1 -> 0 where applicable).
    - Remaining contribution events continue hitting real cells so the counter
      reaches the actual rolling one-year total.
    - Only ONE rocket, ONE laser and ONE impact are animated. This avoids thousands
      of independent CSS animations that make browsers choke on the SVG.
    - Exactly one attack event occurs per second.
    """
    if not date_records:
        raise ValueError("No contribution records provided")

    total_contribs = int(total_contribs or 0)
    if total_contribs <= 0:
        total_contribs = sum(int(r.get("contributions", 0)) for r in date_records.values())
    if total_contribs <= 0:
        raise ValueError("No positive contribution total provided")

    sorted_dates = sorted(datetime.date.fromisoformat(d) for d in date_records)
    first_date, last_date = sorted_dates[0], sorted_dates[-1]
    first_sunday = first_date - datetime.timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    grid = {}
    for d_str, rec in date_records.items():
        d = datetime.date.fromisoformat(d_str)
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < 52 and 0 <= row < 7:
            lvl = max(0, min(4, int(rec.get("level", 0))))
            cnt = max(0, int(rec.get("contributions", 0)))
            grid[(col, row)] = {
                "date": d_str,
                "contributions": cnt,
                "lvl": lvl,
                "col": col,
                "row": row,
                "cx": col * 15 + 5,
                "cy": row * 13 + 5,
            }

    active_cells = [
        cell for cell in grid.values()
        if cell["contributions"] > 0 and cell["lvl"] > 0
    ]
    if not active_cells:
        raise ValueError("No active contribution cells were found")

    # Deterministic random order so the generated SVG is stable between runs.
    import random
    rng = random.Random(2405)
    shuffled = active_cells[:]
    rng.shuffle(shuffled)

    # Build a complete route of exactly total_contribs attacks.
    # First guarantee every cell is visibly depleted according to its level.
    route = []
    remaining_total = total_contribs
    max_required = sum(c["lvl"] for c in shuffled)

    # If the API total is smaller than the visual level sum, use the total as the
    # authoritative number of attacks; otherwise fully deplete every active cell.
    required = min(remaining_total, max_required)

    # Round-robin through the randomized cells, one level per visit.
    for round_no in range(1, 5):
        if len(route) >= required:
            break
        for cell in shuffled:
            if round_no <= cell["lvl"] and len(route) < required:
                route.append(cell)
        if len(route) >= required:
            break

    # Continue attacking real active cells until the counter reaches the real
    # rolling-year total. Depleted cells still flash on later contribution hits,
    # but never go below Level 0.
    while len(route) < remaining_total:
        candidates = shuffled[:]
        rng.shuffle(candidates)
        for cell in candidates:
            if len(route) >= remaining_total:
                break
            route.append(cell)

    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")
    print(f"Real rolling one-year contribution total: {total_contribs:,}")
    print(f"Attack route contains {len(route):,} real contribution hits.")
    print("Animation mode: lightweight ONE-SHOT — all cells visible, no 8-target loop, no reset.")
    print("Attack cadence: exactly 1.00s per contribution.")

    # One attack event per second. Movement is part of that one-second interval.
    ATTACK_INTERVAL = 1.0
    T_MOVE = 0.34
    T_AIM = 0.08
    T_LASER = 0.20
    T_HIT = 0.16
    T_SETTLE = ATTACK_INTERVAL - T_MOVE - T_AIM - T_LASER - T_HIT
    if T_SETTLE < 0:
        raise ValueError("Attack timing configuration is invalid")

    cannon_y = 126
    events = []
    for i, cell in enumerate(route):
        start = i * ATTACK_INTERVAL
        arrive = start + T_MOVE
        fire = arrive + T_AIM
        hit = fire + T_LASER
        end = start + ATTACK_INTERVAL
        events.append({
            "index": i,
            "cell": cell,
            "cx": cell["cx"],
            "cy": cell["cy"],
            "start": start,
            "arrive": arrive,
            "fire": fire,
            "hit": hit,
            "end": end,
        })

    total_duration = len(events) * ATTACK_INTERVAL
    print(f"Total one-shot attack duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)")
    print(f"Attack events: {len(events):,}")

    def pct(seconds):
        if total_duration <= 0:
            return "0%"
        return f"{max(0.0, min(100.0, seconds / total_duration * 100.0)):.4f}%"

    colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]

    # Track how many times each cell has been hit. Only the first N hits change
    # its level; later contribution hits create a visible impact without going
    # below Level 0.
    cell_hit_count = {}
    cell_events = {}
    for ev in events:
        key = (ev["cell"]["col"], ev["cell"]["row"])
        hit_no = cell_hit_count.get(key, 0) + 1
        cell_hit_count[key] = hit_no
        original = ev["cell"]["lvl"]
        remaining_level = max(0, original - min(hit_no, original))
        ev["remaining_level"] = remaining_level
        cell_events.setdefault(key, []).append(ev)

    # Each cell gets ONE animation. This keeps the SVG performant even with
    # thousands of contribution hits.
    cell_css = []
    cell_classes = {}
    for ci, (key, evs) in enumerate(cell_events.items(), 1):
        cls = f"commit-cell-{ci}"
        cell_classes[key] = cls
        original = evs[0]["cell"]["lvl"]

        kf = [
            f"0%, {pct(evs[0]['hit'] - 0.02)} "
            f"{{ fill:{colors[original]}; opacity:1; }}"
        ]
        for ev in evs:
            kf.append(
                f"{pct(ev['hit'])} {{ fill:#FDFBF7; opacity:1; }}"
            )
            kf.append(
                f"{pct(ev['hit'] + 0.06)} "
                f"{{ fill:{colors[ev['remaining_level']]}; opacity:1; }}"
            )
        kf.append(f"100% {{ fill:{colors[0]}; opacity:1; }}")

        cell_css.append(
            f"@keyframes damageCell{ci} {{ {' '.join(kf)} }}"
        )
        cell_css.append(
            f".{cls} {{ fill:{colors[original]}; "
            f"animation:damageCell{ci} {total_duration:.2f}s linear 1 forwards; }}"
        )

    # ONE rocket animation.
    route_kf = []
    first_x = events[0]["cx"]
    route_kf.append(f"0% {{ transform:translate({first_x}px,{cannon_y}px); }}")
    for ev in events:
        route_kf.append(
            f"{pct(ev['start'])} {{ transform:translate({ev['cx']}px,{cannon_y}px); }}"
        )
        route_kf.append(
            f"{pct(ev['arrive'])} {{ transform:translate({ev['cx']}px,{cannon_y}px); }}"
        )
    route_kf.append(
        f"100% {{ transform:translate({events[-1]['cx']}px,{cannon_y}px); }}"
    )
    route_css = (
        f"@keyframes shipPatrolRoute {{ {' '.join(route_kf)} }}"
        f".ship-patrol {{ animation:shipPatrolRoute {total_duration:.2f}s "
        f"linear 1 forwards; }}"
    )

    # ONE laser element whose position changes for every shot.
    laser_kf = []
    spark_kf = []
    for ev in events:
        x, y = ev["cx"], ev["cy"]
        tip = cannon_y - 10
        laser_kf.extend([
            f"{pct(ev['start'])}, {pct(ev['fire'] - 0.01)} "
            f"{{ opacity:0; transform:translate({x}px,{tip}px) scaleY(.1); }}",
            f"{pct(ev['fire'])} "
            f"{{ opacity:1; transform:translate({x}px,{tip}px) scaleY(.8); }}",
            f"{pct(ev['hit'])} "
            f"{{ opacity:1; transform:translate({x}px,{y}px) scaleY(1); }}",
            f"{pct(ev['hit'] + 0.05)} "
            f"{{ opacity:0; transform:translate({x}px,{y}px) scaleY(.1); }}",
        ])
        spark_kf.extend([
            f"{pct(ev['start'])}, {pct(ev['hit'] - 0.01)} "
            f"{{ opacity:0; transform:translate({x}px,{y}px) scale(.1); }}",
            f"{pct(ev['hit'])} "
            f"{{ opacity:1; transform:translate({x}px,{y}px) scale(1); }}",
            f"{pct(ev['hit'] + 0.12)} "
            f"{{ opacity:0; transform:translate({x}px,{y}px) scale(1.7); }}",
        ])

    laser_css_text = (
        f"@keyframes laserShot {{ {' '.join(laser_kf)} }}"
        f".laser-bolt {{ animation:laserShot {total_duration:.2f}s linear 1 forwards; }}"
    )
    spark_css_text = (
        f"@keyframes sparkHit {{ {' '.join(spark_kf)} }}"
        f".spark-burst {{ animation:sparkHit {total_duration:.2f}s ease-out 1 forwards; }}"
    )

    # Compact odometer counter. Four digit strips show every integer from 0
    # through the final total without generating 1,951 separate <text> elements.
    total = total_contribs
    digits = len(str(total))
    digit_h = 11
    odometer = []
    odo_css = []

    for pos in range(digits):
        place = 10 ** (digits - pos - 1)
        steps = total // place
        final_digit = steps % 10
        # A strip of repeated digits lets the digit roll through all intermediate
        # values while the overall counter advances linearly from 0 to total.
        rows = max(12, steps + 2)
        strip = "".join(
            f'<text x="0" y="{i * digit_h}" text-anchor="middle" '
            f'class="counter-digit">{i % 10}</text>'
            for i in range(rows)
        )
        x = 130 + (pos - (digits - 1) / 2) * 8
        distance = steps * digit_h
        odometer.append(f'<g class="odo-{pos}">{strip}</g>')
        odo_css.append(
            f"@keyframes odoAnim{pos} {{ "
            f"from {{ transform:translate({x:.1f}px,4px); }} "
            f"to {{ transform:translate({x:.1f}px,{4-distance}px); }} }}"
            f".odo-{pos} {{ animation:odoAnim{pos} {total_duration:.2f}s "
            f"linear 1 forwards; }}"
        )

    formatted_total = f"{total:,}"

    # Static grid is ALWAYS given its original fill. Animated cells override
    # that fill, preventing the "all cells disappeared" bug.
    grid_markup = []
    for col in range(52):
        for row in range(7):
            x, y = col * 15, row * 13
            cell = grid.get((col, row), {"lvl": 0})
            lvl = max(0, min(4, int(cell.get("lvl", 0))))
            key = (col, row)
            cls = cell_classes.get(key)
            if cls:
                grid_markup.append(
                    f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" '
                    f'fill="{colors[lvl]}" class="{cls}"/>'
                )
            else:
                grid_markup.append(
                    f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" '
                    f'fill="{colors[lvl]}"/>'
                )

    css = f"""
      .bh-bg {{ fill:#0B0C10; stroke:#1F2430; stroke-width:1.5; }}
      .tag-txt {{ font-family:'JetBrains Mono',Consolas,monospace; font-size:11px; font-weight:700; fill:#00F0FF; letter-spacing:2px; }}
      .month-lbl {{ font-family:'JetBrains Mono',Consolas,monospace; font-size:9px; fill:#71737E; }}
      .score-lbl {{ font-family:'JetBrains Mono',Consolas,monospace; font-size:9px; fill:#8B949E; }}
      .counter-frame {{ fill:#111216; stroke:#2563EB; stroke-width:1.2; }}
      .counter-txt,.counter-digit {{ font-family:'JetBrains Mono',Consolas,monospace; font-size:9px; font-weight:700; fill:#39D353; }}
      .live-beacon {{ animation:beaconBlink .8s steps(2,start) infinite; }}
      @keyframes beaconBlink {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.2; }} }}
      {route_css}
      {''.join(cell_css)}
      {laser_css_text}
      {spark_css_text}
      {''.join(odo_css)}
    """

    svg_output = f"""<svg width="850" height="275" viewBox="0 0 850 275" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>{css}</style>
    <clipPath id="counterClip">
      <rect x="108" y="1" width="62" height="16"/>
    </clipPath>
  </defs>

  <rect width="850" height="275" rx="4" class="bh-bg"/>

  <g transform="translate(24,22)">
    <circle cx="0" cy="5" r="3.5" fill="#39D353" class="live-beacon"/>
    <text x="14" y="9" class="tag-txt">PORTAL GATEWAY // SECTOR 03: RETRO LASER CANNON COMMIT ARCADE</text>
  </g>

  <!-- Clear destroyed counter -->
  <g transform="translate(565,10)">
    <rect width="260" height="26" rx="3" class="counter-frame"/>
    <text x="10" y="17" class="counter-txt">DESTROYED: [</text>
    <g clip-path="url(#counterClip)">{''.join(odometer)}</g>
    <text x="175" y="17" class="counter-txt"> / {formatted_total} ]</text>
  </g>

  <line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B" stroke-width="1"/>

  <g transform="translate(36,62)">
    <text x="0" y="-8" class="month-lbl">JAN</text>
    <text x="64" y="-8" class="month-lbl">FEB</text>
    <text x="128" y="-8" class="month-lbl">MAR</text>
    <text x="192" y="-8" class="month-lbl">APR</text>
    <text x="256" y="-8" class="month-lbl">MAY</text>
    <text x="320" y="-8" class="month-lbl">JUN</text>
    <text x="384" y="-8" class="month-lbl">JUL</text>
    <text x="448" y="-8" class="month-lbl">AUG</text>
    <text x="512" y="-8" class="month-lbl">SEP</text>
    <text x="576" y="-8" class="month-lbl">OCT</text>
    <text x="640" y="-8" class="month-lbl">NOV</text>
    <text x="704" y="-8" class="month-lbl">DEC</text>

    <g>{''.join(grid_markup)}</g>

    <!-- Exactly one laser and one impact are animated at a time -->
    <line x1="0" y1="0" x2="0" y2="18" class="laser-bolt"
          stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round"/>

    <g class="spark-burst">
      <circle cx="0" cy="0" r="3" fill="#FDFBF7"/>
      <path d="M0 -7V7 M-7 0H7 M-5 -5L5 5 M5 -5L-5 5"
            stroke="#F59E0B" stroke-width="1.5"/>
    </g>

    <g class="ship-patrol">
      <g transform="translate(0,0)">
        <polygon points="0,-10 7,6 0,2 -7,6" fill="#FDFBF7"/>
        <polygon points="0,2 7,6 7,12 0,9 -7,12 -7,6" fill="#2563EB"/>
        <rect x="-3" y="4" width="6" height="6" fill="#E11D48"/>
        <polygon points="-7,8 -11,14 -7,12" fill="#00F0FF"/>
        <polygon points="7,8 11,14 7,12" fill="#00F0FF"/>
        <polygon points="-4,12 0,18 4,12" fill="#F59E0B"/>
        <circle cx="0" cy="-2" r="1.5" fill="#00F0FF"/>
      </g>
    </g>
  </g>

  <g transform="translate(36,252)">
    <rect width="9" height="9" rx="2" fill="#161B22"/>
    <text x="14" y="8" class="score-lbl">LEVEL 0 (DEPLETED)</text>
    <rect x="140" y="0" width="9" height="9" rx="2" fill="#0E4429"/>
    <text x="154" y="8" class="score-lbl">LEVEL 1</text>
    <rect x="240" y="0" width="9" height="9" rx="2" fill="#006D32"/>
    <text x="254" y="8" class="score-lbl">LEVEL 2</text>
    <rect x="350" y="0" width="9" height="9" rx="2" fill="#26A641"/>
    <text x="364" y="8" class="score-lbl">LEVEL 3</text>
    <rect x="450" y="0" width="9" height="9" rx="2" fill="#39D353"/>
    <text x="464" y="8" class="score-lbl" style="fill:#39D353;font-weight:bold;">LEVEL 4 (FULL LIGHT)</text>
    <text x="630" y="8" font-family="'JetBrains Mono',monospace" font-size="10.5px"
          font-weight="700" fill="#2563EB">{formatted_total} TOTAL COMMITS</text>
  </g>
</svg>"""

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