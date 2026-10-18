import sys, os
sys.path.insert(0, os.path.expanduser("~/.config/opencode/skills/blockbench-lowpoly/scripts"))
import json
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl, bbglb, bbkit as kit

m = Model("espada", tex_w=128, tex_h=128, density=2)
g = m.group("raiz", origin=(8, 0, 8))
kit.bevel_box(m, "lamina", (7, 2, 0), (9, 18, 16), bevel=0.3, group=g)
m.cube("guarda", (4, 2, 6), (12, 4, 10), group=g)
m.cube("cabo", (7, -6, 7), (9, 2, 9), group=g)
m.cube("pomo", (6, -8, 6), (10, -6, 10), group=g)
kit.cylinder(m, "rebite", (8, 3, 8), 0.6, 1, sides=6, axis=1, group=g)

c = bbtex.Canvas.for_model(m)
for reg in m.uv_regions().values():
    c.panel(reg, "#c9c9d4", light="#e8e8f0", dark="#8a8a9a")
png = c.to_png()
m.attach_texture_bytes(png)

rep = bbcheck.check(m.to_dict(), style=True, detail=True, tipo="prop")
print("sword:", len(rep["errors"]), "errors", len(rep["warnings"]), "warnings")
bbrender.render_sheet(m, "preview_sheet.png", size=256)
m.save("espada.bbmodel")
with open("espada.glb","wb") as f: f.write(bbglb.build_glb(m.bake(), "espada"))
open("link.txt","w").write(bburl.build_url(m, "espada"))
print("ok", m.stats())
