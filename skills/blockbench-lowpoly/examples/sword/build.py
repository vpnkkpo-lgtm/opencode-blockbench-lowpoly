#!/usr/bin/env python3
"""
Low-poly sword — reference implementation of the blockbench-lowpoly pipeline.

The pipeline, in order: groups -> cubes -> uv_regions -> cartoon painting ->
validation (bbcheck) -> GLB -> previews -> web app link.

This file documents that structure. It is not a base to copy and retexture;
build new assets from scratch.

    python3 build.py

Outputs (generated in this folder): sword.bbmodel, sword.glb,
preview_sheet.png, link.txt
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
import bbkit as kit  # noqa: E402


def build():
    m = bbmodel.Model("sword", tex_w=128, tex_h=128, density=2)
    root = m.group("root", origin=(8, 0, 8))

    kit.bevel_box(m, "blade", (7, 2, 0), (9, 18, 16), bevel=0.3, group=root)
    m.cube("guard", (4, 2, 6), (12, 4, 10), group=root)
    m.cube("grip", (7, -6, 7), (9, 2, 9), group=root)
    m.cube("pommel", (6, -8, 6), (10, -6, 10), group=root)
    kit.cylinder(m, "rivet", (8, 3, 8), 0.6, 1, sides=6, axis=1, group=root)

    return m


def paint(m):
    c = bbtex.Canvas.for_model(m)
    for reg in m.uv_regions().values():
        c.panel(reg, "#c9c9d4", light="#e8e8f0", dark="#8a8a9a")
    return c.to_png()


def main():
    m = build()
    m.attach_texture_bytes(paint(m))

    # 1. validation (with style lint)
    rep = bbcheck.check(m.to_dict(), style=True, detail=True, kind="prop")
    assert not rep["errors"], rep["report"].print()
    rep["report"].print()
    print(f"sword: {len(rep['errors'])} errors, {len(rep['warnings'])} warnings")

    # 2. save .bbmodel
    bb_path = os.path.join(HERE, "sword.bbmodel")
    m.save(bb_path)
    print(f"saved {bb_path}")

    # 3. GLB (for the engine)
    glb_path = os.path.join(HERE, "sword.glb")
    _, size = bbglb.export_glb(m, glb_path)
    glb_ok, problems = bbglb.check_glb(open(glb_path, "rb").read())
    assert glb_ok, problems
    print(f"saved {glb_path} ({size} bytes, valid GLB)")

    # 4. previews, for visual QC
    bbrender.render_sheet(m, os.path.join(HERE, "preview_sheet.png"), size=256)
    print("previews saved")

    # 5. web app link (opens in the browser without download)
    url = bburl.build_url(m, name="sword")
    bburl.check_url(url)
    with open(os.path.join(HERE, "link.txt"), "w", encoding="utf-8") as fh:
        fh.write(url)
    print(f"link ok ({len(url)} chars) -> link.txt")

    print("ok", m.stats())


if __name__ == "__main__":
    main()