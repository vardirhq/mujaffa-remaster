#!/usr/bin/env python3
from pathlib import Path
import json
import sys

project = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
root = project / 'assets' / 'generated' / 'showroom'
manifest_path = root / 'manifest.json'
background = root / 'original-showroom-background.png'
if not manifest_path.is_file() or not background.is_file():
    raise SystemExit('generated original showroom assets are missing')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
if manifest.get('showroom_frame') != 730:
    raise SystemExit('showroom manifest does not point at frame 730')
if manifest.get('showroom_background_character') != 934:
    raise SystemExit('showroom manifest does not point at character 934')
print('original showroom reference verified')
