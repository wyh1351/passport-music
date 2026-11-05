#!/usr/bin/env python3
"""Dependency-free shipped-font coverage gate; generation needs Pillow/fonttools."""
import hashlib
from music_font_hash import source_digest_matches
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
inv=json.loads((ROOT/'assets/fonts/music_font_inventory.json').read_text())
source=ROOT/'assets/fonts/music_font_16.c'
assert source_digest_matches(source.read_bytes(),inv['generated_sha256'])
points=set(inv['codepoints'])
ui_copy='\n'.join((ROOT/name).read_text(encoding='utf-8') for name in ('main/music_ui.c','main/music_settings.c'))
for literal in re.findall(r'"([^"\n]*)"',ui_copy):
    for char in literal:
        if ord(char)>127: assert ord(char) in points,(char,hex(ord(char)))
assert set(range(0x4e00,0x9ff0))<=points
assert set(range(0x3041,0x3097))<=points
assert set(range(0x30a1,0x30fb))<=points
assert set(range(0x31f0,0x3200))<=points
assert set(range(0xac00,0xd7a4))<=points
assert set(range(0x1100,0x1200))<=points
assert set(range(0x3131,0x318f))<=points
for asset in inv['font_sources']:
    assert hashlib.sha256((ROOT/'assets/fonts'/asset['file']).read_bytes()).hexdigest()==asset['sha256']
required='·•‧∙⋅・‘’“”–—…−±×÷©®™℃℉€£¥①②③←↑→↓♪♫♭♯éü'
required+='あいうえおがぱゔアイウエオガパヴヷーㇰ가나다라마바사아자차카타파하힣한글ㄱㅎᄀᄂ'
assert set(map(ord,required))<=points
font_text=source.read_text(encoding='utf-8')
unicode_data=re.search(r'uint16_t unicode_list\[\] = \{(.*?)\};',font_text,re.S)[1]
actual=[int(x)+0x20 for x in re.findall(r'\d+',unicode_data)]
assert actual==inv['codepoints'] and actual==sorted(set(actual))
coverage=(ROOT/'assets/fonts/music_font_coverage.h').read_text()
missing_data=re.search(r'uint16_t missing\[\] = \{(.*?)\};',coverage,re.S)[1]
assert [int(x) for x in re.findall(r'\d+',missing_data)]==inv['missing']
print(f'Font coverage: PASS ({len(points)} glyphs, 2bpp, Chinese/Latin + Japanese kana + modern Korean)')
large_inv=json.loads((ROOT/'assets/fonts/music_font_20_inventory.json').read_text())
large=ROOT/'assets/fonts/music_font_20.c'
assert large_inv['size']==20 and large_inv['codepoints']==inv['codepoints']
assert large_inv['missing']==inv['missing']
assert source_digest_matches(large.read_bytes(),large_inv['generated_sha256'])
large_text=large.read_text(encoding='utf-8')
large_unicode=re.search(r'uint16_t unicode_list\[\] = \{(.*?)\};',large_text,re.S)[1]
assert [int(x)+0x20 for x in re.findall(r'\d+',large_unicode)]==inv['codepoints']
assert '.line_height=28, .base_line=5' in large_text
print(f'20px title/current lyric coverage: PASS ({len(points)} identical codepoints)')
