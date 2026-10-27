#!/usr/bin/env python3
"""Generate curated language cards from GitHub source-tree byte counts.

This is NOT GitHub Linguist and does not measure authorship.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

OWNER = "Blueteemo"
PROJECTS = {
    "Flashpoint-Uninstaller": "main",
    "astrbot_plugin_awmc_maimaidx_status": "master",
    "astrbot_plugin_gf2_daily": "main",
    "marktext-cn-patch": "main",
    "maimai-knowledge-skill": "main",
    "arcaea-knowledge-skill": "main",
    "ngp-localization": "main",
    "Blueteemo": "main",
}
NDS_BRANCH = "codex/nds-v1.2-integration"
OUT = Path(".github/assets")
COLORS = {"Python": "#3572A5", "C": "#555555"}
IGNORED_DIRS = {
    "vendor", "vendors", "third_party", "third-party", "node_modules",
    "dist", "build", "target", "__pycache__", ".venv", "venv",
    "site-packages", "generated", "external",
}
IGNORED_FILES = {"font.h", "ui-fallback-font.h", "app-icon.h"}
NDS_PREFIXES = ("cpymo-backends/nds/", "cpymo-tool/nds-converter/")

def api(path):
    req = urllib.request.Request(
        "https://api.github.com/" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Blueteemo-profile-language-stats",
            **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]}
               if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)

def eligible(path, nds=False):
    p = path.lower()
    parts = p.split("/")
    if nds and not p.startswith(NDS_PREFIXES):
        return False
    if any(part in IGNORED_DIRS for part in parts[:-1]):
        return False
    if "decoder" in parts and nds:
        return False
    if parts[-1] in IGNORED_FILES or re.search(r"(?:^|/)(?:font|glyph)[-_].*\.h$", p):
        return False
    if not p.endswith((".py", ".c", ".h")):
        return False
    # Tests are included deliberately.
    return True

def measure(repo, branch, nds=False):
    data = api(f"repos/{OWNER}/{repo}/git/trees/{branch}?recursive=1")
    if data.get("truncated"):
        raise RuntimeError(f"Truncated Git tree: {repo}/{branch}")
    totals = {"Python": 0, "C": 0}
    for item in data["tree"]:
        path = item["path"]
        if item["type"] != "blob" or not eligible(path, nds):
            continue
        totals["Python" if path.lower().endswith(".py") else "C"] += item["size"]
    return totals

def svg(py, c, dark):
    fg = "#9198a1" if dark else "#59636e"
    accent = "#b7a8df" if dark else "#625095"
    c_color = "#8b949e" if dark else "#555555"
    total = py + c
    pct = 100 * py / total
    c_pct = 100 - pct
    bar_width = 336 * py / total
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="135" viewBox="0 0 360 135" role="img" aria-labelledby="title desc">
<title id="title">Languages — Selected Projects</title>
<desc id="desc">Curated source file byte distribution including tests, excluding known third-party and generated files. Python {pct:.2f}%, C {c_pct:.2f}%. Not GitHub Linguist.</desc>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}</style>
<text x="12" y="26" font-size="16" font-weight="600" fill="{accent}">Languages · Selected Projects</text>
<text x="12" y="45" font-size="10.5" fill="{fg}">Source bytes · includes tests</text>
<defs><clipPath id="bar"><rect x="12" y="60" width="336" height="9" rx="4.5"/></clipPath></defs>
<g clip-path="url(#bar)"><rect x="12" y="60" width="336" height="9" fill="{c_color}"/><rect x="12" y="60" width="{bar_width:.4f}" height="9" fill="#3572A5"/></g>
<circle cx="19" cy="94" r="5" fill="#3572A5"/><text x="32" y="98" font-size="13" fill="{fg}">Python</text><text x="166" y="98" font-size="13" font-weight="600" text-anchor="end" fill="{fg}">{pct:.2f}%</text>
<circle cx="201" cy="94" r="5" fill="{c_color}"/><text x="214" y="98" font-size="13" fill="{fg}">C</text><text x="348" y="98" font-size="13" font-weight="600" text-anchor="end" fill="{fg}">{c_pct:.2f}%</text>
<text x="12" y="125" font-size="10.5" fill="{fg}">Excludes third-party &amp; generated code</text>
</svg>
'''

def main():
    totals = {"Python": 0, "C": 0}
    for repo, branch in [*PROJECTS.items(), ("CPyMO", NDS_BRANCH)]:
        counts = measure(repo, branch, repo == "CPyMO")
        print(f"{repo}@{branch}: {counts}")
        for lang in totals:
            totals[lang] += counts[lang]
    if not all(totals.values()):
        raise RuntimeError("Missing Python or C source files")
    OUT.mkdir(parents=True, exist_ok=True)
    for dark in (False, True):
        path = OUT / ("languages-dark.svg" if dark else "languages-light.svg")
        path.write_text(svg(totals["Python"], totals["C"], dark), encoding="utf-8")
    print("Totals:", totals)

if __name__ == "__main__":
    main()
