#!/usr/bin/env python3
"""Render the CarPlay-style layout: art right (24x24), text stack left,
progress bar + elapsed under it. Same math as the ESPHome display lambda."""

from PIL import Image, ImageDraw, ImageFont

W, H = 64, 32
SCALE = 12
DOT = SCALE - 2

accent = (250, 45, 72)
dim = (77, 77, 77)
white = (255, 255, 255)

font8 = ImageFont.truetype("/tmp/roboto.ttf", 8)

def frame(title, album, artist, elapsed, duration, playing, has_art, ms):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── left column (0-38): text stack ──
    tw = d.textlength(title, font=font8)
    span = tw + 38
    off = (ms // 60) % span
    x = 38 - off
    d.text((x, 0), title, font=font8, fill=white)
    d.text((0, 9), album, font=font8, fill=(200, 200, 200))
    d.text((0, 17), artist, font=font8, fill=(200, 200, 200))
    # bar + time
    frac = elapsed / duration if duration else 0.0
    d.rectangle((0, 27, 25, 30), outline=dim, width=1)
    if int(frac * 26) > 0:
        d.rectangle((0, 27, int(frac * 26), 30), fill=accent)
    secs = int(elapsed / 1000)
    d.text((29, 25), f"{secs // 60}:{secs % 60:02d}", font=font8, fill=white)

    # ── right column (40-63): album art ──
    if has_art:
        # pretend art: a 24x24 gradient square with a vinyl-circle
        art = Image.new("RGB", (24, 24), (0, 0, 0))
        ad = ImageDraw.Draw(art)
        for yy in range(24):
            t = yy / 23.0
            ad.line((0, yy, 23, yy), fill=(int(90 + t * 60), int(20 + t * 20), int(110 - t * 40)))
        ad.ellipse((5, 5, 18, 18), outline=(250, 45, 72), width=2)
        ad.ellipse((10, 10, 13, 13), fill=white)
        img.paste(art, (40, 4))
        if playing:
            d.rectangle((40, 4, 42, 6), fill=accent)

    # upscale to LED grid
    out = Image.new("RGB", (W * SCALE, H * SCALE), (10, 9, 10))
    od = ImageDraw.Draw(out)
    for yy in range(H):
        for xx in range(W):
            c = img.getpixel((xx, yy))
            if c == (0, 0, 0):
                continue
            x0, y0 = xx * SCALE + 1, yy * SCALE + 1
            od.rounded_rectangle((x0, y0, x0 + DOT - 1, y0 + DOT - 1), radius=2, fill=c)
    return out

frames = [
    ("playing — Heavy Rotation, shuffled", "Just Between Us — natori", "Just Between Us",
     "natori", 96000, 260000, True, True, 3600),
    ("playing — scrolled to album", "Just Between Us — natori", "Just Between Us",
     "natori", 150000, 260000, True, True, 5200),
    ("paused", "Just Between Us — natori", "Just Between Us",
     "natori", 41000, 260000, False, True, 0),
    ("idle — no art yet", "(idle)", "tonearm", "", 0, 0, False, False, 0),
]

sheet = Image.new("RGB", (W * SCALE + 40, (H * SCALE + 60) * len(frames)), (24, 24, 28))
d = ImageDraw.Draw(sheet)
y = 20
for label, title, album, artist, el, dur, playing, art, ms in frames:
    d.text((20, y), label, font=ImageFont.truetype("/tmp/roboto.ttf", 22), fill=(210, 210, 210))
    sheet.paste(frame(title, album, artist, el, dur, playing, art, ms), (20, y + 32))
    y += H * SCALE + 60
sheet.save("/home/inferenceport/tidbyt-mockup.png")
print("saved", sheet.size)
