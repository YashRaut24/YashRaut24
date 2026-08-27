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
    if not date_records:
        raise ValueError("No contribution records provided")
    if total_contribs <= 0:
        total_contribs = sum(r.get("contributions", 0) for r in date_records.values())

    sorted_dates = sorted([datetime.date.fromisoformat(d) for d in date_records.keys()])
    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]

    first_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)
    
    # 52x7 Grid mapping
    grid = {}
    for d_str, rec in date_records.items():
        d = datetime.date.fromisoformat(d_str)
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < 52 and 0 <= row < 7:
            grid[(col, row)] = {
                "date": d_str,
                "contributions": rec.get("contributions", 0),
                "lvl": rec.get("level", 0),
                "initial_level": rec.get("initial_level", rec.get("level", 0)),
                "col": col,
                "row": row
            }

    active_cells = []
    for (col, row), cell in grid.items():
        if cell["lvl"] > 0:
            active_cells.append({
                "col": col,
                "row": row,
                "lvl": cell["lvl"],
                "initial_level": cell["initial_level"],
                "contributions": cell["contributions"],
                "date": cell["date"],
                "cx": col * 15 + 5,
                "cy": row * 13 + 5
            })

    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")

    # Use EVERY real active contribution cell. Each contribution becomes one
    # laser-hit event, distributed round-robin so the rocket keeps moving to
    # other real commits instead of repeating only eight targets.
    import random
    route_cells = active_cells[:]
    random.Random(20260827).shuffle(route_cells)

    targets = []
    remaining = {(c["col"], c["row"]): int(c["contributions"]) for c in route_cells}
    while any(v > 0 for v in remaining.values()):
        for c in route_cells:
            key = (c["col"], c["row"])
            if remaining[key] > 0:
                targets.append(c)
                remaining[key] -= 1

    # Keep the authoritative GitHub rolling total as the final hit count.
    if len(targets) < total_contribs:
        for i in range(total_contribs - len(targets)):
            targets.append(route_cells[i % len(route_cells)])
    elif len(targets) > total_contribs:
        targets = targets[:total_contribs]

    print(f"Attack route contains {len(targets):,} real contribution hits.")
    print("Animation mode: ONE-SHOT — no 8-target loop and no visual reset.")

    targets_data = []
    cell_hit_counts = {}
    for idx, t in enumerate(targets):
        key = (t["col"], t["row"])
        hit_number = cell_hit_counts.get(key, 0)
        cell_hit_counts[key] = hit_number + 1
        start_lvl = max(0, int(t["initial_level"]) - hit_number)
        damaged_lvl = max(0, start_lvl - 1)
        targets_data.append({
            "id": idx + 1,
            "col": t["col"], "row": t["row"],
            "lvl": t["lvl"],
            "start_lvl": start_lvl, "damaged_lvl": damaged_lvl,
            "contributions": t["contributions"], "date": t["date"],
            "cx": t["cx"], "cy": t["cy"],
            "cell_key": key,
        })

    T_AIM      = 0.10
    T_LASER    = 0.16
    T_HIT      = 0.12
    T_POST_HIT = 0.62
    ATTACK_SEQ_DURATION = T_AIM + T_LASER + T_HIT + T_POST_HIT # 1.00s

    cannon_y = 126
    travel_durations = []
    for i in range(len(targets_data)):
        prev_cx = targets_data[i-1]["cx"] if i > 0 else 425 - 36
        curr_cx = targets_data[i]["cx"]
        dx = abs(curr_cx - prev_cx)
        t_travel = 0.35 + min(0.40, (dx / 780.0) * 0.40)
        travel_durations.append(t_travel)

    cycle_durations = [travel_durations[i] + ATTACK_SEQ_DURATION for i in range(len(targets_data))]
    TOTAL_DURATION = sum(cycle_durations)

    print(f"Total one-shot attack duration: {TOTAL_DURATION:.2f}s")
    print(f"Attack events: {len(targets_data):,} (one per real contribution)")

    cycle_start_times = [0.0]
    for d in cycle_durations[:-1]:
        cycle_start_times.append(cycle_start_times[-1] + d)

    def to_pct(seconds):
        pct = (seconds / TOTAL_DURATION) * 100.0
        pct = max(0.0, min(100.0, pct))
        return f"{pct:.3f}%"

    keyframes_css = []

    # 1. Rocket Movement Route Keyframes
    route_kfs = []
    for i, t in enumerate(targets_data):
        t_start = cycle_start_times[i]
        t_travel = travel_durations[i]
        t_arrive = t_start + t_travel
        t_end = t_start + cycle_durations[i]

        tx = t["cx"]
        route_kfs.append(f"  {to_pct(t_start)}  {{ transform: translate({tx}px, {cannon_y}px); }}")
        route_kfs.append(f"  {to_pct(t_arrive)} {{ transform: translate({tx}px, {cannon_y}px); }}")
        route_kfs.append(f"  {to_pct(t_end)}    {{ transform: translate({tx}px, {cannon_y}px); }}")

    route_kfs_str = "\n".join(route_kfs)
    keyframes_css.append(f'''@keyframes shipPatrolRoute {{
{route_kfs_str}
}}''')

    # 2. Laser, Burst & Commit Damage Keyframes for each target
    for i, t in enumerate(targets_data):
        tid = t["id"]
        t_start = cycle_start_times[i]
        t_arrive = t_start + travel_durations[i]
        
        t_fire_start = t_arrive + T_AIM
        t_fire_hit   = t_fire_start + T_LASER
        t_hit_end    = t_fire_hit + T_HIT

        t_y = t["cy"]
        cannon_tip_y = cannon_y - 10

        laser_kf = f'''@keyframes laserShot{tid} {{
  0% {{ opacity: 0; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(0.5); }}
  {to_pct(t_fire_start - 0.01)} {{ opacity: 0; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(0.5); }}
  {to_pct(t_fire_start)}        {{ opacity: 1; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(1.2); }}
  {to_pct(t_fire_hit)}          {{ opacity: 1; transform: translate({t["cx"]}px, {t_y}px) scaleY(0.3); }}
  {to_pct(t_fire_hit + 0.02)}   {{ opacity: 0; transform: translate({t["cx"]}px, {t_y}px) scaleY(0); }}
  100% {{ opacity: 0; transform: translate({t["cx"]}px, {t_y}px); }}
}}'''
        keyframes_css.append(laser_kf)

        spark_kf = f'''@keyframes sparkHit{tid} {{
  0% {{ opacity: 0; transform: scale(0.2); }}
  {to_pct(t_fire_hit - 0.01)} {{ opacity: 0; transform: scale(0.2); }}
  {to_pct(t_fire_hit)}        {{ opacity: 1; transform: scale(1.6); }}
  {to_pct(t_hit_end)}         {{ opacity: 0.8; transform: scale(1.0); }}
  {to_pct(t_hit_end + 0.05)}  {{ opacity: 0; transform: scale(0.3); }}
  100% {{ opacity: 0; transform: scale(0.2); }}
}}'''
        keyframes_css.append(spark_kf)

        dim_colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
        orig_color = dim_colors[t["start_lvl"]]
        target_color = dim_colors[t["damaged_lvl"]]

        commit_kf = f'''@keyframes commitDamage{tid} {{
  0% {{ fill: {orig_color}; }}
  {to_pct(t_fire_hit - 0.01)} {{ fill: {orig_color}; }}
  {to_pct(t_fire_hit)}        {{ fill: #FDFBF7; }}
  {to_pct(t_fire_hit + 0.06)} {{ fill: {target_color}; opacity: 0.85; }}
  {to_pct(TOTAL_DURATION - 0.05)} {{ fill: {target_color}; }}
  100% {{ fill: {target_color}; }}
}}'''
        keyframes_css.append(commit_kf)

    # 3. Destroyed Counter: exactly one integer per successful laser hit.
    # Each attack event corresponds to one real contribution. The counter is
    # synchronized to the actual laser impact time and never uses milestone
    # interpolation or an 8-target cycle.
    num_targets = len(targets_data)
    destroyed_milestones = list(range(num_targets + 1))

    for c_idx in range(num_targets + 1):
        if c_idx == 0:
            t_visible_start = 0.0
            t_visible_end = (
                cycle_start_times[0]
                + travel_durations[0]
                + T_AIM
                + T_LASER
            )
        elif c_idx < num_targets:
            previous = c_idx - 1
            t_visible_start = (
                cycle_start_times[previous]
                + travel_durations[previous]
                + T_AIM
                + T_LASER
            )
            t_visible_end = (
                cycle_start_times[c_idx]
                + travel_durations[c_idx]
                + T_AIM
                + T_LASER
            )
        else:
            t_visible_start = (
                cycle_start_times[num_targets - 1]
                + travel_durations[num_targets - 1]
                + T_AIM
                + T_LASER
            )
            t_visible_end = TOTAL_DURATION

        if c_idx == num_targets:
            counter_kf = f'''@keyframes hudCount{c_idx} {{
  0% {{ opacity: 0; }}
  {to_pct(max(0.0, t_visible_start - 0.001))} {{ opacity: 0; }}
  {to_pct(t_visible_start)} {{ opacity: 1; }}
  100% {{ opacity: 1; }}
}}'''
        else:
            counter_kf = f'''@keyframes hudCount{c_idx} {{
  0% {{ opacity: 0; }}
  {to_pct(max(0.0, t_visible_start - 0.001))} {{ opacity: 0; }}
  {to_pct(t_visible_start)} {{ opacity: 1; }}
  {to_pct(max(t_visible_start, t_visible_end - 0.001))} {{ opacity: 1; }}
  {to_pct(t_visible_end)} {{ opacity: 0; }}
  100% {{ opacity: 0; }}
}}'''
        keyframes_css.append(counter_kf)

    # Laser bolt elements
    laser_elements = []
    for t in targets_data:
        tid = t["id"]
        laser_elements.append(f'    <line x1="0" y1="0" x2="0" y2="18" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round" class="laser-bolt-{tid}"/>')
    lasers_content = "\n".join(laser_elements)

    # Spark elements
    spark_elements = []
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        spark_elements.append(f'''    <!-- Impact Burst {tid} at ({cx}, {cy}) -->
    <g transform="translate({cx}, {cy})" class="spark-burst-{tid}">
      <circle cx="0" cy="0" r="4" fill="#FDFBF7"/>
      <line x1="-5" y1="-5" x2="5" y2="5" stroke="#F59E0B" stroke-width="1.5"/>
      <line x1="5" y1="-5" x2="-5" y2="5" stroke="#F59E0B" stroke-width="1.5"/>
      <line x1="-6" y1="0" x2="6" y2="0" stroke="#E11D48" stroke-width="1.2"/>
      <line x1="0" y1="-6" x2="0" y2="6" stroke="#E11D48" stroke-width="1.2"/>
    </g>''')
    sparks_content = "\n".join(spark_elements)

    formatted_total = f"{total_contribs:,}"

    # Counter text displays every integer from 0 through the real total.
    counter_elements = []
    for c_idx in range(num_targets + 1):
        counter_elements.append(
            f'      <text x="130" y="17" text-anchor="middle" '
            f'class="counter-txt hud-val-{c_idx}">DESTROYED: [ '
            f'{c_idx:,} / {formatted_total} COMMITS ]</text>'
        )
    counter_texts = "\n".join(counter_elements)

    # CSS Rules
    css_class_rules = [
        f".ship-patrol {{ animation: shipPatrolRoute {TOTAL_DURATION:.2f}s cubic-bezier(0.25, 0, 0.15, 1) 1 forwards; }}",
        ".live-beacon { animation: beaconBlink 0.8s steps(2, start) infinite; }",
        ".counter-frame { fill: #111216; stroke: #2563EB; stroke-width: 1.2; }",
        ".counter-txt { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10px; font-weight: 700; fill: #39D353; letter-spacing: 0.8px; }"
    ]
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        css_class_rules.append(f".laser-bolt-{tid}   {{ animation: laserShot{tid} {TOTAL_DURATION:.2f}s linear 1 forwards; }}")
        css_class_rules.append(f".spark-burst-{tid}  {{ animation: sparkHit{tid} {TOTAL_DURATION:.2f}s ease-out 1 forwards; transform-origin: {cx}px {cy}px; }}")
        css_class_rules.append(f".commit-target-{tid} {{ animation: commitDamage{tid} {TOTAL_DURATION:.2f}s ease-in-out 1 forwards; }}")

    for c_idx in range(num_targets + 1):
        init_op = 1 if c_idx == 0 else 0
        css_class_rules.append(f".hud-val-{c_idx} {{ opacity: {init_op}; animation: hudCount{c_idx} {TOTAL_DURATION:.2f}s linear 1 forwards; }}")

    full_css = "\n".join(css_class_rules) + "\n\n" + "\n\n".join(keyframes_css)

    # Construct the 52x7 Grid SVG Elements
    grid_rects = []
    target_tuples = {}
    for t in targets_data:
        target_tuples.setdefault((t["col"], t["row"]), []).append(t["id"])

    for col in range(52):
        for row in range(7):
            x = col * 15
            y = row * 13
            cell = grid.get((col, row), {"lvl": 0})
            lvl = cell["lvl"]
            
            colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
            fill_color = colors[lvl]

            if (col, row) in target_tuples:
                tids = target_tuples[(col, row)]
                classes = " ".join(f"commit-target-{tid}" for tid in tids)
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" class="{classes}"/>')
            else:
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{fill_color}"/>')

    grid_content = "\n".join(grid_rects)

    svg_output = f'''<svg width="850" height="275" viewBox="0 0 850 275" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .bh-bg         {{ fill: #0B0C10; stroke: #1F2430; stroke-width: 1.5; }}
      .tag-txt       {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 11px; font-weight: 700; fill: #00F0FF; letter-spacing: 2px; }}
      .month-lbl     {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 9px; fill: #71737E; }}
      .day-lbl       {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 8.5px; fill: #71737E; }}
      .score-lbl     {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 9px; fill: #8B949E; }}

      @keyframes beaconBlink {{
        0%, 100% {{ opacity: 1; }}
        50%      {{ opacity: 0.2; }}
      }}

      {full_css}
    </style>
  </defs>

  <!-- Container Box -->
  <rect width="850" height="275" rx="4" class="bh-bg"/>

  <!-- Top Title Bar with Live Destroyed Counter HUD -->
  <g transform="translate(24, 22)">
    <circle cx="0" cy="5" r="3.5" fill="#39D353" class="live-beacon"/>
    <text x="14" y="9" class="tag-txt">PORTAL GATEWAY // SECTOR 03: RETRO LASER CANNON COMMIT ARCADE</text>
  </g>

  <!-- Live Counter HUD Badge displaying total commits -->
  <g transform="translate(565, 10)">
    <rect width="260" height="26" rx="3" class="counter-frame"/>
{counter_texts}
  </g>
  <line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B" stroke-width="1"/>

  <!-- 52x7 Real GitHub Contribution Matrix -->
  <g transform="translate(36, 62)">
    
    <!-- Month Labels -->
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

    <!-- Real Contribution Grid -->
    <g>
{grid_content}
    </g>

    <!-- Firing Lasers -->
    <g>
{lasers_content}
    </g>

    <!-- Hit Impact Sparks -->
    <g>
{sparks_content}
    </g>

    <!-- Rocket Cannon Patrol Ship -->
    <g class="ship-patrol">
      <g transform="translate(0, 0)">
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

  <!-- Bottom Legend Footer with Real Total Commits -->
  <g transform="translate(36, 252)">
    <rect x="0" y="0" width="9" height="9" rx="2" fill="#161B22"/>
    <text x="14" y="8" class="score-lbl">LEVEL 0 (DEPLETED)</text>

    <rect x="140" y="0" width="9" height="9" rx="2" fill="#0E4429"/>
    <text x="154" y="8" class="score-lbl">LEVEL 1</text>

    <rect x="240" y="0" width="9" height="9" rx="2" fill="#006D32"/>
    <text x="254" y="8" class="score-lbl">LEVEL 2</text>

    <rect x="350" y="0" width="9" height="9" rx="2" fill="#26A641"/>
    <text x="364" y="8" class="score-lbl">LEVEL 3</text>

    <rect x="450" y="0" width="9" height="9" rx="2" fill="#39D353"/>
    <text x="464" y="8" class="score-lbl" style="fill:#39D353; font-weight:bold;">LEVEL 4 (FULL LIGHT)</text>

    <text x="630" y="8" font-family="'JetBrains Mono', monospace" font-size="10.5px" font-weight="700" fill="#2563EB">{formatted_total} TOTAL COMMITS</text>
  </g>
</svg>
'''
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_output)
    print(f"Successfully wrote {output_path}")

    # Synchronize stats and telemetry SVGs
    sync_other_svgs(total_contribs)

if __name__ == "__main__":
    records, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if records:
        generate_svg(records, total_contribs)
    else:
        print("Error: Could not retrieve contribution records.")
