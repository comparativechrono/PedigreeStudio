"""Contact sheet of the pictures from one or more runs.

usage: python3 sheet.py RUN[,RUN2] [FILTER] [COLUMNS]
  RUN,RUN2  one run, or two side by side for comparison
Needs Pillow (pip install pillow). Writes out/sheet_<runs>_<filter>.png"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
tags = sys.argv[1].split(',')
flt = sys.argv[2] if len(sys.argv) > 2 else ''
cols = int(sys.argv[3]) if len(sys.argv) > 3 else (len(tags) if len(tags) > 1 else 3)
names = [n for n in json.load(open(os.path.join(HERE, 'fixtures', 'index.json'))) if flt in n]
try:
    font = ImageFont.truetype('DejaVuSans.ttf', 18)
except Exception:
    font = ImageFont.load_default()
W, H = 620, 400
cells = []
for n in names:
    for t in tags:
        res = json.load(open(os.path.join(HERE, 'out', t, 'results.json'))).get(n, {})
        img = Image.open(os.path.join(HERE, 'out', t, n.replace('.json', '.png'))).convert('RGB')
        img.thumbnail((W, H - 30))
        cell = Image.new('RGB', (W, H), 'white')
        cell.paste(img, (0, 30))
        d = ImageDraw.Draw(cell)
        d.text((6, 4), '%s [%s] score %s' % (n.replace('.json', ''), t, res.get('score', '?')), fill='black', font=font)
        d.rectangle([0, 0, W - 1, H - 1], outline='#999')
        cells.append(cell)
rows = (len(cells) + cols - 1) // cols
sheet = Image.new('RGB', (cols * W, max(1, rows) * H), 'white')
for i, c in enumerate(cells):
    sheet.paste(c, ((i % cols) * W, (i // cols) * H))
fn = os.path.join(HERE, 'out', 'sheet_%s_%s.png' % ('-'.join(tags), flt or 'all'))
sheet.save(fn)
print(fn)
