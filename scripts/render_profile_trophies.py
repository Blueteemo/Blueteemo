#!/usr/bin/env python3
"""Derive 7-column desktop and compact 4+3 mobile trophies from one source SVG.

Only background/text contrast and top-level card positions/sizes change:
the generator's original badge icons, gradients, ranks and values remain.
Standard-library only; the daily Action downloads a fresh source once.
"""
from __future__ import annotations

import pathlib
import re
import sys
import xml.etree.ElementTree as ET

CARD_OPEN = re.compile(
    r'(<svg\s+)x="\d+"(\s+)y="\d+"(\s+)width="110"(\s+)height="110"'
)
BG = re.compile(r'(<rect\s+x="0\.5"[\s\S]*?\bfill=")#282c34"')
TITLE = re.compile(r'(<text x="50%" y="18"[^>]*\bfill=")#e5c07b"')
DETAIL = re.compile(r'(<text x="50%" y="(?:85|97)"[^>]*\bfill=")#e06c75"')
NAMESPACE = '{http://www.w3.org/2000/svg}'


def validate(source: str) -> None:
    root = ET.fromstring(source)
    cards = [node for node in root if node.tag == NAMESPACE + 'svg']
    if len(cards) != 7:
        raise ValueError(f'Expected seven original trophies, found {len(cards)}')
    if root.get('viewBox') != '0 0 770 110':
        raise ValueError('Unexpected source trophy size; inspect generator changes')
    for node in root.iter():
        if node.tag in {NAMESPACE + 'script', NAMESPACE + 'foreignObject'}:
            raise ValueError('Disallowed markup in trophy source')
        if any(key.lower().startswith('on') for key in node.attrib):
            raise ValueError('Disallowed SVG event handler')
    if not all(any(t.tag == NAMESPACE + 'text' and t.get('y') == '18'
                   for t in card.iter()) for card in cards):
        raise ValueError('Original trophy titles not detected')


def light_variant(source: str) -> str:
    # The colored icon gradients/letter badges are intentionally untouched.
    # Only card backing and readable text change on GitHub's light background.
    source, n = BG.subn(lambda m: m.group(1) + '#f6f3fa"', source)
    if n != 7:
        raise ValueError(f'Expected 7 dark card backings, found {n}')
    source, titles = TITLE.subn(lambda m: m.group(1) + '#625095"', source)
    source, details = DETAIL.subn(lambda m: m.group(1) + '#91506e"', source)
    if titles != 7 or details != 14:
        raise ValueError(f'Unexpected labels: {titles} titles, {details} details')
    return source


def mobile_variant(source: str) -> str:
    if 'width="770"' not in source or 'viewBox="0 0 770 110"' not in source:
        raise ValueError('Unexpected desktop trophy root')
    source = source.replace('width="770"', 'width="480"', 1)
    source = source.replace('height="110"', 'height="200"', 1)
    source = source.replace('viewBox="0 0 770 110"', 'viewBox="0 0 480 200"', 1)
    # Four cards above, three centered below. Each original SVG is scaled
    # from 110 to 100 units; at 320 CSS px the complete image is ~133px tall.
    coords = [(40, 0), (140, 0), (240, 0), (340, 0),
              (90, 100), (190, 100), (290, 100)]
    index = 0

    def place(m: re.Match[str]) -> str:
        nonlocal index
        if index >= 7:
            raise ValueError('Unexpected extra trophy')
        x, y = coords[index]
        index += 1
        return (f'{m.group(1)}x="{x}"{m.group(2)}y="{y}"'
                f'{m.group(3)}width="100"{m.group(4)}height="100"')

    source = CARD_OPEN.sub(place, source)
    if index != 7:
        raise ValueError(f'Expected 7 movable cards, found {index}')
    return source


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render_profile_trophies.py downloaded.svg output_dir')
    src = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
    validate(src)
    light = light_variant(src)
    variants = {
        'trophy.svg': src,
        'trophy-light.svg': light,
        'trophy-mobile-dark.svg': mobile_variant(src),
        'trophy-mobile-light.svg': mobile_variant(light),
    }
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, content in variants.items():
        ET.fromstring(content)
        path = out / name
        path.write_text(content.rstrip() + '\n', encoding='utf-8')
        print(f'{name}: {len(content)} characters, seven original trophy badges')


if __name__ == '__main__':
    main()
