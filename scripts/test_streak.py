import urllib.request
import re
import json
from datetime import datetime, timezone, timedelta, date

url = 'https://github.com/users/YashRaut24/contributions'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# parse tooltips
tooltips = {}
for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', html, re.DOTALL):
    tooltips[m.group(1)] = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()

days = []
for m in re.finditer(r'<td[^>]*data-date="([^"]+)"[^>]*>', html):
    tag = m.group(0)
    dt = m.group(1)
    id_m = re.search(r'id="([^"]+)"', tag)
    tt = tooltips.get(id_m.group(1), '') if id_m else ''
    cnt_m = re.search(r'(\d[\d,]*)\s+contribution', tt, re.IGNORECASE)
    cnt = int(cnt_m.group(1).replace(',', '')) if cnt_m else 0
    days.append((date.fromisoformat(dt), cnt))

days.sort()

# Bug analysis:
# 1. Current streak calculation in space-invaders.yml:
# It searched backwards in `days` for latest_active.
# If latest_active is yesterday (because user hasn't committed today yet),
# the loop started iterating from `days[-1]` (which is today).
# In `space-invaders.yml`:
# `expected = latest_active`
# `for d, count in reversed(days):`
#    `if d != expected: break` -> since `days[-1]` (today) != `latest_active` (yesterday), it broke on the FIRST iteration!
# That's why current_streak was 0 and current_start was None!

# Correct Current Streak logic:
today = datetime.now(timezone.utc).date()
day_map = {d: c for d, c in days}

# In GitHub standard streak calculation:
# A streak is active if there is a contribution on `today` OR `today - 1` (yesterday).
# If count(today) > 0: streak ends today.
# Else if count(yesterday) > 0: streak ends yesterday (today is still in progress).
# Else: streak is 0 (broken).

current_streak = 0
current_start = None
current_end = None

if day_map.get(today, 0) > 0:
    current_end = today
    cur = today
    while cur in day_map and day_map[cur] > 0:
        current_streak += 1
        current_start = cur
        cur -= timedelta(days=1)
elif day_map.get(today - timedelta(days=1), 0) > 0:
    current_end = today - timedelta(days=1)
    cur = current_end
    while cur in day_map and day_map[cur] > 0:
        current_streak += 1
        current_start = cur
        cur -= timedelta(days=1)

print(f"Fixed Current Streak: {current_streak}, {current_start} to {current_end}")

# Longest Streak calculation across all fetched days:
longest_streak = 0
longest_start = None
longest_end = None

run = 0
run_start = None
prev_date = None

for d, count in days:
    if count > 0:
        if prev_date is not None and d == prev_date + timedelta(days=1):
            run += 1
        else:
            run = 1
            run_start = d
        if run > longest_streak:
            longest_streak = run
            longest_start = run_start
            longest_end = d
    else:
        run = 0
        run_start = None
    prev_date = d

print(f"Longest Streak: {longest_streak}, {longest_start} to {longest_end}")
