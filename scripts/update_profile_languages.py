#!/usr/bin/env python3
"""Curated source-byte language cards, not GitHub Linguist or authorship.

Auto-discovers public non-fork projects; adds only the CPyMO NDS port from a
published tag. Includes tests but excludes known third-party/generated code.
"""
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

OWNER = "Blueteemo"
NDS_REF = "nds-v1.2.0"
OUT = Path(".github/assets")
EXTENSIONS = {
    ".py": "Python", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".swift": "Swift", ".asm": "Assembly", ".s": "Assembly",
    ".rs": "Rust", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin", ".sh": "Shell",
}
COLORS = {
    "Python": "#3572A5", "C": "#555555", "C++": "#f34b7d",
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Swift": "#f05138", "Assembly": "#6e4c13",
    "Rust": "#dea584", "Go": "#00add8", "Java": "#b07219",
    "Kotlin": "#a97bff", "Shell": "#89e051", "Other": "#8b949e",
}
IGNORED_DIRS = {
    "vendor", "vendors", "third_party", "third-party", "node_modules",
    "dist", "build", "target", "__pycache__", ".venv", "venv",
    "site-packages", "generated", "external",
}
IGNORED_FILES = {"font.h", "ui-fallback-font.h", "app-icon.h"}
NDS_PREFIXES = ("cpymo-backends/nds/", "cpymo-tool/nds-converter/")


def api(path):
    request = urllib.request.Request(
        "https://api.github.com/" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Blueteemo-profile-language-stats",
            **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]}
               if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)


def public_original_repositories():
    projects = []
    for page in range(1, 11):
        batch = api(f"users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected GitHub repository listing response")
        for repo in batch:
            if repo.get("owner", {}).get("login", "").lower() != OWNER.lower():
                continue
            if any(repo.get(key) for key in ("private", "fork", "archived", "disabled")):
                continue
            if repo.get("default_branch"):
                projects.append((repo["name"], repo["default_branch"]))
        if len(batch) < 100:
            break
    else:
        raise RuntimeError("Repository listing exceeds 1,000 results")
    if not projects:
        raise RuntimeError("No public original repositories discovered")
    return sorted(set(projects), key=lambda item: item[0].lower())


def eligible(repo, path, nds=False):
    name = path.lower()
    parts = name.split("/")
    if nds and not name.startswith(NDS_PREFIXES):
        return False
    if repo == "marktext-cn-patch" and name.startswith("patched/"):
        return False
    if any(part in IGNORED_DIRS for part in parts[:-1]):
        return False
    if nds and "decoder" in parts:
        return False
    if parts[-1] in IGNORED_FILES or re.search(r"(?:^|/)(?:font|glyph)[-_].*\.h$", name):
        return False
    return Path(name).suffix in EXTENSIONS


def measure(repo, ref, nds=False):
    path = f"repos/{quote(OWNER, safe='')}/{quote(repo, safe='')}/git/trees/{quote(ref, safe='')}?recursive=1"
    try:
        data = api(path)
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            print(f"::notice::Skipping empty repository: {repo}@{ref}")
            return {}
        if exc.code == 404:
            raise RuntimeError(
                f"Language source not found: {OWNER}/{repo}@{ref} (HTTP 404)"
            ) from exc
        raise
    if data.get("truncated"):
        raise RuntimeError(f"Truncated Git tree: {repo}@{ref}")
    totals = {}
    for item in data["tree"]:
        path = item["path"]
        if item["type"] != "blob" or not eligible(repo, path, nds):
            continue
        language = EXTENSIONS[Path(path.lower()).suffix]
        totals[language] = totals.get(language, 0) + item["size"]
    return totals


def svg(totals, dark):
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    visible = (ordered[:5] + [("Other", sum(n for _, n in ordered[5:]))]
               if len(ordered) > 6 else ordered)
    total = sum(totals.values())
    rows = math.ceil(len(visible) / 2)
    footer_y = 106 + 28 * rows
    height = footer_y + 16
    fg = "#9198a1" if dark else "#59636e"
    accent = "#b7a8df" if dark else "#625095"
    description = ", ".join(f"{lang} {100 * size / total:.2f}%" for lang, size in ordered)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Languages — Selected Projects</title>',
        f'<desc id="desc">Curated public originals plus CPyMO NDS source bytes, including tests, excluding known third-party, generated and upstream patch files. Not GitHub Linguist or authorship. {description}.</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>',
        f'<text x="12" y="26" font-size="16" font-weight="600" fill="{accent}">Languages · Selected Projects</text>',
        f'<text x="12" y="45" font-size="10.5" fill="{fg}">Source bytes · includes tests</text>',
        '<defs><clipPath id="bar"><rect x="12" y="60" width="336" height="10" rx="5"/></clipPath></defs>',
        '<g clip-path="url(#bar)">',
    ]
    def color(lang):
        return ("#8b949e" if dark and lang == "C" else
                "#b69a6f" if dark and lang == "Assembly" else
                COLORS.get(lang, "#8b949e"))
    x = 12.0
    for lang, size in visible:
        width = 336 * size / total
        parts.append(f'<rect x="{x:.4f}" y="60" width="{width:.4f}" height="10" fill="{color(lang)}"/>')
        x += width
    parts.append('</g>')
    for i, (lang, size) in enumerate(visible):
        col, row = i % 2, i // 2
        cx, tx, px = (19, 32, 166) if col == 0 else (201, 214, 348)
        cy = 98 + row * 28
        parts.extend((
            f'<circle cx="{cx}" cy="{cy}" r="5" fill="{color(lang)}"/>',
            f'<text x="{tx}" y="{cy + 4}" font-size="13" fill="{fg}">{lang}</text>',
            f'<text x="{px}" y="{cy + 4}" font-size="13" font-weight="600" text-anchor="end" fill="{fg}">{100 * size / total:.2f}%</text>',
        ))
    parts.append(f'<text x="12" y="{footer_y}" font-size="10.5" fill="{fg}">Excludes third-party &amp; generated code</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main():
    projects = public_original_repositories()
    projects.append(("CPyMO", NDS_REF))
    totals = {}
    print(f"Selected {len(projects) - 1} public original repositories + CPyMO NDS")
    for repo, ref in projects:
        counts = measure(repo, ref, nds=(repo == "CPyMO"))
        print(f"{repo}@{ref}: {counts}")
        for lang, size in counts.items():
            totals[lang] = totals.get(lang, 0) + size
    totals = {lang: size for lang, size in totals.items() if size > 0}
    if not totals:
        raise RuntimeError("No eligible source files found")
    OUT.mkdir(parents=True, exist_ok=True)
    for dark in (False, True):
        path = OUT / ("languages-dark.svg" if dark else "languages-light.svg")
        path.write_text(svg(totals, dark), encoding="utf-8")
    print("Totals:", totals)


if __name__ == "__main__":
    main()
