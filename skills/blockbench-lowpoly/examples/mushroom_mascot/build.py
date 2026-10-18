#!/usr/bin/env python3
"""
Mushroom Mascot — reference implementation of the blockbench-lowpoly pipeline.

The pipeline, in order: groups -> cubes -> uv_regions -> cartoon painting ->
validation (bbcheck) -> GLB -> previews -> web app link.

This file documents that structure. It is not a base to copy and retexture;
build new assets from scratch.

    python3 build.py

Outputs (generated in this folder): mushroom_mascot.bbmodel, mushroom_mascot.glb,
preview_sheet.png, preview_hero.png, link.txt
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import bbcheck  # noqa: E402
import bbglb  # noqa: E402
import bbmodel  # noqa: E402
import bbrender  # noqa: E402
import bbtex  # noqa: E402
import bburl  # noqa: E402

PAL = bbtex.load_palette(os.path.join(HERE, "..", "..", "templates", "palettes_cute.json"),
                         "mushroom")
# final palette: exactly 8 colors. Ad-hoc shade() calls would push the count
# past the 8-20 target of the style guide
C_EYE = PAL["outline"][0]      # #4a2d3a
C_BLUSH = PAL["blush"][0]      # #f2a0a8
C_CAP = PAL["base"][0]         # #e05a5a
C_CAP_L = PAL["light"][0]      # #f28585
C_CAP_D = PAL["dark"][0]       # #a83a4a
C_CREAM = PAL["accent"][0]     # #ffe9c9
C_CREAM_L = PAL["accent"][1]   # #fff2d9
C_CREAM_AO = "#d9b28e"


def build():
    m = bbmodel.Model("mushroom_mascot", tex_w=128, tex_h=128, density=2)

    root = m.group("mascot", origin=[8, 0, 8])
    body = m.group("body", origin=[8, 0, 8], parent=root)
    head = m.group("head", origin=[8, 7, 8], parent=root)   # pivots at the neck
    arms = m.group("arms", origin=[8, 6.5, 8], parent=root)
    feet = m.group("feet", origin=[8, 0, 8], parent=root)

    m.cube("stem", [5, 0, 5], [11, 8, 11], group=body,
           faces=["north", "east", "south", "west", "down"])

    m.cube("cap", [2, 7, 2], [14, 12, 14], group=head)
    m.cube("cap_top", [4, 12, 4], [12, 15, 12], group=head,
           faces=["north", "east", "south", "west", "up"])

    m.cube("arm_l", [3.2, 4, 4], [5, 6.5, 8], group=arms)
    m.cube("arm_r", [3.2, 4, 4], [5, 6.5, 8], group=arms,
           origin=[5, 6.5, 8]).mirror(0, 8)

    m.cube("foot_l", [3.5, 0, 3.5], [8, 2.5, 7.5], group=feet)
    m.cube("foot_r", [3.5, 0, 3.5], [8, 2.5, 7.5], group=feet,
           origin=[8, 0, 8]).mirror(0, 8)

    return m


def paint(m):
    c = bbtex.Canvas.for_model(m, fill=(0, 0, 0, 0))
    reg = m.uv_regions()

    def r(name, face):
        return reg[(name, face)]

    def panel_cream(region, ao=True):
        c.panel(region, C_CREAM, light=C_CREAM_L, dark=C_CREAM_AO)
        if ao:
            c.ao(region, C_CREAM_AO, edges="bl")

    def panel_cap(region, base=C_CAP, light=C_CAP_L, dark=C_CAP_D):
        c.panel(region, base, light=light, dark=dark)

    # -- stem (cream) ------------------------------------------------------
    for face in ("east", "west", "south"):
        panel_cream(r("stem", face))
    c.panel(r("stem", "down"), C_CREAM_AO, light=C_CREAM, dark=C_CREAM_AO)

    # face (north): eyes + blush + smile, all above the feet
    face_reg = r("stem", "north")
    panel_cream(face_reg)
    c.eyes(face_reg, C_EYE, C_CREAM_L, size=2, gap=5, y_frac=0.28)
    c.blush(face_reg, C_BLUSH, y_frac=0.5, inset=0, width=3)
    c.mouth_smile(face_reg, C_EYE, y_frac=0.62, width=4)

    # -- cap (red) ---------------------------------------------------------
    for face in ("north", "east", "south", "west"):
        region = r("cap", face)
        panel_cap(region)
        c.spot(region, 0.26, 0.45, 3.5, color=C_CREAM, snap=True)
        c.spot(region, 0.65, 0.44, 2.5, color=C_CREAM_L, snap=True)
    c.panel(r("cap", "down"), C_CAP_D, light=C_CAP_D, dark=C_CAP_D)

    for face in ("north", "east", "south", "west"):
        region = r("cap_top", face)
        panel_cap(region, base=C_CAP_L, light=C_CAP_L, dark=C_CAP)
        c.spot(region, 0.47, 0.4, 1.8, color=C_CREAM, snap=True)
    top_reg = r("cap_top", "up")
    panel_cap(top_reg, base=C_CAP_L, light=C_CAP_L, dark=C_CAP_L)
    c.spot(top_reg, 0.33, 0.33, 3.5, color=C_CREAM, snap=True)
    c.spot(top_reg, 0.66, 0.4, 2.5, color=C_CREAM_L, snap=True)
    c.spot(top_reg, 0.4, 0.66, 1.5, color=C_CREAM, snap=True)

    # -- arms and feet ------------------------------------------------------
    for el in ("arm_l", "arm_r", "foot_l", "foot_r"):
        for face in ("north", "east", "south", "west", "up", "down"):
            if (el, face) in reg:
                panel_cream(r(el, face), ao=(face not in ("up", "down")))

    return c.to_png()


def main():
    m = build()
    png = paint(m)
    m.attach_texture_bytes(png)

    info = m.stats()
    print(f"mascot: {info}")

    # 1. validation (with style lint)
    r = bbcheck.check(m.to_dict(), style=True)
    ok = r["report"].print()
    assert ok, "bbcheck found errors in the example!"

    # 2. save .bbmodel
    bb_path = os.path.join(HERE, "mushroom_mascot.bbmodel")
    m.save(bb_path)
    print(f"saved {bb_path}")

    # 3. GLB (for the engine)
    glb_path = os.path.join(HERE, "mushroom_mascot.glb")
    _, size = bbglb.export_glb(m, glb_path)
    glb_ok, problems = bbglb.check_glb(open(glb_path, "rb").read())
    assert glb_ok, problems
    print(f"saved {glb_path} ({size} bytes, valid GLB)")

    # 4. previews, for visual QC
    bbrender.render_sheet(m, os.path.join(HERE, "preview_sheet.png"), size=256)
    bbrender.render(m, os.path.join(HERE, "preview_hero.png"), "hero", 384)
    print("previews saved")

    # 5. web app link (opens in the browser without download)
    url = bburl.build_url(m, name="mushroom_mascot")
    bburl.check_url(url)
    with open(os.path.join(HERE, "link.txt"), "w", encoding="utf-8") as fh:
        fh.write(url)
    print(f"link ok ({len(url)} chars) -> link.txt")


if __name__ == "__main__":
    main()