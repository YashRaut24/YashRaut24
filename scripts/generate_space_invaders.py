import urllib.request
import json
import os
import re
from datetime import datetime, timedelta

USERNAME = "YashRaut24"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", os.environ.get("METRICS_TOKEN", ""))

def fetch_contributions(username, token=""):
    """
    Fetch real GitHub contributions calendar for user.
    """
    if token:
        try:
            graphql_query = """
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
            req_data = json.dumps({"query": graphql_query, "variables": {"username": username}}).encode('utf-8')
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
                calendar = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
                date_dict = {}
                level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
                for week in calendar["weeks"]:
                    for day in week["contributionDays"]:
                        lvl = level_map.get(day["contributionLevel"], 0)
                        date_dict[day["date"]] = lvl
                print(f"Fetched {len(date_dict)} days via GitHub GraphQL API.")
                return date_dict
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Falling back to calendar endpoint...")

    # Fallback to contributions calendar endpoint
    try:
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
        
        matches = re.findall(r'data-date="([^"]+)"(?:\s+[^>]*?)?data-level="([^"]+)"', html)
        if not matches:
            matches = re.findall(r'data-level="([^"]+)"(?:\s+[^>]*?)?data-date="([^"]+)"', html)
            matches = [(d, l) for l, d in matches]
        
        date_dict = {d: int(l) for d, l in matches}
        print(f"Fetched {len(date_dict)} real contribution dates from GitHub.")
        return date_dict
    except Exception as e:
        print(f"Calendar fetch failed: {e}")
        return {}

def generate_svg(date_dict, output_path="assets/space-invaders-commits.svg"):
    if not date_dict:
        raise ValueError("No contribution dates provided")

    LEVEL_COLORS = {
        0: "#161B22",
        1: "#0E4429",
        2: "#006D32",
        3: "#26A641",
        4: "#39D353"
    }

    # Construct the exact 52-week calendar (Sunday = row 0, Saturday = row 6)
    sorted_dates = sorted(date_dict.keys())
    end_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")
    
    # Get last Sunday
    days_since_sunday = (end_date.weekday() + 1) % 7
    last_sunday = end_date - timedelta(days=days_since_sunday)
    first_sunday = last_sunday - timedelta(weeks=51)

    grid_matrix = [] # 52 cols x 7 rows
    active_cells = []

    for col in range(52):
        week_start = first_sunday + timedelta(weeks=col)
        for row in range(7): # 0 = Sunday ... 6 = Saturday
            day_date = week_start + timedelta(days=row)
            day_str = day_date.strftime("%Y-%m-%d")
            lvl = date_dict.get(day_str, 0)
            cell = {
                "col": col,
                "row": row,
                "level": lvl,
                "date": day_str
            }
            grid_matrix.append(cell)
            if lvl >= 1 and 2 <= col <= 50:
                active_cells.append(cell)

    print(f"Generated 52x7 grid spanning {first_sunday.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")

    # Select 8 hybrid arcade targets from actual active cells
    rows_active = {}
    for c in active_cells:
        rows_active.setdefault(c["row"], []).append(c)
    for r in rows_active:
        rows_active[r].sort(key=lambda x: x["col"])

    chosen = []
    # Row Sweep 1
    if 1 in rows_active and len(rows_active[1]) >= 2:
        chosen.extend(rows_active[1][:2])
    elif active_cells:
        chosen.append(active_cells[0])

    # Random Jump 1
    jump_1 = [c for c in active_cells if c["col"] >= 25 and c["row"] != 1]
    if jump_1:
        chosen.append(jump_1[len(jump_1)//2])

    # Row Sweep 2
    if 4 in rows_active and len(rows_active[4]) >= 2:
        cands = [c for c in rows_active[4] if 20 <= c["col"] <= 48]
        if len(cands) >= 2:
            chosen.extend(cands[:2])
        elif len(rows_active[4]) >= 2:
            chosen.extend(rows_active[4][:2])

    # Random Jump 2
    jump_2 = [c for c in active_cells if 10 <= c["col"] <= 25 and c["row"] not in [1, 4]]
    if jump_2:
        chosen.append(jump_2[0])

    # Row Sweep 3
    if 2 in rows_active and len(rows_active[2]) >= 2:
        cands = [c for c in rows_active[2] if c["col"] >= 20]
        if len(cands) >= 2:
            chosen.extend(cands[:2])

    # Fill up to 8 targets if needed
    for c in active_cells:
        if len(chosen) >= 8:
            break
        if c not in chosen:
            chosen.append(c)

    chosen = chosen[:8]
    print(f"Selected {len(chosen)} real targets:")
    for i, t in enumerate(chosen):
        print(f"  Target {i+1}: Col {t['col']}, Row {t['row']}, Level {t['level']}, Date {t['date']}")

    # PROMINENT SHIFT DOWN:
    # Row 6 is at y = 78-88.
    # We place the rocket body at y = 126 (Cannon Tip at y = 116).
    # This leaves 28px of crisp dark space between bottom commit and rocket tip!
    CANNON_Y = 116
    ROCKET_Y = 126

    # TIMING:
    # dt_pause = 1.20s (Solid, prominent pause after hit!)
    # dt_move = 0.35s to 0.60s
    # dt_aim = 0.10s
    # dt_laser = 0.16s
    # dt_hit = 0.14s
    targets_data = []
    for i, c in enumerate(chosen):
        init_lvl = c["level"]
        new_lvl = max(0, init_lvl - 1)
        init_color = LEVEL_COLORS[init_lvl]
        new_color = LEVEL_COLORS[new_lvl]
        
        if i == 0:
            prev_col = chosen[-1]["col"]
        else:
            prev_col = chosen[i-1]["col"]
        col_dist = abs(c["col"] - prev_col)
        dt_move = 0.35 + min(0.25, (col_dist / 52.0) * 0.40) # 0.35s to 0.60s
        
        targets_data.append({
            "id": i + 1,
            "col": c["col"],
            "row": c["row"],
            "init_lvl": init_lvl,
            "new_lvl": new_lvl,
            "init_color": init_color,
            "new_color": new_color,
            "dt_move": dt_move,
            "dt_aim": 0.10,
            "dt_laser": 0.16,
            "dt_hit": 0.14,
            "dt_pause": 1.20  # Unambiguous 1.2s pause after hit!
        })

    # Compute timeline
    cur_t = 0.0
    for t in targets_data:
        t["x"] = t["col"] * 15
        t["y"] = t["row"] * 13
        t["cx"] = t["x"] + 5
        t["cy"] = t["y"] + 5
        t["laser_dist"] = CANNON_Y - t["cy"]
        
        t["t_start"] = cur_t
        t["t_arrive"] = cur_t + t["dt_move"]
        t["t_fire"] = t["t_arrive"] + t["dt_aim"]
        t["t_hit"] = t["t_fire"] + t["dt_laser"]
        t["t_settle"] = t["t_hit"] + t["dt_hit"]
        t["t_end"] = t["t_settle"] + t["dt_pause"]
        cur_t = t["t_end"]

    TOTAL_DURATION = cur_t
    print(f"Total loop duration: {TOTAL_DURATION:.2f}s (~{TOTAL_DURATION/len(targets_data):.2f}s per attack)")

    # Percentages
    for t in targets_data:
        t["p_start"] = (t["t_start"] / TOTAL_DURATION) * 100.0
        t["p_arrive"] = (t["t_arrive"] / TOTAL_DURATION) * 100.0
        t["p_fire"] = (t["t_fire"] / TOTAL_DURATION) * 100.0
        t["p_hit"] = (t["t_hit"] / TOTAL_DURATION) * 100.0
        t["p_settle"] = (t["t_settle"] / TOTAL_DURATION) * 100.0
        t["p_end"] = (t["t_end"] / TOTAL_DURATION) * 100.0

    # Keyframes
    keyframes_css = []

    # Rocket Keyframes
    ship_kf = []
    for t in targets_data:
        ship_kf.append(f"  {t['p_start']:.2f}% {{ transform: translateX({t['x']}px); }}")
        ship_kf.append(f"  {t['p_arrive']:.2f}% {{ transform: translateX({t['x']}px); }}")
        ship_kf.append(f"  {t['p_end']:.2f}% {{ transform: translateX({t['x']}px); }}")
    ship_kf.append(f"  100% {{ transform: translateX({targets_data[0]['x']}px); }}")
    keyframes_css.append("@keyframes shipPatrolRoute {\n" + "\n".join(ship_kf) + "\n}")

    # Laser Keyframes
    for t in targets_data:
        tid = t["id"]
        pf = t["p_fire"]
        ph = t["p_hit"]
        dist = t["laser_dist"]
        laser_kf = [
            f"  0%, {pf - 0.01:.2f}% {{ opacity: 0; transform: translateY(0px); }}",
            f"  {pf:.2f}% {{ opacity: 1; transform: translateY(0px); }}",
            f"  {ph - 0.02:.2f}% {{ opacity: 1; transform: translateY(-{dist}px); }}",
            f"  {ph:.2f}%, 100% {{ opacity: 0; transform: translateY(-{dist}px); }}"
        ]
        keyframes_css.append(f"@keyframes laserShot{tid} {{\n" + "\n".join(laser_kf) + "\n}")

    # Spark Keyframes
    for t in targets_data:
        tid = t["id"]
        ph = t["p_hit"]
        ps = t["p_settle"]
        spark_kf = [
            f"  0%, {ph - 0.01:.2f}% {{ opacity: 0; transform: scale(0.2); }}",
            f"  {ph:.2f}% {{ opacity: 1; transform: scale(0.6); }}",
            f"  {(ph+ps)/2:.2f}% {{ opacity: 1; transform: scale(1.6); }}",
            f"  {ps:.2f}%, 100% {{ opacity: 0; transform: scale(0.2); }}"
        ]
        keyframes_css.append(f"@keyframes sparkHit{tid} {{\n" + "\n".join(spark_kf) + "\n}")

    # Damage Keyframes
    for t in targets_data:
        tid = t["id"]
        ph = t["p_hit"]
        ps = t["p_settle"]
        init_c = t["init_color"]
        new_c = t["new_color"]
        damage_kf = [
            f"  0%, {ph - 0.01:.2f}% {{ fill: {init_c}; stroke: none; }}",
            f"  {ph:.2f}% {{ fill: #FDFBF7; stroke: #F59E0B; stroke-width: 1.5; }}",
            f"  {ps:.2f}% {{ fill: {new_c}; stroke: none; }}",
            f"  98.8% {{ fill: {new_c}; stroke: none; }}",
            f"  100% {{ fill: {init_c}; stroke: none; }}"
        ]
        keyframes_css.append(f"@keyframes commitDamage{tid} {{\n" + "\n".join(damage_kf) + "\n}")

    # Distinct Text Keyframes for Counter HUD
    for c_val in range(9):
        if c_val == 0:
            p_on = 0.0
            p_off = targets_data[0]["p_hit"]
        elif c_val < 8:
            p_on = targets_data[c_val - 1]["p_hit"]
            p_off = targets_data[c_val]["p_hit"]
        else: # 8
            p_on = targets_data[7]["p_hit"]
            p_off = 99.2

        cnt_kf = [
            f"  0%, {max(0, p_on - 0.01):.2f}% {{ opacity: 0; }}",
            f"  {p_on:.2f}%, {p_off - 0.01:.2f}% {{ opacity: 1; }}",
            f"  {p_off:.2f}%, 100% {{ opacity: 0; }}"
        ]
        keyframes_css.append(f"@keyframes hudScore{c_val} {{\n" + "\n".join(cnt_kf) + "\n}")

    # Grid Rects
    target_map = {(t["col"], t["row"]): t for t in targets_data}
    grid_rects = []
    for cell in grid_matrix:
        col = cell["col"]
        row = cell["row"]
        x = col * 15
        y = row * 13
        if (col, row) in target_map:
            t = target_map[(col, row)]
            grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" class="commit-target-{t["id"]}"/>')
        else:
            color = LEVEL_COLORS[cell["level"]]
            grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{color}"/>')
    grid_content = "\n".join(grid_rects)

    # Laser elements (from CANNON_Y = 116)
    laser_elements = []
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        laser_elements.append(f'''    <!-- Laser {tid} targeting Col {t["col"]}, Row {t["row"]} -->
    <g class="laser-bolt-{tid}">
      <line x1="{cx}" y1="{CANNON_Y}" x2="{cx}" y2="{CANNON_Y - 14}" stroke="#E11D48" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="{cx}" y1="{CANNON_Y}" x2="{cx}" y2="{CANNON_Y - 14}" stroke="#FDFBF7" stroke-width="1.2" stroke-linecap="round"/>
    </g>''')
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

    # Counter Text Display Elements (Dedicated text elements with absolute positioning inside badge)
    counter_elements = []
    for c_val in range(9):
        counter_elements.append(f'      <text x="12" y="17" class="counter-txt hud-val-{c_val}">DESTROYED: [ {c_val} / 8 ] TARGETS</text>')
    counter_texts = "\n".join(counter_elements)

    # CSS Rules
    css_class_rules = [
        f".ship-patrol {{ animation: shipPatrolRoute {TOTAL_DURATION:.2f}s cubic-bezier(0.25, 0, 0.15, 1) infinite; }}",
        ".live-beacon { animation: beaconBlink 0.8s steps(2, start) infinite; }",
        ".counter-frame { fill: #16171C; stroke: #2563EB; stroke-width: 1.2; }",
        ".counter-txt { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10.5px; font-weight: 700; fill: #39D353; letter-spacing: 1px; }"
    ]
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        css_class_rules.append(f".laser-bolt-{tid}   {{ animation: laserShot{tid} {TOTAL_DURATION:.2f}s linear infinite; }}")
        css_class_rules.append(f".spark-burst-{tid}  {{ animation: sparkHit{tid} {TOTAL_DURATION:.2f}s ease-out infinite; transform-origin: {cx}px {cy}px; }}")
        css_class_rules.append(f".commit-target-{tid} {{ animation: commitDamage{tid} {TOTAL_DURATION:.2f}s ease-in-out infinite; }}")

    for c_val in range(9):
        css_class_rules.append(f".hud-val-{c_val} {{ animation: hudScore{c_val} {TOTAL_DURATION:.2f}s steps(1) infinite; }}")

    full_css = "\n      ".join(css_class_rules) + "\n\n      " + "\n\n      ".join(keyframes_css)

    svg_output = f'''<svg width="850" height="275" viewBox="0 0 850 275" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .bh-bg       {{ fill: #111215; stroke: #2C303B; stroke-width: 1.5; }}
      .tag-txt     {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 11px; font-weight: 700; fill: #FDFBF7; letter-spacing: 1.5px; }}
      .month-lbl   {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 9px; fill: #52545F; }}
      .score-lbl   {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 9.5px; fill: #71737E; }}

      @keyframes beaconBlink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.2; }} }}

      {full_css}
    </style>
  </defs>

  <!-- Container Box -->
  <rect width="850" height="275" rx="4" class="bh-bg"/>

  <!-- Top Title Bar with Live Destroyed Counter HUD -->
  <g transform="translate(24, 22)">
    <circle cx="0" cy="5" r="3.5" fill="#39D353" class="live-beacon"/>
    <text x="14" y="9" class="tag-txt">PLATE 03 // RETRO SPACE INVADERS: COMMIT BLAST ARCADE</text>
    
    <!-- Live Counter HUD Badge -->
    <g transform="translate(565, -8)">
      <rect width="245" height="26" rx="3" class="counter-frame"/>
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

    <!-- Fired Laser Projectile Bolts (Launching from shifted lowered cannon) -->
{lasers_content}

    <!-- Impact Spark Bursts on Targeted Commits -->
{sparks_content}

    <!-- Autonomous Rocket Spaceship shifted down with prominent breathing room -->
    <g class="ship-patrol">
      <g transform="translate(5, {ROCKET_Y})">
        <!-- Rocket Nose Cone (Cannon Tip at y = 116 relative to grid) -->
        <polygon points="0,-10 9,4 -9,4" fill="#FDFBF7"/>
        <!-- Rocket Body & Wings -->
        <rect x="-9" y="4" width="18" height="6" rx="1.5" fill="#2563EB"/>
        <rect x="-4" y="1" width="8" height="7" fill="#E11D48"/>
        <!-- Cockpit Window -->
        <circle cx="0" cy="-2" r="2" fill="#00F0FF"/>
        <!-- Rocket Thruster Flames -->
        <polygon points="-6,10 -4,15 -2,10" fill="#F59E0B"/>
        <polygon points="2,10 4,15 6,10" fill="#F59E0B"/>
      </g>
    </g>
  </g>

  <!-- Legend & Live Arcade Status -->
  <g transform="translate(36, 240)">
    <rect x="0" y="0" width="9" height="9" rx="2" fill="#161B22"/>
    <text x="14" y="8" class="score-lbl">LEVEL 0 (DEPLETED)</text>

    <rect x="150" y="0" width="9" height="9" rx="2" fill="#0E4429"/>
    <text x="164" y="8" class="score-lbl">LEVEL 1</text>

    <rect x="250" y="0" width="9" height="9" rx="2" fill="#006D32"/>
    <text x="264" y="8" class="score-lbl">LEVEL 2</text>

    <rect x="350" y="0" width="9" height="9" rx="2" fill="#26A641"/>
    <text x="364" y="8" class="score-lbl">LEVEL 3</text>

    <rect x="450" y="0" width="9" height="9" rx="2" fill="#39D353"/>
    <text x="464" y="8" class="score-lbl" style="fill:#39D353; font-weight:bold;">LEVEL 4 (FULL LIGHT)</text>

    <text x="630" y="8" font-family="'JetBrains Mono', monospace" font-size="10.5px" font-weight="700" fill="#2563EB">1,500+ COMMITS LOGGED</text>
  </g>
</svg>
'''
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(svg_output)
    print(f"Successfully wrote {output_path}")

if __name__ == "__main__":
    date_dict = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if date_dict:
        generate_svg(date_dict)
    else:
        print("Error: Could not retrieve contribution dates.")
