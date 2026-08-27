#!/usr/bin/env python3
import urllib.request
import json
import re
import os
import datetime

USERNAME = "YashRaut24"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_contributions(username, token=""):
    """
    Fetch real GitHub contributions calendar and lifetime total contributions for user.
    """
    total_contribs = 1937
    date_dict = {}

    if token:
        try:
            # Query all contribution years via GraphQL
            years_query = """
            query($username: String!) {
              user(login: $username) {
                contributionsCollection {
                  contributionYears
                }
              }
            }
            """
            req_data = json.dumps({"query": years_query, "variables": {"username": username}}).encode('utf-8')
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Space-Invaders-Generator",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                years = res["data"]["user"]["contributionsCollection"]["contributionYears"]
                
                # Fetch calendar for current year
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
                    }
                  }
                }
                """
                req_data2 = json.dumps({"query": cal_query, "variables": {"username": username}}).encode('utf-8')
                req2 = urllib.request.Request(
                    "https://api.github.com/graphql",
                    data=req_data2,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": "Space-Invaders-Generator",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req2) as resp2:
                    res2 = json.loads(resp2.read().decode('utf-8'))
                    calendar = res2["data"]["user"]["contributionsCollection"]["contributionCalendar"]
                    level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
                    for week in calendar["weeks"]:
                        for day in week["contributionDays"]:
                            lvl = level_map.get(day["contributionLevel"], 0)
                            date_dict[day["date"]] = lvl
                    
                    total_contribs = max(1937, calendar["totalContributions"])
                    print(f"Fetched {len(date_dict)} days via GitHub GraphQL API. Total: {total_contribs}")
                    return date_dict, total_contribs
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Falling back to calendar endpoint...")

    # Fallback to contributions calendar endpoint
    try:
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
        
        m = re.search(r'([0-9,]+)\s+contributions\s+in', html)
        if m:
            total_contribs = max(1937, int(m.group(1).replace(",", "")))
        
        matches = re.findall(r'data-date="([^"]+)"(?:\s+[^>]*?)?data-level="([^"]+)"', html)
        if not matches:
            matches = re.findall(r'data-level="([^"]+)"(?:\s+[^>]*?)?data-date="([^"]+)"', html)
            matches = [(d, l) for l, d in matches]
        
        date_dict = {d: int(l) for d, l in matches}
        print(f"Fetched {len(date_dict)} real dates from GitHub. Total contributions: {total_contribs}")
        return date_dict, total_contribs
    except Exception as e:
        print(f"Calendar fetch failed: {e}")
        return {}, 1937

def sync_other_svgs(total_contribs):
    """
    Keep assets/space-portal-stats.svg and assets/space-portal-telemetry.svg in sync with total_contribs.
    """
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

def generate_svg(date_dict, total_contribs=1937, output_path="assets/space-invaders-commits.svg"):
    if not date_dict:
        raise ValueError("No contribution dates provided")

    sorted_dates = sorted([datetime.date.fromisoformat(d) for d in date_dict.keys()])
    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]

    first_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)
    
    grid = {}
    for d_str, lvl in date_dict.items():
        d = datetime.date.fromisoformat(d_str)
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < 52 and 0 <= row < 7:
            grid[(col, row)] = (lvl, d_str)

    active_cells = []
    for (col, row), (lvl, d_str) in grid.items():
        if lvl > 0:
            active_cells.append({
                "col": col,
                "row": row,
                "lvl": lvl,
                "date": d_str,
                "cx": col * 15 + 5,
                "cy": row * 13 + 5
            })

    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")

    targets = []
    preferred_stages = [
        lambda c: c["lvl"] >= 2 and c["col"] < 12,
        lambda c: c["lvl"] >= 2 and c["col"] < 14 and c not in targets,
        lambda c: c["lvl"] >= 2 and c["col"] > 40 and c["row"] >= 4,
        lambda c: c["lvl"] >= 1 and 26 <= c["col"] <= 38 and c["row"] >= 3,
        lambda c: c["lvl"] >= 1 and 26 <= c["col"] <= 38 and c not in targets,
        lambda c: c["lvl"] >= 1 and 12 <= c["col"] <= 24 and c["row"] >= 4,
        lambda c: c["lvl"] >= 2 and 18 <= c["col"] <= 26 and c not in targets,
        lambda c: c["lvl"] >= 1 and 22 <= c["col"] <= 32 and c not in targets,
    ]

    for stage_fn in preferred_stages:
        candidates = [c for c in active_cells if stage_fn(c) and c not in targets]
        if candidates:
            targets.append(candidates[0])
        else:
            remaining = [c for c in active_cells if c not in targets]
            if remaining:
                targets.append(remaining[len(remaining)//2])

    targets = targets[:8]
    while len(targets) < 8:
        targets.append(active_cells[len(targets) % len(active_cells)])

    print(f"Selected {len(targets)} real targets:")
    for idx, t in enumerate(targets):
        print(f"  Target {idx+1}: Col {t['col']}, Row {t['row']}, Level {t['lvl']}, Date {t['date']}")

    targets_data = []
    for idx, t in enumerate(targets):
        targets_data.append({
            "id": idx + 1,
            "col": t["col"],
            "row": t["row"],
            "lvl": t["lvl"],
            "date": t["date"],
            "cx": t["cx"],
            "cy": t["cy"],
            "x": t["col"] * 15,
            "y": t["row"] * 13
        })

    T_AIM      = 0.10
    T_LASER    = 0.16
    T_HIT      = 0.12
    T_POST_HIT = 1.10
    ATTACK_SEQ_DURATION = T_AIM + T_LASER + T_HIT + T_POST_HIT # ~1.48s

    cannon_y = 126
    travel_durations = []
    for i in range(8):
        prev_cx = targets_data[i-1]["cx"] if i > 0 else 425 - 36
        curr_cx = targets_data[i]["cx"]
        dx = abs(curr_cx - prev_cx)
        t_travel = 0.35 + min(0.40, (dx / 780.0) * 0.40)
        travel_durations.append(t_travel)

    cycle_durations = [travel_durations[i] + ATTACK_SEQ_DURATION for i in range(8)]
    TOTAL_DURATION = sum(cycle_durations)

    print(f"Total loop duration: {TOTAL_DURATION:.2f}s (~{TOTAL_DURATION/8.0:.2f}s per attack)")

    cycle_start_times = [0.0]
    for d in cycle_durations[:-1]:
        cycle_start_times.append(cycle_start_times[-1] + d)

    def to_pct(seconds):
        return f"{(seconds / TOTAL_DURATION) * 100.0:.3f}%"

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

    # 2. Laser & Burst & Commit Damage Keyframes for each target
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

        orig_lvl = t["lvl"]
        dim_lvl = max(0, orig_lvl - 1)
        dim_colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
        orig_color = dim_colors[orig_lvl]
        target_color = dim_colors[dim_lvl]

        commit_kf = f'''@keyframes commitDamage{tid} {{
  0% {{ fill: {orig_color}; }}
  {to_pct(t_fire_hit - 0.01)} {{ fill: {orig_color}; }}
  {to_pct(t_fire_hit)}        {{ fill: #FDFBF7; }}
  {to_pct(t_fire_hit + 0.06)} {{ fill: {target_color}; opacity: 0.85; }}
  {to_pct(TOTAL_DURATION - 0.05)} {{ fill: {target_color}; }}
  100% {{ fill: {orig_color}; }}
}}'''
        keyframes_css.append(commit_kf)

    # 3. Dynamic Live Destroyed HUD Counter Keyframes
    for c_val in range(9):
        if c_val == 0:
            t_visible_start = 0.0
            t_visible_end = cycle_start_times[0] + travel_durations[0] + T_AIM + T_LASER
        elif c_val < 8:
            t_visible_start = cycle_start_times[c_val-1] + travel_durations[c_val-1] + T_AIM + T_LASER
            t_visible_end = cycle_start_times[c_val] + travel_durations[c_val] + T_AIM + T_LASER
        else:
            t_visible_start = cycle_start_times[7] + travel_durations[7] + T_AIM + T_LASER
            t_visible_end = TOTAL_DURATION

        counter_kf = f'''@keyframes hudCount{c_val} {{
  0% {{ opacity: {1 if c_val == 0 else 0}; }}
  {to_pct(max(0.0, t_visible_start - 0.02))} {{ opacity: 0; }}
  {to_pct(t_visible_start)}                 {{ opacity: 1; }}
  {to_pct(t_visible_end - 0.02)}             {{ opacity: 1; }}
  {to_pct(t_visible_end)}                   {{ opacity: 0; }}
  100% {{ opacity: {1 if c_val == 8 else 0}; }}
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

    # Counter Text Display Elements (Iterates proportionally from 0 to Total Commits!)
    counter_elements = []
    for c_val in range(9):
        curr_val = int(round((c_val / 8.0) * total_contribs))
        counter_elements.append(f'      <text x="12" y="17" class="counter-txt hud-val-{c_val}">DESTROYED: [ {curr_val:,} / {formatted_total} COMMITS ]</text>')
    counter_texts = "\n".join(counter_elements)

    # CSS Rules
    css_class_rules = [
        f".ship-patrol {{ animation: shipPatrolRoute {TOTAL_DURATION:.2f}s cubic-bezier(0.25, 0, 0.15, 1) infinite; }}",
        ".live-beacon {{ animation: beaconBlink 0.8s steps(2, start) infinite; }}",
        ".counter-frame {{ fill: #16171C; stroke: #2563EB; stroke-width: 1.2; }}",
        ".counter-txt {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10px; font-weight: 700; fill: #39D353; letter-spacing: 0.8px; }}"
    ]
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        css_class_rules.append(f".laser-bolt-{tid}   {{ animation: laserShot{tid} {TOTAL_DURATION:.2f}s linear infinite; }}")
        css_class_rules.append(f".spark-burst-{tid}  {{ animation: sparkHit{tid} {TOTAL_DURATION:.2f}s ease-out infinite; transform-origin: {cx}px {cy}px; }}")
        css_class_rules.append(f".commit-target-{tid} {{ animation: commitDamage{tid} {TOTAL_DURATION:.2f}s ease-in-out infinite; }}")

    for c_val in range(9):
        css_class_rules.append(f".hud-val-{c_val} {{ animation: hudCount{c_val} {TOTAL_DURATION:.2f}s steps(1, start) infinite; }}")

    full_css = "\n".join(css_class_rules) + "\n\n" + "\n\n".join(keyframes_css)

    # Construct the 52x7 Grid SVG Elements
    grid_rects = []
    target_tuples = {(t["col"], t["row"]): t["id"] for t in targets_data}

    for col in range(52):
        for row in range(7):
            x = col * 15
            y = row * 13
            cell_data = grid.get((col, row), (0, ""))
            lvl = cell_data[0]
            
            colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
            fill_color = colors[lvl]

            if (col, row) in target_tuples:
                tid = target_tuples[(col, row)]
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" class="commit-target-{tid}"/>')
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
    
    <!-- Live Counter HUD Badge displaying total commits -->
    <g transform="translate(560, -8)">
      <rect width="250" height="26" rx="3" class="counter-frame"/>
{counter_texts}
    </g>
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
    date_dict, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if date_dict:
        generate_svg(date_dict, total_contribs)
    else:
        print("Error: Could not retrieve contribution dates.")
