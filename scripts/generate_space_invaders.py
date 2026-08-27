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

    # Multi-round target selection across the contribution matrix
    # Round stages select diverse, realistic targets across different sectors of the grid
    round_selectors = [
        # Round 1: Early-year & Mid-year sectors
        [
            lambda c: c["lvl"] >= 2 and c["col"] < 12,
            lambda c: c["lvl"] >= 2 and c["col"] < 14,
            lambda c: c["lvl"] >= 2 and c["col"] > 40 and c["row"] >= 4,
            lambda c: c["lvl"] >= 1 and 26 <= c["col"] <= 38 and c["row"] >= 3,
            lambda c: c["lvl"] >= 1 and 26 <= c["col"] <= 38,
            lambda c: c["lvl"] >= 1 and 12 <= c["col"] <= 24 and c["row"] >= 4,
            lambda c: c["lvl"] >= 2 and 18 <= c["col"] <= 26,
            lambda c: c["lvl"] >= 1 and 22 <= c["col"] <= 32,
        ],
        # Round 2: Autumn & Winter sectors
        [
            lambda c: c["lvl"] >= 2 and 6 <= c["col"] <= 16,
            lambda c: c["lvl"] >= 2 and 36 <= c["col"] <= 46,
            lambda c: c["lvl"] >= 3 and c["col"] >= 15,
            lambda c: c["lvl"] >= 1 and 40 <= c["col"] <= 51 and c["row"] <= 3,
            lambda c: c["lvl"] >= 2 and 10 <= c["col"] <= 20,
            lambda c: c["lvl"] >= 1 and 28 <= c["col"] <= 38 and c["row"] <= 2,
            lambda c: c["lvl"] >= 2 and 44 <= c["col"] <= 51,
            lambda c: c["lvl"] >= 1 and c["col"] <= 10,
        ],
        # Round 3: Spring & Summer sectors
        [
            lambda c: c["lvl"] >= 2 and 20 <= c["col"] <= 30,
            lambda c: c["lvl"] >= 1 and 30 <= c["col"] <= 40,
            lambda c: c["lvl"] >= 2 and 2 <= c["col"] <= 12,
            lambda c: c["lvl"] >= 2 and 42 <= c["col"] <= 50,
            lambda c: c["lvl"] >= 1 and 14 <= c["col"] <= 24,
            lambda c: c["lvl"] >= 3 and 25 <= c["col"] <= 35,
            lambda c: c["lvl"] >= 1 and 35 <= c["col"] <= 45,
            lambda c: c["lvl"] >= 2 and 8 <= c["col"] <= 18,
        ],
        # Round 4: High intensity clusters
        [
            lambda c: c["lvl"] >= 3 and c["col"] < 25,
            lambda c: c["lvl"] >= 3 and c["col"] >= 25,
            lambda c: c["lvl"] >= 2 and 15 <= c["col"] <= 28,
            lambda c: c["lvl"] >= 2 and 32 <= c["col"] <= 48,
            lambda c: c["lvl"] >= 1 and c["col"] <= 15,
            lambda c: c["lvl"] >= 2 and 22 <= c["col"] <= 36,
            lambda c: c["lvl"] >= 1 and 45 <= c["col"] <= 51,
            lambda c: c["lvl"] >= 2 and 5 <= c["col"] <= 20,
        ],
        # Round 5: Full spectrum sweep
        [
            lambda c: c["lvl"] >= 2 and 4 <= c["col"] <= 14,
            lambda c: c["lvl"] >= 1 and 16 <= c["col"] <= 26,
            lambda c: c["lvl"] >= 2 and 28 <= c["col"] <= 38,
            lambda c: c["lvl"] >= 2 and 40 <= c["col"] <= 50,
            lambda c: c["lvl"] >= 1 and 8 <= c["col"] <= 18,
            lambda c: c["lvl"] >= 2 and 20 <= c["col"] <= 32,
            lambda c: c["lvl"] >= 1 and 34 <= c["col"] <= 44,
            lambda c: c["lvl"] >= 3 and c["col"] >= 10,
        ]
    ]

    all_attack_targets = []
    used_in_round = set()

    for r_idx, stage_fns in enumerate(round_selectors):
        round_targets = []
        for stage_fn in stage_fns:
            candidates = [c for c in active_cells if stage_fn(c) and (c["col"], c["row"]) not in used_in_round]
            if not candidates:
                candidates = [c for c in active_cells if stage_fn(c)]
            if not candidates:
                candidates = [c for c in active_cells if (c["col"], c["row"]) not in used_in_round]
            if not candidates:
                candidates = active_cells

            selected = candidates[len(round_targets) % len(candidates)]
            round_targets.append(selected)
            used_in_round.add((selected["col"], selected["row"]))

        all_attack_targets.extend(round_targets)
        used_in_round.clear()

    TOTAL_ATTACKS = len(all_attack_targets)
    print(f"Generated continuous multi-round attack sequence with {TOTAL_ATTACKS} hits.")

    # Target sequence with hit IDs (1 to TOTAL_ATTACKS)
    targets_data = []
    cell_state_map = {} # (col, row) -> current animated level
    for idx, t in enumerate(all_attack_targets):
        key = (t["col"], t["row"])
        if key not in cell_state_map:
            cell_state_map[key] = t["lvl"]
        
        start_lvl = cell_state_map[key]
        damaged_lvl = max(0, start_lvl - 1)
        cell_state_map[key] = damaged_lvl

        targets_data.append({
            "id": idx + 1,
            "col": t["col"],
            "row": t["row"],
            "lvl": t["lvl"],
            "start_lvl": start_lvl,
            "damaged_lvl": damaged_lvl,
            "contributions": t["contributions"],
            "date": t["date"],
            "cx": t["cx"],
            "cy": t["cy"],
            "x": t["col"] * 15,
            "y": t["row"] * 13
        })

    T_AIM      = 0.10
    T_LASER    = 0.16
    T_HIT      = 0.12
    T_POST_HIT = 0.50 # snappy ~0.5s post-hit delay
    ATTACK_SEQ_DURATION = T_AIM + T_LASER + T_HIT + T_POST_HIT # ~0.88s

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

    print(f"Total loop duration: {TOTAL_DURATION:.2f}s (~{TOTAL_DURATION/len(targets_data):.2f}s per attack)")

    cycle_start_times = [0.0]
    for d in cycle_durations[:-1]:
        cycle_start_times.append(cycle_start_times[-1] + d)

    def to_pct(seconds):
        pct = (seconds / TOTAL_DURATION) * 100.0
        pct = max(0.0, min(100.0, pct))
        return f"{pct:.3f}%"

    keyframes_css = []

    # 1. Rocket Movement Route Keyframes across all attacks
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

    # 2. Lasers & Spark Burst Keyframes for each attack
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

    # 3. Grid Cell Damage Keyframes per targeted cell
    dim_colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
    # Group hits by grid coordinate (col, row)
    cell_hits_map = {}
    for i, t in enumerate(targets_data):
        key = (t["col"], t["row"])
        if key not in cell_hits_map:
            cell_hits_map[key] = []
        
        t_start = cycle_start_times[i]
        t_arrive = t_start + travel_durations[i]
        t_fire_hit = t_arrive + T_AIM + T_LASER
        
        cell_hits_map[key].append({
            "hit_time": t_fire_hit,
            "start_lvl": t["start_lvl"],
            "damaged_lvl": t["damaged_lvl"],
            "orig_lvl": t["lvl"]
        })

    for (col, row), hits in cell_hits_map.items():
        cell_id = f"c_{col}_{row}"
        init_lvl = hits[0]["orig_lvl"]
        init_color = dim_colors[init_lvl]
        
        cell_kfs = [f"  0% {{ fill: {init_color}; }}"]
        for h in hits:
            t_hit = h["hit_time"]
            curr_col = dim_colors[h["start_lvl"]]
            dmg_col = dim_colors[h["damaged_lvl"]]
            cell_kfs.append(f"  {to_pct(t_hit - 0.01)} {{ fill: {curr_col}; }}")
            cell_kfs.append(f"  {to_pct(t_hit)} {{ fill: #FDFBF7; }}")
            cell_kfs.append(f"  {to_pct(t_hit + 0.05)} {{ fill: {dmg_col}; }}")
        
        cell_kfs.append(f"  {to_pct(TOTAL_DURATION - 0.05)} {{ fill: {dim_colors[hits[-1]['damaged_lvl']]}; }}")
        cell_kfs.append(f"  100% {{ fill: {init_color}; }}")
        
        cell_kf_str = "\n".join(cell_kfs)
        keyframes_css.append(f'''@keyframes commitDamage_{cell_id} {{
{cell_kf_str}
}}''')

    # 4. Continuous Destroyed HUD Counter Keyframes (0 -> 1 -> 2 -> ... -> TOTAL_ATTACKS)
    for c_val in range(TOTAL_ATTACKS + 1):
        if c_val == 0:
            t_visible_end = cycle_start_times[0] + travel_durations[0] + T_AIM + T_LASER
            counter_kf = f'''@keyframes hudCount0 {{
  0% {{ opacity: 1; }}
  {to_pct(t_visible_end - 0.01)} {{ opacity: 1; }}
  {to_pct(t_visible_end)} {{ opacity: 0; }}
  100% {{ opacity: 0; }}
}}'''
        elif c_val < TOTAL_ATTACKS:
            t_visible_start = cycle_start_times[c_val-1] + travel_durations[c_val-1] + T_AIM + T_LASER
            t_visible_end = cycle_start_times[c_val] + travel_durations[c_val] + T_AIM + T_LASER
            counter_kf = f'''@keyframes hudCount{c_val} {{
  0% {{ opacity: 0; }}
  {to_pct(t_visible_start - 0.01)} {{ opacity: 0; }}
  {to_pct(t_visible_start)} {{ opacity: 1; }}
  {to_pct(t_visible_end - 0.01)} {{ opacity: 1; }}
  {to_pct(t_visible_end)} {{ opacity: 0; }}
  100% {{ opacity: 0; }}
}}'''
        else:
            t_visible_start = cycle_start_times[TOTAL_ATTACKS-1] + travel_durations[TOTAL_ATTACKS-1] + T_AIM + T_LASER
            counter_kf = f'''@keyframes hudCount{TOTAL_ATTACKS} {{
  0% {{ opacity: 0; }}
  {to_pct(t_visible_start - 0.01)} {{ opacity: 0; }}
  {to_pct(t_visible_start)} {{ opacity: 1; }}
  {to_pct(TOTAL_DURATION - 0.01)} {{ opacity: 1; }}
  100% {{ opacity: 1; }}
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

    # Counter Text Display Elements (Starts from 0 and increments continuously 1 per hit: 0 -> 1 -> 2 -> ... -> TOTAL_ATTACKS)
    counter_elements = []
    for c_val in range(TOTAL_ATTACKS + 1):
        counter_elements.append(f'      <text x="127" y="17" text-anchor="middle" class="counter-txt hud-val-{c_val}">DESTROYED: [ {c_val} / {formatted_total} COMMITS ]</text>')
    counter_texts = "\n".join(counter_elements)

    # CSS Rules
    css_class_rules = [
        f".ship-patrol {{ animation: shipPatrolRoute {TOTAL_DURATION:.2f}s cubic-bezier(0.25, 0, 0.15, 1) infinite; }}",
        ".live-beacon { animation: beaconBlink 0.8s steps(2, start) infinite; }",
        ".counter-frame { fill: #111216; stroke: #2563EB; stroke-width: 1.2; }",
        ".counter-txt { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10px; font-weight: 700; fill: #39D353; letter-spacing: 0.8px; }"
    ]
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        css_class_rules.append(f".laser-bolt-{tid}   {{ animation: laserShot{tid} {TOTAL_DURATION:.2f}s linear infinite; }}")
        css_class_rules.append(f".spark-burst-{tid}  {{ animation: sparkHit{tid} {TOTAL_DURATION:.2f}s ease-out infinite; transform-origin: {cx}px {cy}px; }}")

    for (col, row) in cell_hits_map.keys():
        cell_id = f"c_{col}_{row}"
        css_class_rules.append(f".commit-cell-{cell_id} {{ animation: commitDamage_{cell_id} {TOTAL_DURATION:.2f}s ease-in-out infinite; }}")

    for c_val in range(TOTAL_ATTACKS + 1):
        init_op = 1 if c_val == 0 else 0
        css_class_rules.append(f".hud-val-{c_val} {{ opacity: {init_op}; animation: hudCount{c_val} {TOTAL_DURATION:.2f}s linear infinite; }}")

    full_css = "\n".join(css_class_rules) + "\n\n" + "\n\n".join(keyframes_css)

    # Construct the 52x7 Grid SVG Elements
    grid_rects = []
    targeted_cell_set = set(cell_hits_map.keys())

    for col in range(52):
        for row in range(7):
            x = col * 15
            y = row * 13
            cell = grid.get((col, row), {"lvl": 0})
            lvl = cell["lvl"]
            
            colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
            fill_color = colors[lvl]

            if (col, row) in targeted_cell_set:
                cell_id = f"c_{col}_{row}"
                grid_rects.append(f'      <rect x="{x}" y="{y}" width="10" height="10" rx="2" class="commit-cell-{cell_id}"/>')
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
