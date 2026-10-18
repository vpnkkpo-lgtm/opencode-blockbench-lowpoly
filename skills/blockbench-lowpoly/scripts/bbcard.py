#!/usr/bin/env python3
"""card_v7.py — multi-theme store card.

Same layout as v6 (side hero + checklist + info panel + CTA), but with
different VIBE THEMES for each model type.

Themes:
  casual       candy pink/purple, cute (default)
  horror       blood red, drips, horror mood
  dark_fantasy purple/black, runes and embers, dark medieval
  sci_fi       neon cyan/purple, futuristic grid, cyber
  nature       green/brown, leaves, cozy
  royal        purple/gold, luxury, elegant

CLI:
  python card_v7.py --theme horror --name "Zombie" --desc "..." \
      --preview prev.png --out card.png --info "Key: value" \
      [--price "R$ 19,90" --old-price "R$ 39,90"] [--badge "NEW"]
"""
import argparse
import math
import os
import random
import unicodedata

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1000, 660
SIDE_W = 400

# ---------------------------------------------------------------- THEMES
# each theme defines palette + CTA texts + bg/hero/accent colors
THEMES = {
    "casual": dict(
        bg_top=(255, 120, 175), bg_bot=(126, 92, 226),
        stripe=(255, 255, 255, 22), stripe_w=44, stripe_gap=90,
        hero=(36, 150, 200), halo=(255, 255, 255, 235),
        ink=(32, 24, 52), title=(32, 24, 52), tagline=(70, 58, 96),
        accent=(255, 74, 140), accent2=(46, 196, 236),
        check=(72, 205, 128), check2=(46, 196, 236),
        cta=(255, 74, 140), cta_shadow=(20, 60, 90), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(255, 205, 55), tag_text=(32, 24, 52), tag="3D MODEL",
        stat_bg=(248, 240, 255), stat_v=(32, 24, 52), stat_k=(120, 100, 150),
        stat_div=(200, 186, 226),
        seal=(255, 205, 55), seal_text=(32, 24, 52), seal_mid=(255, 74, 140),
        badge="READY TO USE",
        price_fill=(72, 205, 128), price_text=(255, 255, 255),
        price_old=(20, 90, 60), price_hole=(255, 251, 238),
        deco="stripes",
    ),
    "horror": dict(
        bg_top=(58, 8, 12), bg_bot=(18, 2, 4),
        stripe=(120, 10, 16, 40), stripe_w=50, stripe_gap=70,
        hero=(70, 8, 12), halo=(160, 10, 16, 200),
        ink=(12, 2, 4), title=(198, 22, 28), tagline=(150, 120, 124),
        accent=(198, 22, 28), accent2=(120, 10, 16),
        check=(150, 14, 20), check2=(90, 8, 12),
        cta=(178, 16, 24), cta_shadow=(30, 0, 2), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(150, 14, 20), tag_text=(255, 235, 235), tag="3D MODEL",
        stat_bg=(40, 6, 10), stat_v=(235, 220, 222), stat_k=(150, 110, 114),
        stat_div=(90, 20, 26),
        seal=(150, 14, 20), seal_text=(255, 235, 235), seal_mid=(255, 120, 120),
        badge="READY TO USE",
        price_fill=(120, 10, 16), price_text=(255, 235, 235),
        price_old=(200, 170, 172), price_hole=(58, 8, 12),
        deco="blood",
    ),
    "dark_fantasy": dict(
        bg_top=(46, 24, 78), bg_bot=(14, 6, 26),
        stripe=(90, 60, 140, 26), stripe_w=40, stripe_gap=110,
        hero=(34, 18, 58), halo=(180, 130, 255, 170),
        ink=(12, 6, 22), title=(214, 176, 110), tagline=(150, 132, 180),
        accent=(214, 176, 110), accent2=(140, 90, 220),
        check=(214, 176, 110), check2=(140, 90, 220),
        cta=(120, 70, 200), cta_shadow=(16, 8, 30), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(214, 176, 110), tag_text=(30, 16, 46), tag="3D MODEL",
        stat_bg=(30, 16, 52), stat_v=(224, 206, 240), stat_k=(150, 130, 180),
        stat_div=(80, 50, 120),
        seal=(214, 176, 110), seal_text=(30, 16, 46), seal_mid=(30, 16, 46),
        badge="READY TO USE",
        price_fill=(214, 176, 110), price_text=(30, 16, 46),
        price_old=(150, 130, 110), price_hole=(46, 24, 78),
        deco="embers",
    ),
    "sci_fi": dict(
        bg_top=(10, 24, 48), bg_bot=(6, 10, 26),
        stripe=(0, 240, 255, 18), stripe_w=3, stripe_gap=48,
        hero=(8, 30, 52), halo=(0, 240, 255, 180),
        ink=(2, 8, 16), title=(0, 240, 255), tagline=(120, 170, 190),
        accent=(0, 240, 255), accent2=(255, 60, 200),
        check=(0, 240, 255), check2=(255, 60, 200),
        cta=(0, 210, 235), cta_shadow=(0, 20, 40), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(0, 240, 255), tag_text=(2, 8, 16), tag="3D MODEL",
        stat_bg=(8, 22, 40), stat_v=(200, 250, 255), stat_k=(90, 150, 175),
        stat_div=(20, 80, 110),
        seal=(0, 240, 255), seal_text=(2, 8, 16), seal_mid=(255, 60, 200),
        badge="READY TO USE",
        price_fill=(255, 60, 200), price_text=(255, 255, 255),
        price_old=(160, 200, 215), price_hole=(10, 24, 48),
        deco="grid",
    ),
    "natureza": dict(
        bg_top=(120, 170, 90), bg_bot=(60, 110, 60),
        stripe=(255, 255, 255, 26), stripe_w=30, stripe_gap=80,
        hero=(70, 130, 80), halo=(255, 255, 230, 200),
        ink=(26, 44, 26), title=(30, 60, 30), tagline=(60, 80, 56),
        accent=(200, 120, 50), accent2=(70, 130, 80),
        check=(90, 170, 90), check2=(200, 150, 60),
        cta=(90, 165, 90), cta_shadow=(30, 60, 30), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(240, 210, 120), tag_text=(40, 60, 30), tag="3D MODEL",
        stat_bg=(240, 245, 225), stat_v=(30, 60, 30), stat_k=(110, 130, 90),
        stat_div=(190, 205, 170),
        seal=(240, 210, 120), seal_text=(40, 60, 30), seal_mid=(200, 120, 50),
        badge="READY TO USE",
        price_fill=(90, 165, 90), price_text=(255, 255, 255),
        price_old=(70, 100, 60), price_hole=(240, 245, 225),
        deco="leaves",
    ),
    "royal": dict(
        bg_top=(60, 24, 90), bg_bot=(22, 8, 40),
        stripe=(214, 176, 110, 22), stripe_w=26, stripe_gap=100,
        hero=(44, 18, 70), halo=(255, 215, 130, 190),
        ink=(16, 6, 30), title=(240, 205, 120), tagline=(180, 160, 200),
        accent=(240, 205, 120), accent2=(150, 90, 220),
        check=(240, 205, 120), check2=(150, 90, 220),
        cta=(200, 160, 70), cta_shadow=(20, 8, 36), cta_text="ADD TO MY GAME",
        cta_buy="BUY NOW",
        tag_fill=(240, 205, 120), tag_text=(30, 12, 50), tag="3D MODEL",
        stat_bg=(36, 16, 62), stat_v=(240, 225, 245), stat_k=(175, 155, 200),
        stat_div=(100, 60, 150),
        seal=(240, 205, 120), seal_text=(30, 12, 50), seal_mid=(150, 90, 220),
        badge="READY TO USE",
        price_fill=(240, 205, 120), price_text=(30, 12, 50),
        price_old=(180, 160, 130), price_hole=(60, 24, 90),
        deco="crowns",
    ),
}


# ---------------------------------------------------------------- utilities
def ascii_text(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = s.encode("ascii", "ignore").decode("ascii")
    return "".join(c if 32 <= ord(c) < 127 else " " for c in s)


def load_font(size):
    return ImageFont.load_default(size=size)


def fit_font(text, max_w, start, minimum=10):
    size = start
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while size > minimum:
        f = load_font(size)
        if probe.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return load_font(minimum)


def wrap_text(d, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def paste_center(img, layer, cx, cy):
    img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def render_rotated(size, angle, draw_fn):
    tmp = Image.new("RGBA", (int(size[0]) + 8, int(size[1]) + 8), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(tmp))
    return tmp.rotate(angle, resample=Image.BICUBIC, expand=True)


def drop_shadow(layer, blur=6, offset=(6, 7), opacity=90, pad=30):
    cw, ch = layer.size[0] + pad * 2, layer.size[1] + pad * 2
    padded = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    padded.paste(layer, (pad, pad), layer)
    alpha = padded.split()[3].point(lambda a: opacity if a > 8 else 0)
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh.paste((0, 0, 0), (0, 0), alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.paste(sh, offset)
    return out, pad


# ---------------------------------------------------------------- background
def make_background(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(H):
        u = y / H
        col = tuple(int(t["bg_top"][i] + (t["bg_bot"][i] - t["bg_top"][i]) * u)
                    for i in range(3))
        d.line([(0, y), (W, y)], fill=col)

    stripes = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stripes)
    for i in range(-H, W + H, t["stripe_gap"]):
        sd.line([(i, 0), (i + H * 2, H * 2)], fill=t["stripe"], width=t["stripe_w"])
    stripes = stripes.crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    img.alpha_composite(stripes)
    return img


def ray_burst(img, cx, cy, r, color, n=18):
    layer = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(n):
        a0 = i * math.tau / n
        a1 = a0 + math.tau / (n * 2.4)
        d.polygon([(r, r),
                   (r + r * math.cos(a0), r + r * math.sin(a0)),
                   (r + r * math.cos(a1), r + r * math.sin(a1))], fill=color)
    paste_center(img, layer, cx, cy)


def draw_deco(img, t):
    """Extra background decoration per theme."""
    d = ImageDraw.Draw(img)
    rng = random.Random(5)
    kind = t["deco"]

    if kind == "blood":
        # blood drips from the top
        for _ in range(14):
            x = rng.randrange(20, W - 20)
            top = rng.randrange(-10, 40)
            ln = rng.randrange(40, 160)
            w = rng.randrange(4, 11)
            col = (150, 10, 16, 235)
            d.line([(x, top), (x, top + ln)], fill=col, width=w)
            d.ellipse([(x - w / 2, top + ln - w / 2), (x + w / 2, top + ln + w / 2)],
                      fill=col)
    elif kind == "embers":
        # floating embers
        for _ in range(50):
            x, y = rng.randrange(0, W), rng.randrange(0, H)
            s = rng.randrange(1, 4)
            c = rng.choice([(255, 170, 60), (255, 120, 40), (200, 140, 255)])
            d.ellipse([(x - s, y - s), (x + s, y + s)], fill=(*c, 200))
    elif kind == "grid":
        # subtle cyber grid
        gc = (0, 240, 255, 26)
        for gx in range(0, W, 48):
            d.line([(gx, 0), (gx, H)], fill=gc, width=1)
        for gy in range(0, H, 48):
            d.line([(0, gy), (W, gy)], fill=gc, width=1)
    elif kind == "leaves":
        # little leaves
        for _ in range(26):
            x, y = rng.randrange(10, W - 10), rng.randrange(10, H - 10)
            c = rng.choice([(70, 140, 70), (110, 170, 80), (170, 190, 90)])
            a = rng.uniform(0, math.tau)
            pts = [(x + 9 * math.cos(a + k * 0.6), y + 9 * math.sin(a + k * 0.6))
                   for k in range(3)]
            d.polygon(pts + [(x, y)], fill=(*c, 190))
    elif kind == "crowns":
        # golden sparkles/stars
        for _ in range(30):
            x, y = rng.randrange(10, W - 10), rng.randrange(10, H - 10)
            s = rng.randrange(3, 8)
            d.line([(x - s, y), (x + s, y)], fill=(240, 205, 120, 200), width=2)
            d.line([(x, y - s), (x, y + s)], fill=(240, 205, 120, 200), width=2)


# ---------------------------------------------------------------- hero
def hero_panel(img, path, t):
    d = ImageDraw.Draw(img)

    wave = []
    for y in range(0, H + 1, 10):
        wave.append((SIDE_W - 26 + 22 * math.sin(y / 70.0), y))
    poly = [(0, 0)] + wave + [(0, H)]
    d.polygon(poly, fill=t["hero"])

    ray_burst(img, SIDE_W // 2 - 20, H // 2 - 10, 300, (255, 255, 255, 26))

    sh = Image.new("RGBA", (360, 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([(10, 8), (350, 52)], fill=(0, 0, 0, 115))
    paste_center(img, sh.filter(ImageFilter.GaussianBlur(9)), SIDE_W // 2 - 20, H - 92)

    if path and os.path.exists(path):
        try:
            box = 330
            pv = Image.open(path).convert("RGBA")
            sc = box / max(pv.size)
            pv = pv.resize((int(pv.width * sc), int(pv.height * sc)), Image.LANCZOS)

            glow = Image.new("RGBA", (pv.width + 34, pv.height + 34), (0, 0, 0, 0))
            glow.paste(pv, (17, 17), pv)
            ga = glow.split()[3].point(lambda a: 255 if a > 40 else 0)
            gmask = ga.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4))
            halo = Image.new("RGBA", glow.size, (0, 0, 0, 0))
            halo.paste(t["halo"][:3] + (t["halo"][3],), (0, 0), gmask)
            pos = (SIDE_W // 2 - 20 - glow.width // 2 + 10, H // 2 - 10 - glow.height // 2)
            img.alpha_composite(halo, pos)
            img.alpha_composite(glow, pos)
        except Exception as exc:  # pragma: no cover
            d.text((SIDE_W // 2, H // 2), ascii_text(f"error: {exc}"),
                   font=load_font(14), fill=(255, 255, 255), anchor="mm")
    else:
        d.ellipse([(SIDE_W // 2 - 90, H // 2 - 90), (SIDE_W // 2 + 90, H // 2 + 90)],
                  fill=t["hero"], outline=t["ink"], width=6)

    tagtxt = t["tag"]
    tw = 40 + int(load_font(18).getlength(tagtxt))
    tag = render_rotated((tw, 40), -3, lambda rd: (
        rd.rounded_rectangle([(3, 3), (tw - 3, 37)], radius=18, fill=t["tag_fill"],
                             outline=t["ink"], width=3),
        rd.text((tw / 2, 20), tagtxt, font=load_font(18), fill=t["tag_text"], anchor="mm"),
    ))
    paste_center(img, tag, SIDE_W // 2 - 20, 46)


# ---------------------------------------------------------------- content
def draw_check(d, cx, cy, r, color, ink):
    d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color, outline=ink, width=3)
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.38),
            (cx + r * 0.5, cy - r * 0.4)], fill=(255, 255, 255), width=max(3, r // 3),
           joint="curve")


def title_block(img, name, desc, t):
    d = ImageDraw.Draw(img)
    x = SIDE_W + 34
    maxw = W - x - 34

    font = fit_font(name, maxw, 54, minimum=24)
    d.text((x + 4, 58 + 4), name, font=font, fill=(0, 0, 0, 90))
    d.text((x, 58), name, font=font, fill=t["title"])

    uy = 64 + int(font.size * 1.15)
    pts = [(x + i * 12, uy + 4 * math.sin(i / 2.0)) for i in range(int(maxw / 12))]
    d.line(pts, fill=t["accent"], width=6, joint="curve")

    tf = load_font(19)
    lines = wrap_text(d, ascii_text(desc), tf, maxw - 10)
    for i, ln in enumerate(lines):
        d.text((x, uy + 22 + i * 26), ln, font=tf, fill=t["tagline"])
    return x, uy + 22 + len(lines) * 26


def checklist(img, x, y, infos, maxw, t):
    d = ImageDraw.Draw(img)
    for i, raw in enumerate(infos[:5]):
        cy = y + i * 44
        draw_check(d, x + 13, cy, 12, t["check"] if i % 2 == 0 else t["check2"], t["ink"])
        txt = raw if len(raw) < 46 else raw[:44] + ".."
        f = fit_font(txt, maxw - 44, 18, minimum=13)
        d.text((x + 36, cy - int(f.size * 0.62)), txt, font=f, fill=t["title"])
        d.line([(x + 36, cy + 15), (x + maxw - 10, cy + 15)], fill=t["stat_div"], width=2)
    return y + len(infos[:5]) * 44


def stat_bar(img, x, y, w, stats, t):
    d = ImageDraw.Draw(img)
    h = 74
    d.rounded_rectangle([(x, y), (x + w, y + h)], radius=20, fill=t["stat_bg"],
                        outline=t["ink"], width=4)
    n = max(1, len(stats))
    cw = (w - 24) / n
    for i, (k, v) in enumerate(stats):
        cx = x + 12 + cw * i + cw / 2
        vf = fit_font(v, cw - 16, 21, minimum=12)
        d.text((cx, y + 22), v, font=vf, fill=t["stat_v"], anchor="ma")
        d.text((cx, y + 50), k.upper(), font=load_font(12), fill=t["stat_k"], anchor="ma")
        if i:
            d.line([(x + 12 + cw * i, y + 14), (x + 12 + cw * i, y + h - 14)],
                   fill=t["stat_div"], width=2)


def cta_button(img, x, y, w, text, t):
    h = 62
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([(x + 7, y + 8), (x + w + 7, y + h + 8)], radius=h // 2,
                        fill=t["cta_shadow"])
    btn = render_rotated((w, h), 0, lambda rd: (
        rd.rounded_rectangle([(2, 2), (w - 2, h - 2)], radius=h // 2, fill=t["cta"],
                             outline=t["ink"], width=4),
        rd.rounded_rectangle([(12, 9), (w - 12, 26)], radius=9, fill=(255, 255, 255, 70)),
    ))
    img.alpha_composite(btn, (x, y))
    f = fit_font(text, w - 120, 23, minimum=13)
    d.text((x + w / 2 - 16, y + h / 2), text, font=f, fill=(255, 255, 255), anchor="mm")
    ax = x + w - 54
    ay = y + h / 2
    d.line([(ax - 12, ay), (ax + 14, ay)], fill=(255, 255, 255), width=5)
    d.polygon([(ax + 14, ay), (ax + 2, ay - 11), (ax + 2, ay + 11)], fill=(255, 255, 255))


def price_tag(img, cx, cy, price, old_price=None, angle=-8, t=None):
    t = t or THEMES["casual"]
    pad = 22
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    pf = load_font(30)
    pw = int(probe.textlength(price, font=pf))
    ow = int(probe.textlength(old_price, font=load_font(17))) + 16 if old_price else 0
    bw = max(pw, ow) + pad * 2
    bh = 62 + (18 if old_price else 0)

    def draw_it(d):
        d.rounded_rectangle([(3, 3), (bw + 3, bh + 3)], radius=16, fill=t["price_fill"],
                            outline=t["ink"], width=4)
        d.rounded_rectangle([(10, 8), (bw - 4, 22)], radius=7, fill=(255, 255, 255, 70))
        d.ellipse([(12, 12), (24, 24)], fill=t["price_hole"], outline=t["ink"], width=3)
        cxl = bw / 2 + 8
        y0 = 26
        if old_price:
            f_old = load_font(17)
            d.text((cxl, y0 + 8), old_price, font=f_old, fill=t["price_old"], anchor="mm")
            ow2 = probe.textlength(old_price, font=f_old)
            d.line([(cxl - ow2 / 2, y0 + 8), (cxl + ow2 / 2, y0 + 8)],
                   fill=t["price_old"], width=3)
            y0 += 16
        d.text((cxl, y0 + 22), price, font=pf, fill=t["price_text"], anchor="mm")

    lay = render_rotated((bw + 6, bh + 6), angle, draw_it)
    sh, pad2 = drop_shadow(lay, blur=5, offset=(5, 6), opacity=110)
    img.alpha_composite(sh, (int(cx - lay.width / 2 - pad2), int(cy - lay.height / 2 - pad2)))
    img.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def seal(img, cx, cy, lines, t, max_text_w=104):
    S = 168
    R_OUT, R_IN = 76, 58

    def burst(rd):
        pts = []
        for i in range(24):
            a = i * math.pi / 12 - math.pi / 2
            rr = R_OUT if i % 2 == 0 else R_IN
            pts.append((S / 2 + rr * math.cos(a), S / 2 + rr * math.sin(a)))
        rd.polygon(pts, fill=t["seal"], outline=t["ink"])
        n = len(lines)
        for i, (txt, size, col) in enumerate(lines):
            f = fit_font(txt, max_text_w, size, minimum=10)
            rd.text((S / 2, S / 2 + (i - (n - 1) / 2) * (f.size + 8)), txt,
                    font=f, fill=col, anchor="mm")

    lay = render_rotated((S, S), -14, burst)
    sh, pad = drop_shadow(lay, blur=5, offset=(5, 6))
    img.alpha_composite(sh, (int(cx - lay.width / 2 - pad), int(cy - lay.height / 2 - pad)))
    img.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


# ---------------------------------------------------------------- bbmodel
def stats_from_bbmodel(path, estilo="Cute Lowpoly"):
    """Reads a .bbmodel and returns (name, [info strings]) ready for the card.

    Infos: Height (Y bounds / 16 = meters), Polygons, Texture, Style.
    """
    import json
    d = json.load(open(path, encoding="utf-8"))
    name = d.get("name") or os.path.splitext(os.path.basename(path))[0]
    name = name.replace("_", " ").replace("-", " ").strip()

    els = d.get("elements", [])
    tris = 0
    ys = []
    for e in els:
        if e.get("type") == "cube":
            tris += 12
        else:
            tris += max(1, len(e.get("faces", {})) * 2)
        f, t = e.get("from"), e.get("to")
        if f and t:
            ys += [f[1], t[1]]
    altura = (max(ys) - min(ys)) / 16.0 if ys else 0.0

    infos = ["Height: %.2fm" % altura]
    if tris:
        infos.append("Polygons: %d" % tris)

    tex = d.get("textures", [])
    tw = th = 0
    if tex:
        tw, th = tex[0].get("width", 0), tex[0].get("height", 0)
    if not (tw and th):
        res = d.get("resolution", {})
        tw, th = res.get("width", 0), res.get("height", 0)
    infos.append("Texture: %dx%d" % (tw, th) if tw and th else "Texture: --")
    infos.append("Style: %s" % estilo)
    return name, infos


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Multi-theme store card v7 (PIL)")
    ap.add_argument("--theme", default="casual", choices=sorted(THEMES.keys()),
                    help="card theme/vibe")
    ap.add_argument("--name", default="MODEL NAME")
    ap.add_argument("--desc", default="Model description.")
    ap.add_argument("--preview", default=None)
    ap.add_argument("--out", default="/sdcard/TesteBbmodel/card_v7.png")
    ap.add_argument("--info", action="append", default=[])
    ap.add_argument("--model", default=None,
                    help="path to a .bbmodel — fills name and stats automatically")
    ap.add_argument("--estilo", default="Cute Lowpoly",
                    help="text of the Style field when using --model")
    ap.add_argument("--badge", default=None,
                    help="badge text (default comes from the theme)")
    ap.add_argument("--cta", default=None,
                    help="free button text (default comes from the theme)")
    ap.add_argument("--price", default=None,
                    help="price (e.g. 'R$ 19,90'). Empty = free")
    ap.add_argument("--old-price", default=None, dest="old_price",
                    help="crossed-out old price")
    args = ap.parse_args()

    t = THEMES[args.theme]
    name = ascii_text(args.name).upper()
    desc = ascii_text(args.desc)
    infos = [ascii_text(i) for i in args.info]

    # --model: pull name + stats straight from the .bbmodel (explicit info takes priority)
    if args.model and os.path.exists(args.model):
        mname, minfos = stats_from_bbmodel(args.model, estilo=ascii_text(args.estilo))
        if args.name == "MODEL NAME":
            name = ascii_text(mname).upper()
        infos = [ascii_text(i) for i in minfos] + infos

    if not infos:
        infos = ["Height: --", "Polygons: --", "Texture: --", "Style: --"]

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(make_background(t))
    draw_deco(canvas, t)
    hero_panel(canvas, args.preview, t)

    x, y_after_title = title_block(canvas, name, desc, t)

    stats, checks = [], []
    for it in infos:
        if ":" in it and len(stats) < 4:
            k, v = it.split(":", 1)
            stats.append((k.strip(), v.strip()))
        else:
            checks.append(it)
    if not checks:
        checks = ["Clean finish", "Texture ready", "Exports in 1 click",
                  "Fits in any scene"]
    filler = ["Texture already applied", "Clean topology", "Ready to animate",
              "Fits any scene", "Lightweight file"]
    while len(checks) < 4 and filler:
        checks.append(filler.pop(0))

    y = max(y_after_title + 8, 236)
    y_end = checklist(canvas, x, y, checks[:5], W - x - 34, t)
    stat_bar(canvas, x, y_end + 6, W - x - 34, stats[:4], t)

    cta_y = H - 112
    if args.price:
        cta_button(canvas, x, cta_y, W - x - 34, t["cta_buy"], t)
        price_tag(canvas, SIDE_W - 40, H - 100, ascii_text(args.price),
                  ascii_text(args.old_price) if args.old_price else None, t=t)
    else:
        cta_text = ascii_text(args.cta) if args.cta else t["cta_text"]
        cta_button(canvas, x, cta_y, W - x - 34, cta_text, t)
        badge = ascii_text(args.badge) if args.badge else t["badge"]
        seal(canvas, SIDE_W - 52, H - 104,
             [(badge, 15, t["ink"]), ("100%", 26, t["seal_mid"]),
              ("FREE", 15, t["ink"])], t)

    out = canvas.convert("RGB")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out.save(args.out)
    print("card saved to", args.out)


if __name__ == "__main__":
    main()
