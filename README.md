# 🧱 Blockbench LowPoly

A pure-Python toolkit for building low-poly 3D assets from code, packaged as an OpenCode v2 plugin.

No Blender, no editor, no MCP, no dependencies. Describe a character, prop, weapon or mob and you get a `.bbmodel` (Blockbench project), a `.glb` for your engine, preview PNGs and a link that opens the model straight in the Blockbench web app. Builds are deterministic, so re-running gives the same bytes.

[![GitHub stars](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenCode Plugin](https://img.shields.io/badge/OpenCode-v2%20plugin-7c3aed)](https://opencode.ai)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://python.org)
[![Zero Deps](https://img.shields.io/badge/deps-zero-brightgreen)](#)
[![Blockbench](https://img.shields.io/badge/Blockbench-web%20app-0ea5e9)](https://web.blockbench.net)

---

## What you get

| Deliverable | File | Purpose |
|---|---|---|
| Native project | `.bbmodel` | Open/edit in Blockbench |
| Engine/runtime | `.glb` | Unity, Godot, Unreal, Three.js |
| Preview | `preview_sheet.png` | Quick visual check (front/iso/side) |
| Shareable link | `link.txt` | Opens the model in the Blockbench web app |

One `build.py` does the whole thing. Run it again and you get the same output.

---

## Install

Add to `opencode.json(c)`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "github:vpnkkpo-lgtm/opencode-blockbench-lowpoly"
  ]
}
```

Or clone and point locally:

```jsonc
{
  "plugins": ["./opencode-blockbench-lowpoly"]
}
```

Or copy `skills/blockbench-lowpoly` into `~/.config/opencode/skills/` and use it as a plain skill.

---

## Quickstart

```python
import sys, os
sys.path.insert(0, "skills/blockbench-lowpoly/scripts")
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl, bbglb

m = Model("mushroom", tex_w=128, tex_h=128, density=2)
body = m.group("body", origin=(8, 0, 8))
m.cube("trunk", (5, 0, 5), (11, 8, 11), group=body,
       faces=["north", "east", "south", "west"])

c = bbtex.Canvas.for_model(m)
c.panel(m.uv_regions()[("trunk", "north")], "#f6ddb8", light="#fdefd6", dark="#e8c894")
m.attach_texture_bytes(c.to_png())

assert not bbcheck.check(m.to_dict(), style=True)["errors"]
bbrender.render_sheet(m, "preview.png", size=384)
m.save("asset.bbmodel")
open("asset.glb", "wb").write(bbglb.build_glb(m.bake(), "asset"))
open("link.txt", "w").write(bburl.build_url(m, "asset"))
```

Output: `asset.bbmodel`, `asset.glb`, `preview.png`, `link.txt`. No errors, no warnings.

---

## Pipeline

```
plan silhouette → pick palette → build geometry → paint texture → validate → preview → ship
```

1. Plan on paper. Silhouette readable at 64px, head 35-50% for the cute style, tri budget (prop ~800, character ~3000).
2. Pick a palette from `templates/palettes_cute.json` or define 8-20 colors. Never pure black/white.
3. Build geometry with `Model.cube` / `Model.mesh`. `from < to`. Pivot on the joint when rigged.
4. Paint with the Canvas using `uv_regions()` as the map: `panel`, `outline_region`, `eyes/blush/mouth_smile`, `spot(snap=True)`.
5. Validate with `bbcheck.check(d, style=True)`. Aim for 0 errors and 0 warnings.
6. Preview with `render_sheet` and `render(..., view="hero")`, then look at the PNGs.
7. Ship: `save .bbmodel`, `bbglb.build_glb`, `bburl.build_url` into `link.txt`. Re-run the build to iterate.
8. For animated models, call `bbmodel.preserve_animations(prev, m)` before saving.

---

## API

### `bbmodel.py`
- `Model(name, tex_w, tex_h, density=2, format="free")`
- `m.group(name, origin, rotation=..., parent=...)`
- `m.cube(name, frm, to, group, faces=None, uv=None, mirror_uv=False, inflate=0.0)`
- `m.mesh(name, vertices, faces, group, uv="planar")` — free format only
- `Cube.mirror(axis, center)` / `Mesh.mirror(axis, center)`
- `m.uv_regions()` · `m.bake()` · `m.stats()` · `m.save(path)` · `Model.load(path)`
- `bbmodel.preserve_animations(prev, m)` · `bbmodel.det_uuid(kind, name)`

### `bbtex.py`
- `Canvas.for_model(m)` · `encode_png`/`decode_png` · `load_palette`
- Writing: `set/rect/line_h/line_v/ellipse/fill_region`
- Regions: `panel/ao/outline_region/hstripes/vstripes/dots/checker/dither`
- Face: `eyes/blush/mouth_smile/mouth_o`
- Spots: `spot(region, cx_frac, cy_frac, r, snap=True)` (r≥2.4)
- Finish: `bleed(region, px=1)` · `to_png()` · `palette_used()`

### `bbcheck.py`
- `check(path_or_dict, style=False, tex_override=None)` → `{errors, warnings, infos, report}`
- CLI: `python3 bbcheck.py model.bbmodel --style --tex texture.png` (exit 1 on error)
- Checks uuid/refs, UV, from<to, duplicate faces, zero area, stretch >1.5×, winding, Java-block, budgets

### `bbglb.py` · `bburl.py` · `bbrender.py`
- `build_glb(baked, name) -> bytes` · `check_glb(data)`
- `build_url(model, name) -> str` · `verify(url)` (roundtrip)
- `render(model, path, view="iso"|"front"|"side"|"hero", size, supersample=2)` · `render_sheet(model, path)`

---

## Style

Cute cartoon by default, but the same pipeline works for horror, dark fantasy and realistic low poly. See `references/style-*.md`. Silhouette readable at 64px, head 35-50% for cute, 8-20 colors, no pure black/white, hidden faces omitted, 1px bleed between UV islands.

---

## Structure

```
opencode-blockbench-lowpoly/
├── src/index.ts              # OpenCode v2 plugin (registers the skill)
├── skills/blockbench-lowpoly/ # the skill (SKILL.md + scripts + refs + templates + example)
│   ├── SKILL.md
│   ├── scripts/   (bbmodel, bbtex, bbcheck, bbglb, bburl, bbrender, bbkit, bbcard)
│   ├── references/ (spec, pitfalls, style, workflow)
│   ├── templates/  (4 palettes)
│   └── examples/  (mascote_cogumelo, espada)
├── package.json
├── LICENSE
└── README.md
```

---

## Web app link

```
https://web.blockbench.net/#loadtype=json&loadname=NAME.bbmodel&loaddata=DATA
```

The web app picks the codec by the extension of `loadname`. Without `.bbmodel`, no codec matches and you get "invalid format". `bburl.build_url()` already appends the extension and `bburl.verify()` fails if it's missing. Don't build the URL by hand.

---

## Why star this

- Deterministic builds (fixed seed, deterministic uuids, byte-identical output)
- Validated before shipping (`bbcheck --style` → 0 errors, 0 warnings)
- Geometry + texture + preview + GLB + link in one script
- Pure Python, no MCP, no editor, no dependencies
- Shareable link opens the model in the Blockbench web app
- Animations survive rebuilds (`preserve_animations`)

If it saved you time, a star is appreciated.

[![Star this repo](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)

---

## ☕ Support

If this toolkit saved you time, consider buying me a coffee.

<div align="center">

### Pix

**`vpnkkpo@gmail.com`**

*Copy the key above and paste it in your bank app.*

[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/vpnkkpo-lgtm)

</div>

Every bit helps keep the project running. Thanks! 🙏

---

## References

- `skills/blockbench-lowpoly/references/bbmodel-spec.md` — format spec
- `skills/blockbench-lowpoly/references/pitfalls.md` — pitfall catalog
- `skills/blockbench-lowpoly/references/style-cute-cartoon.md` — art direction
- `skills/blockbench-lowpoly/references/blockbench-workflow.md` — test/edit/export

---

## Contributing

Issues and PRs welcome. Forged something cool? Add it under `examples/`.

## License

MIT. Do whatever you want, keep the notice.
