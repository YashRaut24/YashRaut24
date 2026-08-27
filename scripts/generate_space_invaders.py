import urllib.request
import json
import re
import os
import datetime
import time

USERNAME = "YashRaut24"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_contributions(username, token=""):
    """Fetch the same rolling one-year contribution calendar shown on GitHub.

    Priority 1: GitHub's own contribution-calendar HTML (the page is the source
               for the exact "contributions in the last year" number).
    Priority 2: GitHub GraphQL contributionCalendar (official API).
    Priority 3: Community API fallback if GitHub endpoints are temporarily
               unavailable.
    """

    # 1. GitHub's own contribution page. This gives the exact rolling-year
    # total shown in the profile UI and the corresponding per-day cells.
    try:
        url = f"https://github.com/users/{username}/contributions?_={int(time.time())}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Space-Invaders-Generator/1.0)",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")

        tooltips = {}
        for match in re.finditer(
            r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>',
            html,
            re.DOTALL,
        ):
            tooltips[match.group(1)] = re.sub(r"<[^>]+>", " ", match.group(2)).strip()

        records = {}
        for m in re.finditer(r'<td[^>]*data-date="([^"]+)"[^>]*>', html):
            td_tag = m.group(0)
            date_val = m.group(1)
            level_m = re.search(r'data-level="([^"]+)"', td_tag)
            id_m = re.search(r'id="([^"]+)"', td_tag)
            level_val = int(level_m.group(1)) if level_m else 0
            comp_id = id_m.group(1) if id_m else ""
            tt_text = tooltips.get(comp_id, "")
            cnt_m = re.search(r'(\d[\d,]*)\s+contribution', tt_text, re.IGNORECASE)
            cnt_val = int(cnt_m.group(1).replace(",", "")) if cnt_m else 0
            records[date_val] = {
                "date": date_val,
                "contributions": cnt_val,
                "level": level_val,
                "initial_level": level_val,
            }

        h2_m = re.search(r'([0-9,]+)\s+contributions?\s+in', html, re.IGNORECASE)
        h2_total = int(h2_m.group(1).replace(",", "")) if h2_m else 0
        sum_total = sum(r["contributions"] for r in records.values())

        # Prefer GitHub's displayed rolling-year total. If the heading cannot
        # be parsed, use the exact sum of the fetched daily contribution counts.
        total_contribs = h2_total if h2_total > 0 else sum_total
        if records and total_contribs > 0:
            print(
                f"Fetched {len(records)} days from GitHub contribution page. "
                f"Rolling last-year total: {total_contribs:,}"
            )
            return records, total_contribs
    except Exception as e:
        print(f"GitHub contribution page fetch failed: {e}. Trying GraphQL API...")

    # 2. Official GitHub GraphQL API fallback. contributionsCollection without
    # explicit from/to dates represents GitHub's rolling contribution calendar.
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
                }
              }
            }
            """
            req_data = json.dumps({
                "query": cal_query,
                "variables": {"username": username},
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Space-Invaders-Generator",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))

            if res.get("errors"):
                raise RuntimeError(res["errors"])

            col = res["data"]["user"]["contributionsCollection"]
            calendar = col["contributionCalendar"]
            level_map = {
                "NONE": 0,
                "FIRST_QUARTILE": 1,
                "SECOND_QUARTILE": 2,
                "THIRD_QUARTILE": 3,
                "FOURTH_QUARTILE": 4,
            }
            records = {}
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    cnt = int(day.get("contributionCount", 0))
                    lvl = level_map.get(day.get("contributionLevel"), 0)
                    d_str = day["date"]
                    records[d_str] = {
                        "date": d_str,
                        "contributions": cnt,
                        "level": lvl,
                        "initial_level": lvl,
                    }

            cal_total = int(calendar.get("totalContributions", 0))
            sum_total = sum(r["contributions"] for r in records.values())
            total_contribs = cal_total if cal_total > 0 else sum_total
            if records and total_contribs > 0:
                print(
                    f"Fetched {len(records)} days via GitHub GraphQL. "
                    f"Rolling last-year total: {total_contribs:,}"
                )
                return records, total_contribs
        except Exception as e:
            print(f"GitHub GraphQL fetch failed: {e}. Trying community API fallback...")

    # 3. Last-resort community API fallback. This remains dynamic and is never
    # hardcoded; it is only used when GitHub's own endpoints are unavailable.
    try:
        url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last&_={int(time.time())}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Space-Invaders-Generator", "Cache-Control": "no-cache"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw_contribs = data.get("contributions", [])
        records = {}
        for item in raw_contribs:
            d_str = item["date"]
            cnt = int(item.get("count", 0))
            lvl = int(item.get("level", 0))
            records[d_str] = {
                "date": d_str,
                "contributions": cnt,
                "level": lvl,
                "initial_level": lvl,
            }

        sum_total = sum(r["contributions"] for r in records.values())
        api_total = int(data.get("total", {}).get("lastYear", 0))
        total_contribs = api_total if api_total > 0 else sum_total
        if records and total_contribs > 0:
            print(
                f"Fetched {len(records)} days via community API fallback. "
                f"Rolling last-year total: {total_contribs:,}"
            )
            return records, total_contribs
    except Exception as e:
        print(f"Community contribution API fallback failed: {e}")

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
    # Generate the arcade SVG from the real rolling one-year GitHub contribution calendar.
    # The contribution data is the source of truth for the matrix and denominator.
    # The rocket animation uses a small set of real active cells as visual targets,
    # while the HUD counter is an independent persistent hit counter from 0 through
    # the real one-year total. The counter never resets when the visual route loops.
    if not date_records:
        raise ValueError("No contribution records provided")
    if total_contribs <= 0:
        total_contribs = sum(r.get("contributions", 0) for r in date_records.values())
    if total_contribs <= 0:
        raise ValueError("No positive contribution total provided")

    sorted_dates = sorted(datetime.date.fromisoformat(d) for d in date_records)
    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]
    first_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)

    # 52 x 7 contribution matrix. Keep real contribution counts separate from levels.
    grid = {}
    for d_str, rec in date_records.items():
        d = datetime.date.fromisoformat(d_str)
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < 52 and 0 <= row < 7:
            grid[(col, row)] = {
                "date": d_str,
                "contributions": int(rec.get("contributions", 0)),
                "lvl": int(rec.get("level", 0)),
                "initial_level": int(rec.get("initial_level", rec.get("level", 0)))
            }

    active_cells = []
    for (col, row), cell in grid.items():
        if cell["contributions"] > 0 and cell["lvl"] > 0:
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

    if not active_cells:
        raise ValueError("No active contribution cells found")

    print(f"Generated 52x7 grid spanning {first_sunday} to {last_date}.")
    print(f"Found {len(active_cells)} active contribution cells in authentic layout.")
    print(f"Real rolling one-year contribution total: {total_contribs:,}")

    # Select up to eight real cells spread across the matrix. The route can repeat;
    # the global HUD hit counter is independent and never resets.
    ranked = sorted(active_cells, key=lambda c: (c["lvl"], c["contributions"], c["col"], c["row"]), reverse=True)
    targets = []
    buckets = {}
    for c in ranked:
        bucket = min(7, (c["col"] * 8) // 52)
        buckets.setdefault(bucket, []).append(c)
    for bucket in range(8):
        candidates = buckets.get(bucket, [])
        if candidates:
            targets.append(candidates[0])
    for c in ranked:
        if len(targets) >= min(8, len(active_cells)):
            break
        if c not in targets:
            targets.append(c)
    if len(active_cells) >= 8:
        targets = targets[:8]
    else:
        targets = active_cells[:]

    print(f"Selected {len(targets)} real visual targets:")
    for idx, t in enumerate(targets):
        print(f"  Target {idx + 1}: Col {t['col']}, Row {t['row']}, Level {t['lvl']}, Date {t['date']}, Contribs {t['contributions']}")

    targets_data = []
    for idx, t in enumerate(targets):
        targets_data.append({
            "id": idx + 1,
            "col": t["col"],
            "row": t["row"],
            "lvl": t["lvl"],
            "start_lvl": t["lvl"],
            "damaged_lvl": max(0, t["lvl"] - 1),
            "contributions": t["contributions"],
            "date": t["date"],
            "cx": t["cx"],
            "cy": t["cy"],
            "x": t["col"] * 15,
            "y": t["row"] * 13
        })

    # Fast arcade timing for the visual route.
    T_AIM = 0.04
    T_LASER = 0.08
    T_HIT = 0.08
    T_POST_HIT = 0.12
    ATTACK_SEQ_DURATION = T_AIM + T_LASER + T_HIT + T_POST_HIT

    cannon_y = 126
    travel_durations = []
    for i in range(len(targets_data)):
        prev_cx = targets_data[i - 1]["cx"] if i > 0 else 425 - 36
        curr_cx = targets_data[i]["cx"]
        dx = abs(curr_cx - prev_cx)
        t_travel = 0.10 + min(0.12, (dx / 780.0) * 0.12)
        travel_durations.append(t_travel)

    cycle_durations = [travel_durations[i] + ATTACK_SEQ_DURATION for i in range(len(targets_data))]
    VISUAL_CYCLE_DURATION = sum(cycle_durations)
    cycle_start_times = [0.0]
    for d in cycle_durations[:-1]:
        cycle_start_times.append(cycle_start_times[-1] + d)

    # One HUD hit every 0.45s. This deliberately reaches every integer instead of
    # interpolating eight milestone values. The final value remains visible.
    HIT_INTERVAL = 0.45
    TOTAL_HIT_COUNT = int(total_contribs)
    COUNTER_DURATION = max(HIT_INTERVAL, TOTAL_HIT_COUNT * HIT_INTERVAL)

    print(f"Visual attack cycle: {VISUAL_CYCLE_DURATION:.2f}s")
    print(f"HUD hit cadence: {HIT_INTERVAL:.2f}s")
    print(f"HUD final count: {TOTAL_HIT_COUNT:,}")
    print(f"HUD reaches final count after: {COUNTER_DURATION / 60:.1f} minutes")

    def pct(seconds, duration):
        return f"{max(0.0, min(100.0, (seconds / duration) * 100.0)):.4f}%"

    keyframes_css = []

    # Rocket route.
    route_kfs = []
    for i, t in enumerate(targets_data):
        t_start = cycle_start_times[i]
        t_travel = travel_durations[i]
        t_arrive = t_start + t_travel
        t_end = t_start + cycle_durations[i]
        tx = t["cx"]
        route_kfs.append(f"  {pct(t_start, VISUAL_CYCLE_DURATION)} {{ transform: translate({tx}px, {cannon_y}px); }}")
        route_kfs.append(f"  {pct(t_arrive, VISUAL_CYCLE_DURATION)} {{ transform: translate({tx}px, {cannon_y}px); }}")
        route_kfs.append(f"  {pct(t_end, VISUAL_CYCLE_DURATION)} {{ transform: translate({tx}px, {cannon_y}px); }}")
    keyframes_css.append("@keyframes shipPatrolRoute {\n" + "\n".join(route_kfs) + "\n}")

    # Laser, impact and one-level visual damage for each route target.
    for i, t in enumerate(targets_data):
        tid = t["id"]
        t_start = cycle_start_times[i]
        t_arrive = t_start + travel_durations[i]
        t_fire_start = t_arrive + T_AIM
        t_fire_hit = t_fire_start + T_LASER
        t_hit_end = t_fire_hit + T_HIT
        t_y = t["cy"]
        cannon_tip_y = cannon_y - 10

        keyframes_css.append(f'''@keyframes laserShot{tid} {{
  0% {{ opacity: 0; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(0.5); }}
  {pct(t_fire_start, VISUAL_CYCLE_DURATION)} {{ opacity: 0; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(0.5); }}
  {pct(t_fire_start + 0.001, VISUAL_CYCLE_DURATION)} {{ opacity: 1; transform: translate({t["cx"]}px, {cannon_tip_y}px) scaleY(1.2); }}
  {pct(t_fire_hit, VISUAL_CYCLE_DURATION)} {{ opacity: 1; transform: translate({t["cx"]}px, {t_y}px) scaleY(0.3); }}
  {pct(t_fire_hit + 0.02, VISUAL_CYCLE_DURATION)} {{ opacity: 0; transform: translate({t["cx"]}px, {t_y}px) scaleY(0); }}
  100% {{ opacity: 0; transform: translate({t["cx"]}px, {t_y}px); }}
}}''')

        keyframes_css.append(f'''@keyframes sparkHit{tid} {{
  0% {{ opacity: 0; transform: scale(0.2); }}
  {pct(t_fire_hit, VISUAL_CYCLE_DURATION)} {{ opacity: 0; transform: scale(0.2); }}
  {pct(t_fire_hit + 0.001, VISUAL_CYCLE_DURATION)} {{ opacity: 1; transform: scale(1.6); }}
  {pct(t_hit_end, VISUAL_CYCLE_DURATION)} {{ opacity: 0.8; transform: scale(1.0); }}
  {pct(t_hit_end + 0.04, VISUAL_CYCLE_DURATION)} {{ opacity: 0; transform: scale(0.3); }}
  100% {{ opacity: 0; transform: scale(0.2); }}
}}''')

        dim_colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
        orig_color = dim_colors[t["start_lvl"]]
        target_color = dim_colors[t["damaged_lvl"]]
        keyframes_css.append(f'''@keyframes commitDamage{tid} {{
  0% {{ fill: {orig_color}; opacity: 1; }}
  {pct(t_fire_hit, VISUAL_CYCLE_DURATION)} {{ fill: {orig_color}; opacity: 1; }}
  {pct(t_fire_hit + 0.001, VISUAL_CYCLE_DURATION)} {{ fill: #FDFBF7; opacity: 1; }}
  {pct(t_fire_hit + 0.04, VISUAL_CYCLE_DURATION)} {{ fill: {target_color}; opacity: 0.85; }}
  {pct(VISUAL_CYCLE_DURATION - 0.01, VISUAL_CYCLE_DURATION)} {{ fill: {target_color}; opacity: 0.85; }}
  100% {{ fill: {orig_color}; opacity: 1; }}
}}''')

    # -------------------------------------------------------------------------
    # Persistent counter: 0,1,2,...,REAL TOTAL. Each state owns one interval.
    # Animation delay is absolute from SVG load and is NOT tied to the repeating
    # target route, so it cannot reset when the route loops.
    # -------------------------------------------------------------------------
    formatted_total = f"{total_contribs:,}"
    counter_elements = []
    counter_css = []
    for hit in range(TOTAL_HIT_COUNT + 1):
        value = f"{hit:,}"
        class_name = f"hud-count-{hit}"
        delay = hit * HIT_INTERVAL
        duration = HIT_INTERVAL if hit < TOTAL_HIT_COUNT else 0.01
        if hit == TOTAL_HIT_COUNT:
            keyframes_css.append(f'''@keyframes {class_name}-show {{
  0% {{ opacity: 0; }}
  1% {{ opacity: 1; }}
  100% {{ opacity: 1; }}
}}''')
        else:
            keyframes_css.append(f'''@keyframes {class_name}-show {{
  0% {{ opacity: 0; }}
  1% {{ opacity: 1; }}
  99% {{ opacity: 1; }}
  100% {{ opacity: 0; }}
}}''')
        counter_css.append(
            f".{class_name} {{ opacity: 0; animation: {class_name}-show {duration:.3f}s linear {delay:.3f}s 1 both; }}"
        )
        counter_elements.append(
            f'      <text x="130" y="17" text-anchor="middle" class="counter-txt {class_name}">'
            f'DESTROYED: [ {value} / {formatted_total} COMMITS ]</text>'
        )

    laser_elements = []
    spark_elements = []
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        laser_elements.append(f'    <line x1="0" y1="0" x2="0" y2="18" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round" class="laser-bolt-{tid}"/>')
        spark_elements.append(f'''    <g transform="translate({cx}, {cy})" class="spark-burst-{tid}">
      <circle cx="0" cy="0" r="4" fill="#FDFBF7"/>
      <line x1="-5" y1="-5" x2="5" y2="5" stroke="#F59E0B" stroke-width="1.5"/>
      <line x1="5" y1="-5" x2="-5" y2="5" stroke="#F59E0B" stroke-width="1.5"/>
      <line x1="-6" y1="0" x2="6" y2="0" stroke="#E11D48" stroke-width="1.2"/>
      <line x1="0" y1="-6" x2="0" y2="6" stroke="#E11D48" stroke-width="1.2"/>
    </g>''')

    lasers_content = "\n".join(laser_elements)
    sparks_content = "\n".join(spark_elements)
    counter_texts = "\n".join(counter_elements)

    css_class_rules = [
        f".ship-patrol {{ animation: shipPatrolRoute {VISUAL_CYCLE_DURATION:.3f}s linear infinite; }}",
        ".live-beacon { animation: beaconBlink 0.8s steps(2, start) infinite; }",
        ".counter-frame { fill: #111216; stroke: #2563EB; stroke-width: 1.2; }",
        ".counter-txt { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10px; font-weight: 700; fill: #39D353; letter-spacing: 0.8px; }"
    ]
    css_class_rules.extend(counter_css)
    for t in targets_data:
        tid = t["id"]
        cx = t["cx"]
        cy = t["cy"]
        css_class_rules.append(f".laser-bolt-{tid} {{ animation: laserShot{tid} {VISUAL_CYCLE_DURATION:.3f}s linear infinite; }}")
        css_class_rules.append(f".spark-burst-{tid} {{ animation: sparkHit{tid} {VISUAL_CYCLE_DURATION:.3f}s ease-out infinite; transform-origin: {cx}px {cy}px; }}")
        css_class_rules.append(f".commit-target-{tid} {{ animation: commitDamage{tid} {VISUAL_CYCLE_DURATION:.3f}s ease-in-out infinite; }}")

    full_css = "\n".join(css_class_rules) + "\n\n" + "\n\n".join(keyframes_css)

    target_tuples = {(t["col"], t["row"]): t["id"] for t in targets_data}
    grid_rects = []
    colors = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
    for col in range(52):
        for row in range(7):
            x = col * 15
            y = row * 13
            cell = grid.get((col, row), {"lvl": 0})
            lvl = max(0, min(4, int(cell.get("lvl", 0))))
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

  <rect width="850" height="275" rx="4" class="bh-bg"/>

  <g transform="translate(24, 22)">
    <circle cx="0" cy="5" r="3.5" fill="#39D353" class="live-beacon"/>
    <text x="14" y="9" class="tag-txt">PORTAL GATEWAY // SECTOR 03: RETRO LASER CANNON COMMIT ARCADE</text>
  </g>

  <g transform="translate(565, 10)">
    <rect width="260" height="26" rx="3" class="counter-frame"/>
{counter_texts}
  </g>
  <line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B" stroke-width="1"/>

  <g transform="translate(36, 62)">
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

    <g>
{grid_content}
    </g>

    <g>
{lasers_content}
    </g>

    <g>
{sparks_content}
    </g>

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
    sync_other_svgs(total_contribs)

if __name__ == "__main__":
    records, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if records:
        generate_svg(records, total_contribs)
    else:
        print("Error: Could not retrieve contribution records.")
