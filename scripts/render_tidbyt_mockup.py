#!/usr/bin/env python3
"""Render exactly what the Tidbyt Gen 2's 64x32 matrix shows, from the
same layout math as the ESPHome display lambda: scrolling title (top),
artist (middle), playhead bar (bottom), playing dot (top-right)."""

from PIL import Image, ImageDraw, ImageFont

W, H = 64, 32
SCALE = 12           # px per LED in the output
DOT = SCALE - 2      # LED dot size (2px black gap = the matrix grid look)

accent = (250, 45, 72)     # tonearm red
dim = (77, 77, 77)
white = (255, 255, 255)
off = (18, 16, 18)

font_title = ImageFont.truetype("/tmp/roboto.ttf", 10)
font_artist = ImageFont.truetype("/tmp/roboto.ttf", 8)

def frame(title, artist, elapsed, duration, playing, ms):
    """One 64x32 logical frame, upscaled with LED dots."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # title: horizontal pixel-scroll, loops (millis()/60 % span) — drawn
    # with top-left anchor at y=1 like the firmware's it.printf(x, 1, ...)
    tw = d.textlength(title, font=font_title)
    span = tw + W + 10
    offset = (ms // 60) % span
    x = W - offset
    d.text((x, 1), title, font=font_title, fill=white)
    # artist (middle row), top-left anchor at y=13
    if artist:
        d.text((1, 13), artist, font=font_artist, fill=(180, 180, 180))
    # playhead bar (bottom 8 rows): outline + fill = fraction played
    frac = elapsed / duration if duration else 0.0
    d.rectangle((0, 24, W - 1, 31), outline=dim, width=1)
    if int(frac * W) > 0:
        d.rectangle((0, 24, int(frac * W), 31), fill=accent)
    # playing dot, top-right
    if playing:
        d.rectangle((W - 3, 0, W - 1, 2), fill=accent)

    # upscale to LED-grid: each logical px -> a rounded dot
    out = Image.new("RGB", (W * SCALE, H * SCALE), (10, 9, 10))
    od = ImageDraw.Draw(out)
    for yy in range(H):
        for xx in range(W):
            c = img.getpixel((xx, yy))
            if c == (0, 0, 0):
                continue
            x0, y0 = xx * SCALE + 1, yy * SCALE + 1
            od.rounded_rectangle((x0, y0, x0 + DOT - 1, y0 + DOT - 1),
                                 radius=2, fill=c)
    return out

frames = [
    ("playing — mid-scroll", frame("Just Between Us — natori", "natori",
                                   96000, 260000, True, 4200)),
    ("playing — scroll wrapped", frame("Just Between Us — natori", "natori",
                                   180000, 260000, True, 7800)),
    ("paused", frame("Overdose", "natori", 41000, 197094, False, 0)),
    ("idle (nothing playing)", frame("(idle)", "tonearm", 0, 0, False, 0)),
]

sheet = Image.new("RGB", (W * SCALE + 40, (H * SCALE + 60) * len(frames)),
                  (24, 24, 28))
d = ImageDraw.Draw(sheet)
y = 20
for label, im in frames:
    d.text((20, y), label, font=ImageFont.truetype("/tmp/roboto.ttf", 22),
           fill=(210, 210, 210))
    sheet.paste(im, (20, y + 32))
    y += H * SCALE + 60
sheet.save("/home/inferenceport/tidbyt-mockup.png")
print("saved /home/inferenceport/tidbyt-mockup.png", sheet.size)
