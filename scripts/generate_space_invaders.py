import urllib.request
import json
import re
import os
import datetime
import time
import random

USERNAME = "YashRaut24"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Marker comments used to find (and, after the first run, precisely
# re-locate) the arcade block inside assets/space-portal-unified.svg.
# On the very first run the markers don't exist yet, so we fall back to
# structural detection (sector id + the old "hud-val-0" CSS fingerprint).
# Every run after that uses the markers directly -- fast and unambiguous.
UNIFIED_MARKUP_START = "<!-- ARCADE_MARKUP_START (auto-generated, do not hand-edit) -->"
UNIFIED_MARKUP_END = "<!-- ARCADE_MARKUP_END -->"
UNIFIED_STYLE_START = "/* ARCADE_STYLE_START (auto-generated, do not hand-edit) */"
UNIFIED_STYLE_END = "/* ARCADE_STYLE_END */"


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


def build_arcade(date_records, total_contribs):
    """
    Builds the reusable arcade block: a compact, real-data commit arcade.

    Returns (inner_markup, style_block, formatted_total) where inner_markup
    is everything that goes INSIDE the 850x275 panel (header, counter,
    grid, laser, impact, rocket, footer legend) and style_block is the
    CSS driving it. Both are shared verbatim between the standalone
    assets/space-invaders-commits.svg file and the spliced-in block inside
    assets/space-portal-unified.svg, so the two never drift apart again.

    Performance design:
    - Real 52x7 GitHub contribution grid.
    - One rocket, one laser, one impact -- not one animated element per cell.
    - A discrete, real-data DESTROYED counter (jumps by each day's actual
      contribution count, not by 1 and not by a fake milestone interpolation).
    - 2-decimal keyframe percentages instead of 4 -- sub-20ms precision loss,
      meaningfully smaller CSS payload.
    """

    if not date_records:
        raise ValueError("No contribution records provided")

    total_contribs = int(total_contribs or 0)

    if total_contribs <= 0:
        total_contribs = sum(
            int(r.get("contributions", 0))
            for r in date_records.values()
        )

    if total_contribs <= 0:
        raise ValueError("No positive contribution total provided")

    # ------------------------------------------------------------
    # REAL GITHUB 52 x 7 GRID
    # ------------------------------------------------------------

    sorted_dates = sorted(
        datetime.date.fromisoformat(d)
        for d in date_records
    )

    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]

    first_sunday = first_date - datetime.timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    colors = [
        "#161B22",
        "#0E4429",
        "#006D32",
        "#26A641",
        "#39D353",
    ]

    grid = {}

    for d_str, rec in date_records.items():

        d = datetime.date.fromisoformat(d_str)

        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7

        if 0 <= col < 52 and 0 <= row < 7:

            contributions = max(0, int(rec.get("contributions", 0)))
            level = max(0, min(4, int(rec.get("level", 0))))

            grid[(col, row)] = {
                "date": d_str,
                "contributions": contributions,
                "level": level,
                "col": col,
                "row": row,
                "cx": col * 15 + 5,
                "cy": row * 13 + 5,
            }

    active_cells = [
        cell
        for cell in grid.values()
        if cell["contributions"] > 0
        and cell["level"] > 0
    ]

    if not active_cells:
        raise ValueError("No active contribution cells found")

    # ------------------------------------------------------------
    # RANDOMIZED REAL TARGET ROUTE
    # ------------------------------------------------------------

    route = active_cells[:]
    random.Random(20260828).shuffle(route)

    # ------------------------------------------------------------
    # TIMING
    # ------------------------------------------------------------

    ATTACK_INTERVAL = 1.0
    MOVE_TIME = 0.55
    FIRE_TIME = 0.30

    TOTAL_DURATION = len(route) * ATTACK_INTERVAL

    cannon_x = 425
    cannon_y = 126

    route_points = []

    for index, cell in enumerate(route):
        start = index * ATTACK_INTERVAL
        move_end = start + MOVE_TIME
        fire_start = move_end + 0.04
        impact = fire_start + FIRE_TIME

        route_points.append({
            "start": start,
            "move_end": move_end,
            "fire": fire_start,
            "impact": impact,
            "cell": cell,
        })

    def percent(seconds):
        if TOTAL_DURATION <= 0:
            return "0%"
        value = (seconds / TOTAL_DURATION) * 100.0
        value = max(0.0, min(100.0, value))
        # 2 decimal places instead of 4: at a 183s total duration this is
        # ~1.8ms of timing precision, imperceptible, but noticeably shrinks
        # every single keyframe entry across all three animated elements.
        return f"{value:.2f}%"

    # ------------------------------------------------------------
    # ROCKET KEYFRAMES
    # ------------------------------------------------------------

    rocket_kf = []
    first_cell = route_points[0]["cell"]

    rocket_kf.append(
        f"0%{{transform:translate({first_cell['cx']}px,{cannon_y}px);}}"
    )

    for point in route_points:
        cell = point["cell"]
        rocket_kf.append(
            f"{percent(point['start'])}{{transform:translate({cell['cx']}px,{cannon_y}px);}}"
        )
        rocket_kf.append(
            f"{percent(point['move_end'])}{{transform:translate({cell['cx']}px,{cannon_y}px);}}"
        )

    rocket_css = (
        "@keyframes rocketRoute{" + "".join(rocket_kf) + "}"
        f".rocket{{animation:rocketRoute {TOTAL_DURATION:.2f}s linear 1 forwards;}}"
    )

    # ------------------------------------------------------------
    # LASER KEYFRAMES
    # ------------------------------------------------------------

    laser_kf = []
    for point in route_points:
        cell = point["cell"]
        x, y = cell["cx"], cell["cy"]
        start, fire, impact = point["start"], point["fire"], point["impact"]

        laser_kf.extend([
            f"{percent(start)}{{opacity:0;transform:translate({x}px,{cannon_y - 10}px) scaleY(0);}}",
            f"{percent(fire)}{{opacity:1;transform:translate({x}px,{cannon_y - 10}px) scaleY(1);}}",
            f"{percent(impact)}{{opacity:1;transform:translate({x}px,{y}px) scaleY(0.2);}}",
            f"{percent(impact + 0.04)}{{opacity:0;transform:translate({x}px,{y}px) scaleY(0);}}",
        ])

    laser_css = (
        "@keyframes laserRoute{" + "".join(laser_kf) + "}"
        f".laser{{animation:laserRoute {TOTAL_DURATION:.2f}s linear 1 forwards;}}"
    )

    # ------------------------------------------------------------
    # SINGLE IMPACT / EXPLOSION
    # ------------------------------------------------------------

    impact_kf = []
    for point in route_points:
        cell = point["cell"]
        x, y = cell["cx"], cell["cy"]
        start, impact = point["start"], point["impact"]

        impact_kf.extend([
            f"{percent(start)}{{opacity:0;transform:translate({x}px,{y}px) scale(.1);}}",
            f"{percent(impact)}{{opacity:1;transform:translate({x}px,{y}px) scale(1);}}",
            f"{percent(impact + 0.10)}{{opacity:0;transform:translate({x}px,{y}px) scale(1.7);}}",
        ])

    impact_css = (
        "@keyframes impactRoute{" + "".join(impact_kf) + "}"
        f".impact{{animation:impactRoute {TOTAL_DURATION:.2f}s linear 1 forwards;}}"
    )

    # ------------------------------------------------------------
    # DESTROYED COUNTER -- REAL, DISCRETE, ACTUALLY WIRED UP
    #
    # Each state is a separate <text> shown only during its own real
    # window (from the moment of that impact until the next one), using
    # ONE shared @keyframes definition plus a tiny per-state delay/duration
    # rule. This gives a correct, jump-by-real-contribution-count counter
    # without needing one full @keyframes block per state.
    # ------------------------------------------------------------

    formatted_total = f"{total_contribs:,}"

    counter_states = []  # (start_seconds, duration_seconds, label)
    first_gap = max(route_points[0]["impact"], 0.05)
    counter_states.append((0.0, first_gap, f"DESTROYED: [ 0 / {formatted_total} ]"))

    cumulative = 0
    for i, point in enumerate(route_points):
        cumulative += int(point["cell"]["contributions"])
        cumulative = min(cumulative, total_contribs)

        start = point["impact"]
        end = (
            route_points[i + 1]["impact"]
            if i + 1 < len(route_points)
            else TOTAL_DURATION
        )
        duration = max(end - start, 0.05)

        counter_states.append(
            (start, duration, f"DESTROYED: [ {cumulative:,} / {formatted_total} ]")
        )

    counter_text_markup = []
    counter_rules = []

    for idx, (start, duration, label) in enumerate(counter_states):
        counter_text_markup.append(
            f'<text x="137" y="19" text-anchor="middle" class="counter cnt-{idx}">{label}</text>'
        )
        counter_rules.append(
            f".cnt-{idx}{{animation-delay:{start:.2f}s;animation-duration:{duration:.2f}s;}}"
        )

    counter_css = (
        "@keyframes counterPulse{0%{opacity:0;}2%{opacity:1;}98%{opacity:1;}100%{opacity:0;}}"
        ".counter{opacity:0;animation-name:counterPulse;animation-timing-function:linear;"
        "animation-iteration-count:1;animation-fill-mode:forwards;}"
        + "".join(counter_rules)
    )

    # ------------------------------------------------------------
    # GRID
    # ------------------------------------------------------------

    grid_markup = []
    for col in range(52):
        for row in range(7):
            x = col * 15
            y = row * 13
            cell = grid.get((col, row))
            level = cell["level"] if cell else 0
            grid_markup.append(
                f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colors[level]}"/>'
            )

    # ------------------------------------------------------------
    # INNER MARKUP (shared between standalone file and unified splice)
    # ------------------------------------------------------------

    inner_markup = f"""<!-- HEADER -->
<g transform="translate(24,22)">
<circle cx="0" cy="5" r="3.5" fill="#39D353"/>
<text x="14" y="9" class="arcade header">PORTAL GATEWAY // RETRO LASER CANNON COMMIT ARCADE</text>
</g>

<!-- COUNTER -->
<g transform="translate(555,9)">
<rect width="275" height="28" rx="4" class="counter-box"/>
{''.join(counter_text_markup)}
</g>

<line x1="0" y1="42" x2="850" y2="42" stroke="#2C303B"/>

<!-- GRID -->
<g transform="translate(36,62)">
<text x="0" y="-8" class="arcade month">JAN</text>
<text x="64" y="-8" class="arcade month">FEB</text>
<text x="128" y="-8" class="arcade month">MAR</text>
<text x="192" y="-8" class="arcade month">APR</text>
<text x="256" y="-8" class="arcade month">MAY</text>
<text x="320" y="-8" class="arcade month">JUN</text>
<text x="384" y="-8" class="arcade month">JUL</text>
<text x="448" y="-8" class="arcade month">AUG</text>
<text x="512" y="-8" class="arcade month">SEP</text>
<text x="576" y="-8" class="arcade month">OCT</text>
<text x="640" y="-8" class="arcade month">NOV</text>
<text x="704" y="-8" class="arcade month">DEC</text>

{''.join(grid_markup)}

<!-- LASER -->
<line x1="0" y1="0" x2="0" y2="18" class="laser"/>

<!-- IMPACT -->
<g class="impact">
<circle cx="0" cy="0" r="4" fill="#FDFBF7"/>
<path d="M0 -8V8 M-8 0H8 M-6 -6L6 6 M6 -6L-6 6" stroke="#F59E0B" stroke-width="1.6" stroke-linecap="round"/>
</g>

<!-- ROCKET -->
<g class="rocket">
<polygon points="0,-10 7,6 0,2 -7,6" fill="#FDFBF7"/>
<polygon points="0,2 7,6 7,12 0,9 -7,12 -7,6" fill="#2563EB"/>
<rect x="-3" y="4" width="6" height="6" fill="#E11D48"/>
<polygon points="-7,8 -11,14 -7,12" fill="#00F0FF"/>
<polygon points="7,8 11,14 7,12" fill="#00F0FF"/>
<polygon points="-4,12 0,18 4,12" fill="#F59E0B"/>
</g>

</g>

<!-- FOOTER -->
<g transform="translate(36,252)">
<rect width="9" height="9" rx="2" fill="#161B22"/>
<text x="14" y="8" class="arcade month">LEVEL 0</text>
<rect x="90" width="9" height="9" rx="2" fill="#0E4429"/>
<text x="104" y="8" class="arcade month">LEVEL 1</text>
<rect x="180" width="9" height="9" rx="2" fill="#006D32"/>
<text x="194" y="8" class="arcade month">LEVEL 2</text>
<rect x="270" width="9" height="9" rx="2" fill="#26A641"/>
<text x="284" y="8" class="arcade month">LEVEL 3</text>
<rect x="360" width="9" height="9" rx="2" fill="#39D353"/>
<text x="374" y="8" class="arcade month">LEVEL 4</text>
<text x="510" y="8" class="arcade month">{formatted_total} TOTAL COMMITS</text>
</g>
"""

    style_block = (
        ".arcade{font-family:'JetBrains Mono',Consolas,monospace;}"
        ".header{font-size:10px;font-weight:700;fill:#00F0FF;letter-spacing:1px;}"
        ".month{font-size:9px;fill:#71737E;}"
        ".counter{font-family:'JetBrains Mono',Consolas,monospace;font-size:12px;font-weight:800;fill:#39D353;}"
        ".counter-box{fill:#111216;stroke:#2563EB;stroke-width:1.2;}"
        ".rocket{transform-box:fill-box;transform-origin:center;}"
        ".laser{stroke:#00F0FF;stroke-width:2.5;stroke-linecap:round;transform-box:fill-box;transform-origin:top;}"
        ".impact{transform-box:fill-box;transform-origin:center;}"
        + rocket_css + laser_css + impact_css + counter_css
    )

    print(
        f"Generated 52x7 grid spanning {first_sunday} to {last_date}."
    )
    print(
        f"Found {len(active_cells)} active contribution cells in authentic layout."
    )
    print(
        f"Real rolling one-year contribution total: {total_contribs:,}"
    )
    print(
        f"Attack route contains {len(route):,} real active-cell targets."
    )
    print(
        "Animation mode: COMPACT ONE-SHOT -- one rocket, one laser, one impact; "
        "no 8-target loop."
    )
    print(
        f"Attack cadence: exactly {ATTACK_INTERVAL:.2f}s per target."
    )
    print(
        f"Total visual duration: {TOTAL_DURATION:.2f}s ({TOTAL_DURATION / 60:.1f} minutes)."
    )
    print(
        f"Destroyed counter states: {len(counter_states)} (real per-day jumps, not a 1-by-1 count)."
    )
    print(
        f"Final destroyed count: {total_contribs:,}"
    )

    return inner_markup, style_block, formatted_total


def generate_svg(
    date_records,
    total_contribs,
    output_path="assets/space-invaders-commits.svg",
):
    """
    Writes the standalone, lightweight GitHub contribution arcade.
    """

    inner_markup, style_block, formatted_total = build_arcade(date_records, total_contribs)

    svg_output = f"""<svg
width="850"
height="275"
viewBox="0 0 850 275"
fill="none"
xmlns="http://www.w3.org/2000/svg">

<style>
{style_block}
</style>

<rect width="850" height="275" rx="5" fill="#0B0C10" stroke="#1F2430"/>

{inner_markup}

</svg>
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_output)

    print(f"Successfully wrote {output_path}")

    return inner_markup, style_block, formatted_total


def update_unified_portal(
    inner_markup,
    style_block,
    unified_path="assets/space-portal-unified.svg",
):
    """
    Splices the freshly generated arcade block into assets/space-portal-unified.svg,
    replacing the stale, per-target-element arcade section that was committed once
    and never regenerated. Everything else in that file (header, subsystems,
    quote panel, telemetry, radar, etc.) is left completely untouched.

    First run: locates the block structurally (sector-3 container + the old
    "hud-val-0" CSS fingerprint left over from the previous per-cell counter
    implementation) and wraps the new content in sentinel markers.
    Every run after that: finds those markers directly. If neither the
    markers nor the structural fingerprint can be found, this raises loudly
    instead of guessing and corrupting a 4MB+ hand-authored file.
    """

    if not os.path.exists(unified_path):
        print(f"{unified_path} not found -- skipping unified portal splice.")
        return

    with open(unified_path, "r", encoding="utf-8") as f:
        content = f.read()

    wrapped_markup = f"{UNIFIED_MARKUP_START}\n{inner_markup}\n{UNIFIED_MARKUP_END}"
    wrapped_style = f"{UNIFIED_STYLE_START}\n{style_block}\n{UNIFIED_STYLE_END}"

    # --- Locate and replace the markup block ---
    if UNIFIED_MARKUP_START in content and UNIFIED_MARKUP_END in content:
        start_idx = content.index(UNIFIED_MARKUP_START)
        end_idx = content.index(UNIFIED_MARKUP_END) + len(UNIFIED_MARKUP_END)
        content = content[:start_idx] + wrapped_markup + content[end_idx:]
        print("Replaced arcade markup via existing markers.")
    else:
        sector_open = '<g id="sector-3"'
        sector4_open = '<g id="sector-4"'

        if sector_open not in content or sector4_open not in content:
            raise RuntimeError(
                "Could not locate the arcade section in "
                f"{unified_path} (no markers, no sector-3/sector-4 anchors). "
                "Refusing to modify the file blindly -- check it manually."
            )

        idx_sector3 = content.index(sector_open)
        idx_g_open_end = content.index(">", idx_sector3) + 1
        idx_sector4 = content.index(sector4_open, idx_sector3)

        # The divider line immediately preceding sector-4 marks the end of
        # sector-3's replaceable region; the </g> closing sector-3 sits
        # right before it.
        idx_divider = content.rfind('<line x1="18" y1="', idx_g_open_end, idx_sector4)
        if idx_divider == -1:
            raise RuntimeError(
                "Could not locate the sector-3/sector-4 divider in "
                f"{unified_path}. Refusing to modify the file blindly."
            )
        idx_sector3_close = content.rfind("</g>", idx_g_open_end, idx_divider)
        if idx_sector3_close == -1:
            raise RuntimeError(
                "Could not locate the closing </g> for sector-3 in "
                f"{unified_path}. Refusing to modify the file blindly."
            )
        idx_sector3_close_end = idx_sector3_close + len("</g>")

        content = (
            content[:idx_g_open_end]
            + "\n"
            + wrapped_markup
            + "\n</g>\n"
            + content[idx_sector3_close_end:]
        )
        print("Replaced arcade markup via structural sector-3 detection (first run).")

    # --- Locate and replace the style block ---
    if UNIFIED_STYLE_START in content and UNIFIED_STYLE_END in content:
        start_idx = content.index(UNIFIED_STYLE_START)
        end_idx = content.index(UNIFIED_STYLE_END) + len(UNIFIED_STYLE_END)
        content = content[:start_idx] + wrapped_style + content[end_idx:]
        print("Replaced arcade CSS via existing markers.")
    else:
        fingerprint = "hud-val-0"
        if fingerprint not in content:
            raise RuntimeError(
                "Could not locate the old arcade <style> block in "
                f"{unified_path} (no markers, no 'hud-val-0' fingerprint). "
                "Refusing to modify the file blindly -- check it manually."
            )
        idx_fp = content.index(fingerprint)
        idx_style_open = content.rfind("<style", 0, idx_fp)
        idx_style_open_end = content.index(">", idx_style_open) + 1
        idx_style_close = content.index("</style>", idx_fp)

        content = (
            content[:idx_style_open_end]
            + "\n"
            + wrapped_style
            + "\n"
            + content[idx_style_close:]
        )
        print("Replaced arcade CSS via structural style-block detection (first run).")

    with open(unified_path, "w", encoding="utf-8") as f:
        f.write(content)

    new_size = os.path.getsize(unified_path)
    print(f"Successfully updated {unified_path} ({new_size:,} bytes).")


if __name__ == "__main__":
    records, total_contribs = fetch_contributions(USERNAME, GITHUB_TOKEN)
    if records:
        inner_markup, style_block, formatted_total = generate_svg(records, total_contribs)
        sync_other_svgs(total_contribs)
        update_unified_portal(inner_markup, style_block)
    else:
        print("Error: Could not retrieve contribution records.")