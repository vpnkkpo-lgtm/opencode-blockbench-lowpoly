---
name: blockbench-lowpoly
description: Pure-Python toolkit (no MCP, no dependencies) to author low-poly 3D assets in a "refined cute cartoon" style from code — generates .bbmodel (JSON), paints the texture via Canvas, validates (bbcheck), renders PNG previews (bbrender), exports GLB (bbglb) and builds the web app Blockbench link (bburl). Use when creating characters, props, mobs, 3D icons, dioramas or any model for Blockbench/glTF without opening the editor.
---

# Blockbench LowPoly — Procedural Genesis of Cute Cartoon Assets

100% pure-Python toolkit for the agent to **author low-poly 3D assets from code** and deliver them in 4 formats: `.bbmodel` (native Blockbench project), `.glb` (engine/runtime), preview PNGs and a link that opens the model directly in the Blockbench web app. Zero external dependencies, zero MCP, zero editor.

## Structure

```
scripts/bbmodel.py   builder: Model/Group/Cube/Mesh, UV, mirror, bake, load/save
scripts/bbtex.py     pure PNG (encode/decode) + cartoon painting Canvas
scripts/bbcheck.py   validator (geometry, UV, outliner, style, budgets)
scripts/bbglb.py     GLB exporter (glTF 2.0 binary, embedded texture)
scripts/bburl.py     Blockbench web app link + verification roundtrip
scripts/bbrender.py  software rasterizer: ortho/iso/hero previews
templates/palettes_cute.json  7 curated palettes (roles: outline/base/light/dark/accent/blush/shadow)
examples/mascote_cogumelo/    commented end-to-end example (build.py, previews, link)
references/           format spec, pitfalls, style guide, Blockbench workflow
```

## Quickstart

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.config/opencode/skills/blockbench-lowpoly/scripts"))
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl

m = Model("mushroom", tex_w=128, tex_h=128, density=2)   # density = px per unit
body = m.group("body", origin=(8, 0, 8))
m.cube("trunk", (5, 0, 5), (11, 8, 11), group=body,
       faces=["north","east","south","west"])            # omitted up/down = economical

c = bbtex.Canvas.for_model(m)
c.panel(m.uv_regions()[("trunk","north")], "#f6ddb8", light="#fdefd6", dark="#e8c894")
png = c.to_png()
m.attach_texture_bytes(png)

rep = bbcheck.check(m.to_dict(), style=True, tex_override=png)  # E/W/I + style lint
bbrender.render_sheet(m, "preview.png", size=384)
m.save("asset.bbmodel")
with open("asset.glb","wb") as f: f.write(__import__("bbglb").build_glb(m.bake(), "asset"))
open("link.txt","w").write(bburl.build_url(m, "asset"))
```

## Recommended workflow

1. **Plan on paper**: silhouette readable at 64px, proportions (head 35–50% for "cute"), tri budget (prop ≤800, character ≤3000).
2. **Pick a palette** in `templates/palettes_cute.json` (`bbtex.load_palette(path, name)`) or define ~8–20 colors of your own. NEVER pure #000000/#ffffff.
3. **Build the geometry** with `Model.cube`/`Model.mesh`; `from < to` always; pivot (`origin`) on the joint when rigged.
4. **Paint the texture** with the Canvas using `uv_regions()` as the map. Use `panel()` on faces, `outline_region()` for outlines, `eyes/blush/mouth_smile` for the face, `spot(snap=True)` for spots.
5. **Validate**: `bbcheck.check(d, style=True, tex_override=png)` — aim for 0 errors and 0 warnings.
6. **Preview and visual QC**: `bbrender.render_sheet` + `render(..., view="hero")` and READ the PNGs (but check critical pixels in ASCII: rendering smooths and hides pixel-art defects).
7. **Ship**: save `.bbmodel`, `bbglb.build_glb`, `bburl.build_url` → `link.txt`. Iterate by re-running the build (everything is deterministic).
8. **If the model is animated**: call `bbmodel.preserve_animations(prev, m)` before save (see "Animations" section).

## Essential API

### bbmodel.py
- `Model(name, tex_w, tex_h, density=2, format="free")` — texture and resolution.
- `m.group(name, origin, rotation=(0,0,0), color=None, parent=None)`
- `m.cube(name, frm, to, group, origin=None, rotation=None, inflate=0.0, mirror_uv=False, faces=None, uv=None)` — `faces` = subset of the 6 directions; `uv=None` auto-allocates per face; dict per face for manual.
- `m.mesh(name, vertices, faces, group, uv="planar")` — `free` only; faces CCW seen from outside; planar quads.
- `Cube.mirror(axis, center)` / `Mesh.mirror(axis, center)` — mirrors THE cube toward the center (axis 0/1/2 = X/Y/Z).
- `m.uv_regions()` — `{(element, face): [u1,v1,u2,v2]}` for painting.
- `m.bake()` — tris in world space with per-corner UV (used by GLB/render).
- `m.stats()` — elements/groups/tris/uv_regions/tex_used_pct.
- `m.save(path)`, `Model.load(path)`, `m.reset_alloc()` (only for loaded ones; see pitfalls).
- `m.animations` — list of animation dicts in BB format; `to_dict()` already emits (does not zero).
- `bbmodel.preserve_animations(prev, m)` — **mandatory on rebuild of an animated model** (see section below).
- `bbmodel.det_uuid(kind, name)` — deterministic uuid (uuid5); keeps bones stable across builds.

### bbtex.py
- `Canvas.for_model(m)`, `encode_png`/`decode_png`, `col/hexof/shade/mix/load_palette`.
- Writing: `set/rect/line_h/line_v/ellipse/fill_region`.
- Regions: `region_bbox/fill_region/panel(base,light,dark)/ao/outline_region/hstripes/vstripes/dots/checker/dither`.
- Face: `eyes(eye_color, spark_color, size, gap, y_frac)/blush/mouth_smile/mouth_o`.
- Spots: `spot(region, cx_frac, cy_frac, r, snap=True)` — use `snap=True` and r≥2.4 (otherwise becomes diamond/cross), `spots()` for batches.
- Finishing: `bleed(region, px=1)` (bleeds 1px border at junctions), `to_png(indexed=None)`, `palette_used()`.

### bbcheck.py
- `bbcheck.check(path_or_dict, style=False, tex_override=None) -> dict(errors/warnings/infos/report)`.
- CLI: `python3 bbcheck.py model.bbmodel [--style] [--tex texture.png]` (exit 1 if there is an error).
- Checks: uuid/refs of the outliner, texture index, UV within bounds, from<to, duplicate faces, zero area, stretch >1.5×, mesh planarity/winding, Java-block −16..32, tri budgets.
- `--style`: pure black/white = ERROR; magenta = warning; palette >20 = warning; texel density variation >1.6× = warning.

### bbglb.py / bburl.py / bbrender.py
- `bbglb.build_glb(baked, name) -> bytes`; `bbglb.check_glb(data)`; CLI validates file.
- `bburl.build_url(model, name) -> str`; `bburl.verify(url)` roundtrip; CLI `--out link.txt --verify`.
- `bbrender.render(model_or_baked, path, view="iso"|"front"|"side"|"hero"|..., size, supersample=2)`; `bbrender.render_sheet(model, path)` = front+iso+side.

## Animations — preserve on rebuild (DO NOT skip)

Animated models are sometimes authored by script and then animated by an external tool (e.g. `bbanim_*`), which writes `animations` directly into the `.bbmodel`. The `build.py` script rebuilds the model from scratch, so **without the 3 steps below every animation is silently deleted**.

1. **Snapshot** the previous file at the start of `main()`:
   ```python
   prev = None
   if os.path.exists(bb_path):
       prev = json.load(open(bb_path, encoding="utf-8"))
   ```
2. **Build** the new model normally (`m = build()`).
3. **Relink** the animations by bone NAME, before `save`/`build_url`:
   ```python
   if prev and prev.get("animations"):
       bbmodel.preserve_animations(prev, m)
   ```

Why it works: `animations[].animators` is indexed by the **bone UUID**, and the build reconstructs the hierarchy. Since `Model` uses **deterministic uuids** (`det_uuid`, derived from the name), bones with the same name keep the same UUID — and `preserve_animations` still remaps by name and drops bones that disappeared (warns on stderr). Good side effect: the build becomes byte-identical across runs.

`preserve_animations` accepts a dict, a `.bbmodel` path or a loaded `Model`.

## Web app link — the extension is mandatory

```
https://web.blockbench.net/#loadtype=json&loadname=NAME.bbmodel&loaddata=DATA
```

The web app picks the codec by the **extension** of `loadname` (`js/io/io.js`: `pathToExtension(file.path)` against `codec.load_filter.extensions`). Without `.bbmodel` in `loadname`, no codec matches and the app shows **"invalid format"** (`unsupportedFileFormatMessage`). `bburl.build_url()` already appends the extension and `bburl.verify()` fails if it's missing — so never generate the URL by hand.

`verify()` reproduces the real parser of the app (`js/web.ts`): one `decodeURIComponent` on the whole hash, `split('&')` and `re.split(r'=\s*(.+)')` per field.

## Golden rules

1. `from < to` in every cube; pivot on the joint when rigged.
2. Never pure black/white — shadow is a dark saturated color from the palette.
3. Target 8–20 colors; each material with 2–3 tones (base/light/dark) + rim.
4. Equal texel density (~2 px/unit) for all elements.
5. Hidden faces OMITTED (`faces=[...]`) — saves tris and UV.
6. 1px bleed (`bleed`) between UV islands touching in 3D.
7. Small circumferences: radius ≥2.4 and integer center (`snap=True`).
8. Always run `bbcheck --style` and READ the previews before shipping.
9. Deterministic model: fixed seed, same colors → same byte output. Uuids are already deterministic (`det_uuid`), so rebuilds are byte-identical.
10. **Animated model**: preserve animations on rebuild (snapshot + `preserve_animations`) — otherwise they vanish without error.
11. **Web app link**: always via `bburl.build_url` (it guarantees `.bbmodel` in `loadname`); a hand-built URL opens "invalid format".

## References

- `references/bbmodel-spec.md` — canonical facts of the format (vertices, winding, UV, rotation, outliner, GLB, URL).
- `references/pitfalls.md` — pitfall catalog (symptom → cause → fix).
- `references/style-cute-cartoon.md` — art direction: proportions, palette, lighting, readability at 64px.
- `references/blockbench-workflow.md` — testing/editing in Blockbench, exporting to engines, web app limits.
