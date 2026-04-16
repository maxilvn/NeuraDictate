"""Generate a DMG background image with 'drag here' arrow."""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 600, 380
BG = (242, 242, 247, 255)  # Apple light gray
FG = (28, 28, 30, 255)
ACCENT = (142, 142, 147, 255)

img = Image.new("RGBA", (W, H), BG)
draw = ImageDraw.Draw(img)

# Title
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 26)
    font_small = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 13)
except Exception:
    font_title = ImageFont.load_default()
    font_small = font_title

draw.text((W//2, 40), "Install NeuraDictate", fill=FG,
           font=font_title, anchor="mm")
draw.text((W//2, 72), "Drag the app into the Applications folder",
           fill=ACCENT, font=font_small, anchor="mm")

# Arrow pointing from app (left) to Applications (right)
# App icon area: x=120, y=200 (center)
# Applications icon area: x=480, y=200 (center)
arrow_y = 220
arrow_start = 200
arrow_end = 400
draw.line([(arrow_start, arrow_y), (arrow_end, arrow_y)], fill=ACCENT, width=3)
# Arrow head
draw.polygon([
    (arrow_end, arrow_y),
    (arrow_end - 14, arrow_y - 8),
    (arrow_end - 14, arrow_y + 8),
], fill=ACCENT)

out = os.path.join(os.path.dirname(__file__), "dmg-background.png")
img.save(out)
print(f"Created {out}")
