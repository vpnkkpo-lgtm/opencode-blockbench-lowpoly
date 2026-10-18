#!/usr/bin/env python3
"""
bbrender.py — pure-Python software renderer to preview the model
(without opening Blockbench). Orthographic, z-buffer, NEAREST texture, flat lighting.

So the agent "sees" the result: front/side/iso renders + contact sheet.

Usage:
    from bbrender import render, render_sheet
    render(model, "preview.png", view="iso", size=384)
    render_sheet(model, "sheet.png")          # front + iso + side

Views: front, back, side (east), left, top, iso, hero (low 3/4).
"""

import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbtex  # noqa: E402

VIEWS = {
    # name: (model->camera direction, up hint)
    "front": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "back": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "side": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "top": ((0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
    "iso": ((0.8, 0.7, -1.0), (0.0, 1.0, 0.0)),
    "hero": ((0.7, -0.35, -1.0), (0.0, 1.0, 0.0)),
}


def _norm(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / ln, v[1] / ln, v[2] / ln) if ln > 1e-12 else (0.0, 0.0, 1.0)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _baked(model_or_baked):
    if hasattr(model_or_baked, "bake"):
        return model_or_baked.bake()
    return model_or_baked


def _tex_from_baked(baked):
    png = baked.get("png")
    if not png:
        return None
    return bbtex.decode_png(png)


def _light_dir():
    return _norm((0.35, 0.85, 0.45))


def render(model_or_baked, path, view="iso", size=384, bg=(0, 0, 0, 0), zoom=1.0,
           ambient=0.58, key=0.45, fill=0.18, supersample=2, outline=False):
    """Render a view to PNG. bg: RGBA (default transparent)."""
    baked = _baked(model_or_baked)
    tris = baked["tris"]
    tex_w = baked.get("tex_w") or 16
    tex_h = baked.get("tex_h") or 16
    tex = _tex_from_baked(baked)
    cam, up_hint = VIEWS[view]
    back = _norm(cam)
    right = _norm(_cross(up_hint, back))
    up = _norm(_cross(back, right))

    # supersample for smoother edges
    ss = max(1, int(supersample))
    W = size * ss
    H = size * ss

    def proj(p):
        return (_dot(p, right), _dot(p, up), _dot(p, back))

    # fit
    pts = []
    for (p0, p1, p2, *_uv) in tris:
        pts.extend((proj(p0), proj(p1), proj(p2)))
    if not pts:
        raise ValueError("empty model")
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span_x = max(max(xs) - min(xs), 1e-6)
    span_y = max(max(ys) - min(ys), 1e-6)
    margin = 0.06
    scale = min(W * (1 - 2 * margin) / span_x, H * (1 - 2 * margin) / span_y) * zoom
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    ox = W / 2 - cx * scale
    oy = H / 2 + cy * scale

    def to_screen(p):
        sx, sy, d = proj(p)
        return (sx * scale + ox, oy - sy * scale, d)

    zbuf = [-1e30] * (W * H)
    color = bytearray(bytes(bg) * (W * H))
    L1 = _norm((0.45, 0.8, -0.55))
    L2 = _norm((-0.5, 0.25, -0.6))

    for (p0, p1, p2, uv0, uv1, uv2) in tris:
        x0, y0, d0 = to_screen(p0)
        x1, y1, d1 = to_screen(p1)
        x2, y2, d2 = to_screen(p2)
        n = _norm(_cross(_sub(p1, p0), _sub(p2, p0)))
        lam = (ambient
               + key * max(0.0, _dot(n, L1))
               + fill * max(0.0, _dot(n, L2)))
        lam = min(1.15, lam)
        minx = max(0, int(min(x0, x1, x2)))
        maxx = min(W - 1, int(max(x0, x1, x2)) + 1)
        miny = max(0, int(min(y0, y1, y2)))
        maxy = min(H - 1, int(max(y0, y1, y2)) + 1)
        if minx > maxx or miny > maxy:
            continue
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        inv = 1.0 / area
        for py in range(miny, maxy + 1):
            row = py * W
            for px_ in range(minx, maxx + 1):
                w0 = ((x1 - px_) * (y2 - py) - (x2 - px_) * (y1 - py)) * inv
                w1 = ((x2 - px_) * (y0 - py) - (x0 - px_) * (y2 - py)) * inv
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                depth = w0 * d0 + w1 * d1 + w2 * d2
                if depth <= zbuf[row + px_]:
                    continue
                u = w0 * uv0[0] + w1 * uv1[0] + w2 * uv2[0]
                v = w0 * uv0[1] + w1 * uv1[1] + w2 * uv2[1]
                if tex:
                    tx = min(tex_w - 1, max(0, int(u)))
                    ty = min(tex_h - 1, max(0, int(v)))
                    t = (ty * tex_w + tx) * 4
                    r, g, b, a = tex["rgba"][t:t + 4]
                    if a == 0:
                        continue
                else:
                    r, g, b, a = 200, 200, 200, 255
                i = (row + px_) * 4
                color[i] = min(255, int(r * lam))
                color[i + 1] = min(255, int(g * lam))
                color[i + 2] = min(255, int(b * lam))
                color[i + 3] = 255
                zbuf[row + px_] = depth

    if outline:
        # draws triangle edges (outline/toon)
        def plot(px_, py_, depth, col_):
            if px_ < 0 or py_ < 0 or px_ >= W or py_ >= H:
                return
            idx = py_ * W + px_
            if depth >= zbuf[idx] - 1e-4:
                i4 = idx * 4
                color[i4:i4 + 4] = bytes(col_)

        for (p0, p1, p2, *_uv) in tris:
            for a, b in ((p0, p1), (p1, p2), (p2, p0)):
                x0, y0, d0 = to_screen(a)
                x1, y1, d1 = to_screen(b)
                # Bresenham
                xi, yi = int(round(x0)), int(round(y0))
                xj, yj = int(round(x1)), int(round(y1))
                dx = abs(xj - xi); dy = abs(yj - yi)
                sx = 1 if xi < xj else -1
                sy = 1 if yi < yj else -1
                err = dx - dy
                steps = max(dx, dy, 1)
                for _ in range(steps + 1):
                    t = _ / steps if steps else 0.0
                    dd = d0 + (d1 - d0) * t
                    plot(xi, yi, dd, (0, 0, 0, 255))
                    if xi == xj and yi == yj:
                        break
                    e2 = 2 * err
                    if e2 > -dy:
                        err -= dy
                        xi += sx
                    if e2 < dx:
                        err += dx
                        yi += sy

    if ss > 1:
        color = _downsample(color, W, H, ss)
    bbtex_bytes = bbtex.encode_png(size, size, color)
    if path:
        with open(path, "wb") as fh:
            fh.write(bbtex_bytes)
    return bbtex_bytes


def _downsample(src, W, H, ss):
    size = W // ss
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            r = g = b = a = 0
            for dy in range(ss):
                for dx in range(ss):
                    i = ((y * ss + dy) * W + (x * ss + dx)) * 4
                    r += src[i]
                    g += src[i + 1]
                    b += src[i + 2]
                    a += src[i + 3]
            n = ss * ss
            o = (y * size + x) * 4
            out[o] = r // n
            out[o + 1] = g // n
            out[o + 2] = b // n
            out[o + 3] = a // n
    return out


def render_sheet(model_or_baked, path, views=("front", "iso", "side"), size=256,
                 bg=(235, 236, 240, 255)):
    """Contact sheet with several views side by side."""
    n = len(views)
    total_w = size * n
    sheet = bytearray(bytes(bg) * (total_w * size))
    for i, view in enumerate(views):
        png = render(model_or_baked, None, view=view, size=size, bg=bg)
        dec = bbtex.decode_png(png)
        for y in range(size):
            src = y * size * 4
            dst = (y * total_w + i * size) * 4
            sheet[dst:dst + size * 4] = dec["rgba"][src:src + size * 4]
        for y in range(size):
            x = i * size
            dst = (y * total_w + x) * 4
            sheet[dst:dst + 4] = bytes(bg)
    out = bbtex.encode_png(total_w, size, sheet)
    if path:
        with open(path, "wb") as fh:
            fh.write(out)
    return out


def _demo():
    import bbmodel as bm
    m = bm.Model("render_demo", tex_w=128, tex_h=128, density=2)
    g = m.group("root")
    m.cube("legs", [2, 0, 2], [14, 6, 14], group=g)
    m.cube("head", [1, 6, 1], [15, 16, 15], group=g)
    m.cube("beak", [6, 9, 0], [10, 11, 3], group=g)

    c = bbtex.Canvas(128, 128, fill=(0, 0, 0, 0))
    for name, d in m.uv_regions().items():
        c.panel(d, "#e8b04a", ao_color="#b57f2e")
    png = c.to_png()
    m.attach_texture_bytes(png)
    import tempfile
    out = os.path.join(tempfile.gettempdir(), "bbrender_demo.png")
    render_sheet(m, out, size=192)
    data = open(out, "rb").read()
    dec = bbtex.decode_png(data)
    assert dec["width"] == 192 * 3 and dec["height"] == 192
    solid = sum(1 for i in range(0, len(dec["rgba"]), 4 * 37) if dec["rgba"][i + 3] > 0)
    assert solid > 50, "render came out empty?"
    one = render(m, os.path.join(tempfile.gettempdir(), "bbrender_iso.png"), "iso", 192)
    assert len(one) > 500
    print(f"bbrender smoke OK — sheet 3 views + iso ({len(data)} bytes)")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] not in ("--demo",):
        # CLI: bbrender.py model.bbmodel output.png [view] [size]
        import bbmodel as bm
        model = bm.Model.load(sys.argv[1])
        out = sys.argv[2] if len(sys.argv) > 2 else "preview.png"
        view = sys.argv[3] if len(sys.argv) > 3 else "iso"
        size = int(sys.argv[4]) if len(sys.argv) > 4 else 384
        render(model, out, view=view, size=size)
        print(f"render saved to {out} ({view}, {size}px)")
    elif len(sys.argv) == 1 or sys.argv[1] == "--demo":
        _demo()
    else:
        print(__doc__)
