#!/usr/bin/env python3
"""
bbtex.py — PNG em Python puro + pintura cartoon para texturas de .bbmodel.

Sem dependências (nem Pillow, nem numpy). Suporta:
- encode PNG: RGBA (color type 6) e indexado 8-bit (color type 3, com PLTE/tRNS)
- decode PNG: color types 0/2/3/4/6, bit depth 1/2/4/8/16 (sem interlace)
- Canvas com pincéis cartoon: panel, ao, outline, eyes, blush, mouth, stripes, dots
- Paletas curadas (ver templates/palettes_cute.json)

Regras de estilo cute cartoon (ver references/style-cute-cartoon.md):
- NUNCA use #000000 nem #FFFFFF; sombra é colorida (roxo/azul), luz é quente.
- Cada material com 2-3 tons (base, claro, escuro) + AO nas bordas inferiores.
"""

import colorsys
import json
import os
import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"

# ---------------------------------------------------------------------------
# encode
# ---------------------------------------------------------------------------

def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(width, height, rgba):
    """rgba: bytearray/bytes de w*h*4 (ordem RGBA, linha a linha)."""
    if len(rgba) != width * height * 4:
        raise ValueError(f"rgba tem {len(rgba)} bytes, esperado {width * height * 4}")
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filtro None
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (PNG_SIG + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def encode_png_indexed(width, height, indices, palette):
    """PNG indexado 8-bit. palette: lista de (r,g,b) ou (r,g,b,a), até 256 cores."""
    if len(indices) != width * height:
        raise ValueError("indices com tamanho errado")
    if len(palette) > 256:
        raise ValueError("paleta com mais de 256 cores")
    plte = bytearray()
    alphas = bytearray()
    last_alpha = 0
    for c in palette:
        plte += bytes(c[:3])
        a = c[3] if len(c) > 3 else 255
        alphas.append(a)
        if a != 255:
            last_alpha = len(alphas)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += bytes(indices[y * width:(y + 1) * width])
    out = PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"PLTE", bytes(plte))
    if last_alpha:
        out += _chunk(b"tRNS", bytes(alphas[:last_alpha]))
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")
    return out


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, width, height, bpp, stride):
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 0:
            pass
        elif ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                up = prev[i]
                upleft = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, up, upleft)) & 0xFF
        else:
            raise ValueError(f"filtro PNG desconhecido: {ftype}")
        out += line
        prev = line
    return out


def decode_png(data):
    """Decodifica PNG para RGBA. Retorna dict(width, height, rgba bytes, palette=None)."""
    if data[:8] != PNG_SIG:
        raise ValueError("não é um PNG")
    pos = 8
    width = height = bitdepth = colortype = None
    interlace = 0
    idat = bytearray()
    plte = None
    trns = None
    while pos < len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if tag == b"IHDR":
            width, height, bitdepth, colortype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif tag == b"tRNS":
            trns = bytes(body)
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    if width is None:
        raise ValueError("PNG sem IHDR")
    if interlace:
        raise ValueError("PNG entrelaçado não suportado")
    if colortype not in (0, 2, 3, 4, 6):
        raise ValueError(f"color type {colortype} não suportado")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
    if bitdepth == 16:
        bpp = channels * 2
        stride = (width * channels * 16 + 7) // 8
    else:
        bpp = max(1, (channels * bitdepth) // 8)
        stride = (width * channels * bitdepth + 7) // 8
    raw = zlib.decompress(bytes(idat))
    rows = _unfilter(raw, width, height, bpp, stride)

    rgba = bytearray(width * height * 4)
    px = 0

    for y in range(height):
        line = rows[y * stride:(y + 1) * stride]
        if bitdepth == 16:
            vals = [line[i * 2] for i in range(width * channels)]
        elif bitdepth == 8:
            vals = list(line[:width * channels])
        else:  # 1/2/4 bits
            vals = []
            per = 8 // bitdepth
            mask = (1 << bitdepth) - 1
            for i in range(width * channels):
                byte_i = i // per
                shift = 8 - bitdepth * ((i % per) + 1)
                vals.append((line[byte_i] >> shift) & mask)
            if bitdepth in (1, 2, 4) and colortype in (0, 4):
                vals = [v * (255 // mask) for v in vals]
        if colortype == 0:
            for x in range(width):
                g = vals[x]
                a = 255
                if trns and len(trns) >= 2 and g == trns[0]:
                    a = 0
                rgba[px:px + 4] = bytes((g, g, g, a))
                px += 4
        elif colortype == 2:
            for x in range(width):
                r, g, b = vals[x * 3], vals[x * 3 + 1], vals[x * 3 + 2]
                a = 255
                if trns and len(trns) >= 6 and (r, g, b) == (trns[0], trns[2], trns[4]):
                    a = 0
                rgba[px:px + 4] = bytes((r, g, b, a))
                px += 4
        elif colortype == 3:
            if plte is None:
                raise ValueError("PNG indexado sem PLTE")
            for x in range(width):
                idx = vals[x]
                r, g, b = plte[idx]
                a = trns[idx] if (trns and idx < len(trns)) else 255
                rgba[px:px + 4] = bytes((r, g, b, a))
                px += 4
        elif colortype == 4:
            for x in range(width):
                g, a = vals[x * 2], vals[x * 2 + 1]
                rgba[px:px + 4] = bytes((g, g, g, a))
                px += 4
        else:  # 6
            for x in range(width):
                rgba[px:px + 4] = bytes(vals[x * 4:x * 4 + 4])
                px += 4
    return {"width": width, "height": height, "rgba": bytes(rgba),
            "palette": plte, "colortype": colortype}


def png_min_alpha(data):
    """Menor alpha presente no PNG (255 = totalmente opaco)."""
    dec = decode_png(data)
    return min(dec["rgba"][3::4])


def blank_png(width=16, height=16, color=(255, 0, 255, 255)):
    return encode_png(width, height, bytearray(bytes(color) * (width * height)))


# ---------------------------------------------------------------------------
# cores
# ---------------------------------------------------------------------------

def col(hex_or_tuple):
    if isinstance(hex_or_tuple, tuple):
        return tuple(hex_or_tuple) if len(hex_or_tuple) == 4 else tuple(hex_or_tuple) + (255,)
    h = hex_or_tuple.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        h += "ff"
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))


def hexof(rgba):
    return "#" + "".join(f"{c:02x}" for c in rgba[:3])


def shade(color, factor):
    """Clareia (factor>1) ou escurece (factor<1) mexendo em V e S do HSV.

    Sombra "quente": ao escurecer, satura um pouco mais e puxa para roxo/azul.
    """
    r, g, b, a = col(color)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if factor >= 1:
        v = min(1.0, v * factor)
        s = max(0.0, s * (1.0 - 0.25 * (factor - 1)))
        # luz levemente quente
        h = (h + 0.015) % 1.0
    else:
        v = v * factor
        s = min(1.0, s * 1.08)
        # sombra levemente fria (roxo/azul)
        h = (h + 0.965) % 1.0
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)


def mix(c1, c2, t):
    a = col(c1)
    b = col(c2)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def load_palette(path, name):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if name not in data:
        raise KeyError(f"paleta {name!r} não existe em {path}: {sorted(data)}")
    return data[name]


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, fill=(0, 0, 0, 0)):
        self.w = int(width)
        self.h = int(height)
        self.rgba = bytearray(bytes(col(fill)) * (self.w * self.h))

    @classmethod
    def for_model(cls, model, fill=(0, 0, 0, 0)):
        return cls(model.tex_w, model.tex_h, fill=fill)

    # -- básico -------------------------------------------------------------

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, color):
        if not self.inside(x, y):
            return
        i = (y * self.w + x) * 4
        self.rgba[i:i + 4] = bytes(col(color))

    def get(self, x, y):
        i = (y * self.w + x) * 4
        return tuple(self.rgba[i:i + 4])

    def rect(self, x, y, w, h, color, fill=True):
        c = bytes(col(color))
        if fill:
            for yy in range(y, y + h):
                if not (0 <= yy < self.h):
                    continue
                x0 = max(0, x)
                x1 = min(self.w, x + w)
                if x1 <= x0:
                    continue
                i = (yy * self.w + x0) * 4
                self.rgba[i:i + (x1 - x0) * 4] = c * (x1 - x0)
        else:
            for xx in range(x, x + w):
                self.set(xx, y, color)
                self.set(xx, y + h - 1, color)
            for yy in range(y, y + h):
                self.set(x, yy, color)
                self.set(x + w - 1, yy, color)

    def line_h(self, x, y, w, color):
        for xx in range(x, x + w):
            self.set(xx, y, color)

    def line_v(self, x, y, h, color):
        for yy in range(y, y + h):
            self.set(x, yy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                dx = (xx - cx) / max(rx, 0.5)
                dy = (yy - cy) / max(ry, 0.5)
                if dx * dx + dy * dy <= 1.02:
                    self.set(xx, yy, color)

    # -- regiões UV ---------------------------------------------------------

    @staticmethod
    def region_bbox(region):
        u1, v1, u2, v2 = region
        return int(round(min(u1, u2))), int(round(min(v1, v2))), \
            max(1, int(round(abs(u2 - u1)))), max(1, int(round(abs(v2 - v1))))

    def fill_region(self, region, color):
        x, y, w, h = self.region_bbox(region)
        self.rect(x, y, w, h, color)
        return x, y, w, h

    # -- pincéis cartoon ----------------------------------------------------

    def panel(self, region, base, light=None, dark=None, ao_color=None):
        """Painel cartoon 3 tons: base + linha superior clara + linha inferior escura."""
        x, y, w, h = self.fill_region(region, base)
        light = light or shade(base, 1.18)
        dark = dark or shade(base, 0.8)
        self.line_h(x, y, w, light)
        self.line_h(x, y + h - 1, w, dark)
        if ao_color and h > 3:
            self.line_v(x + w - 1, y + 1, h - 2, ao_color)
        return x, y, w, h

    def ao(self, region, color, edges="bl"):
        """Ambient occlusion pintada: escurece aresta(s) inferiores."""
        x, y, w, h = self.region_bbox(region)
        if "b" in edges:
            self.line_h(x, y + h - 1, w, color)
        if "l" in edges:
            self.line_v(x, y, h, color)
        if "r" in edges:
            self.line_v(x + w - 1, y, h, color)
        if "t" in edges:
            self.line_h(x, y, w, color)

    def outline_region(self, region, color):
        x, y, w, h = self.region_bbox(region)
        self.rect(x, y, w, h, color, fill=False)

    def hstripes(self, region, colors, offset=0):
        x, y, w, h = self.region_bbox(region)
        for yy in range(y, y + h):
            self.line_h(x, yy, w, colors[(yy - y + offset) % len(colors)])

    def vstripes(self, region, colors, offset=0):
        x, y, w, h = self.region_bbox(region)
        for xx in range(x, x + w):
            self.line_v(xx, y, h, colors[(xx - x + offset) % len(colors)])

    def dots(self, region, color, step=4, offset=(2, 2), size=1):
        x, y, w, h = self.region_bbox(region)
        for yy in range(y + offset[1], y + h, step):
            for xx in range(x + offset[0], x + w, step):
                self.rect(xx, yy, size, size, color)

    def checker(self, region, c1, c2, size=2):
        x, y, w, h = self.region_bbox(region)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                c = c1 if ((xx - x) // size + (yy - y) // size) % 2 == 0 else c2
                self.set(xx, yy, c)

    def dither(self, region, c1, c2, density=0.5, seed=1):
        """Dither determinístico 2 cores (sem ruído caótico — estilo limpo)."""
        x, y, w, h = self.region_bbox(region)
        s = seed & 0x7FFFFFFF
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                s = (1103515245 * s + 12345) & 0x7FFFFFFF
                c = c1 if (s / 0x7FFFFFFF) < density else c2
                self.set(xx, yy, c)

    def eyes(self, region, eye_color, spark_color, size=2, gap=4, y_frac=0.45, mirror=True):
        """Dois olhos redondos com brilho — centro horizontal da região."""
        x, y, w, h = self.region_bbox(region)
        cy = y + round(y_frac * (h - size))
        cx = x + w // 2
        left_x = cx - gap // 2 - size
        right_x = cx + gap // 2 + (gap % 2)
        for ex in (left_x, right_x):
            self.rect(ex, cy, size, size, eye_color)
            self.set(ex, cy, spark_color)
        return (left_x, right_x, cy)

    def blush(self, region, color, y_frac=0.62, inset=1, width=2):
        x, y, w, h = self.region_bbox(region)
        cy = y + round(y_frac * (h - 1))
        self.rect(x + inset, cy, width, 1, color)
        self.rect(x + w - inset - width, cy, width, 1, color)

    def mouth_smile(self, region, color, y_frac=0.72, width=4):
        """Sorriso em U de 1px: pontas em cima, meio embaixo."""
        x, y, w, h = self.region_bbox(region)
        cx = x + w // 2
        cy = y + round(y_frac * (h - 1))
        half = max(1, width // 2)
        for i in range(-half, half + 1):
            yy = cy if abs(i) == half else cy + 1
            self.set(cx + i, yy, color)

    def mouth_o(self, region, color, y_frac=0.72):
        x, y, w, h = self.region_bbox(region)
        cx = x + w // 2
        cy = y + round(y_frac * (h - 1))
        self.set(cx - 1, cy, color)
        self.set(cx, cy, color)
        self.set(cx, cy + 1, color)
        self.set(cx - 1, cy + 1, color)

    def spot(self, region, cx, cy, rx, ry=None, color="#ffe9c9", snap=False):
        """Mancha circular clipada à região. cx/cy em fração (0..1) da região.

        snap=True arredonda o centro para pixel inteiro (círculos simétricos,
        sem cara de "cruz" quando o raio é pequeno).
        """
        x, y, w, h = self.region_bbox(region)
        ry = rx if ry is None else ry
        pcx = x + cx * (w - 1)
        pcy = y + cy * (h - 1)
        if snap:
            pcx = x + round(cx * (w - 1))
            pcy = y + round(cy * (h - 1))
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                dx = (xx - pcx) / max(rx, 0.5)
                dy = (yy - pcy) / max(ry, 0.5)
                if dx * dx + dy * dy <= 1.0:
                    self.set(xx, yy, color)

    def spots(self, region, color, coords):
        """Pintas quadradas em coordenadas relativas (0..1) da região."""
        x, y, w, h = self.region_bbox(region)
        for (fx, fy, size) in coords:
            px = x + min(w - 1, int(fx * w))
            py = y + min(h - 1, int(fy * h))
            self.rect(px, py, size, size, color)

    def bleed(self, region, px=1):
        """Copia as bordas da região para fora px pixels (evita costura com filtro linear)."""
        x, y, w, h = self.region_bbox(region)
        for i in range(1, px + 1):
            for xx in range(x, x + w):
                c = self.get(xx, y + h - 1)
                self.set(xx, y + h - 1 + i, c)
                c = self.get(xx, y)
                self.set(xx, y - i, c)
            for yy in range(y, y + h):
                c = self.get(x + w - 1, yy)
                self.set(x + w - 1 + i, yy, c)
                c = self.get(x, yy)
                self.set(x - i, yy, c)

    # -- saída --------------------------------------------------------------

    def to_png(self, indexed=None):
        if indexed is None:
            return encode_png(self.w, self.h, self.rgba)
        used = {}
        order = []
        idx = bytearray(self.w * self.h)
        for p in range(self.w * self.h):
            rgba = tuple(self.rgba[p * 4:p * 4 + 4])
            if rgba not in used:
                used[rgba] = len(order)
                order.append(rgba)
            idx[p] = used[rgba]
        if len(order) > 256:
            raise ValueError(f"{len(order)} cores > 256; use to_png() RGBA")
        return encode_png_indexed(self.w, self.h, idx, order)

    def palette_used(self):
        return {tuple(self.rgba[i:i + 4]) for i in range(0, len(self.rgba), 4)}


def _smoke_test():
    c = Canvas(16, 16, fill=(0, 0, 0, 0))
    c.panel((0, 0, 8, 8), "#e04f5f")
    c.eyes((0, 0, 8, 8), "#3d2942", "#ffe9c9")
    c.blush((0, 0, 8, 8), "#f2a0a8")
    c.mouth_smile((0, 0, 8, 8), "#5a2a3a")
    c.dots((8, 0, 8, 8), "#ffe9c9", step=3)
    c.bleed((0, 0, 8, 8), 1)
    png = c.to_png()
    dec = decode_png(png)
    assert (dec["width"], dec["height"]) == (16, 16)
    assert dec["rgba"] == bytes(c.rgba), "roundtrip RGBA falhou"
    png_i = c.to_png(indexed=True)
    dec_i = decode_png(png_i)
    assert dec_i["rgba"] == bytes(c.rgba), "roundtrip indexado falhou"
    assert png_min_alpha(png) == 0
    assert 1 < len(c.palette_used()) <= 12
    s = shade("#e04f5f", 0.7)
    assert s[0] > s[2], "sombra deve puxar para frio/roxo"
    print("bbtex smoke OK —", hexof(shade("#e04f5f", 1.2)), hexof(s))


if __name__ == "__main__":
    _smoke_test()
