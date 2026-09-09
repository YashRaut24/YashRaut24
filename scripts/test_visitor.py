import urllib.request
import re
import json
import os

# Test Komarev
try:
    req = urllib.request.Request(
        "https://komarev.com/ghpvc/?username=YashRaut24",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8")
        matches = re.findall(r'<text[^>]*>(\d+)</text>', content)
        if matches:
            print(f"Komarev visitor count: {matches[-1]}")
except Exception as e:
    print(f"Komarev error: {e}")
