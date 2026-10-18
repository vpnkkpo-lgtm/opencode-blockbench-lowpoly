# 🧱 Blockbench LowPoly

### Forge cute-cartoon 3D assets from code — right inside OpenCode.

[![GitHub stars](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenCode Plugin](https://img.shields.io/badge/OpenCode-v2%20plugin-7c3aed)](https://opencode.ai)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://python.org)
[![Zero Deps](https://img.shields.io/badge/deps-zero-brightgreen)](#)
[![Blockbench](https://img.shields.io/badge/Blockbench-web%20app-0ea5e9)](https://web.blockbench.net)

> **No Blender. No editor. No MCP. No dependencies.** Just pure Python and an agent that obeys.
> Describe a character, a prop, a weapon, a mob — and get `.bbmodel`, `.glb`, preview PNGs and a link that opens the model **directly in the Blockbench web app**. Everything deterministic, everything versionable, everything in code.

---

## ⚡ What you get

| Deliverable | File | Purpose |
|---|---|---|
| Native project | `.bbmodel` | Open/edit in Blockbench |
| Engine/runtime | `.glb` | Unity, Godot, Unreal, Three.js |
| Preview | `preview_sheet.png` | Fast visual QC (front/iso/side) |
| Shareable link | `link.txt` | Opens the model in the Blockbench web app |

One single `build.py`. Run it again, byte-identical. Iterate in seconds.

---

## 🚀 Installation (OpenCode v2)

### Option A — as a plugin (recommended)

Add to your `opencode.json(c)`:

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

Done. The `blockbench-lowpoly` skill is registered automatically and the agent learns to forge low-poly assets.

### Option B — as a standalone skill

Copy the `skills/blockbench-lowpoly` folder to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project). Works without the plugin.

---

## 🎬 Quickstart (30 seconds)

```python
import sys, os
sys.path.insert(0, "skills/blockbench-lowpoly/scripts")
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl

m = Model("mushroom", tex_w=128, tex_h=128, density=2)
body = m.group("body", origin=(8, 0, 8))
m.cube("trunk", (5, 0, 5), (11, 8, 11), group=body,
       faces=["north", "east", "south", "west"])

c = bbtex.Canvas.for_model(m)
c.panel(m.uv_regions()[("trunk", "north")], "#f6ddb8", light="#fdefd6", dark="#e8c894")
png = c.to_png()
m.attach_texture_bytes(png)

rep = bbcheck.check(m.to_dict(), style=True, tex_override=png)  # 0 errors, 0 warnings
bbrender.render_sheet(m, "preview.png", size=384)
m.save("asset.bbmodel")
open("asset.glb", "wb").write(__import__("bbglb").build_glb(m.bake(), "asset"))
open("link.txt", "w").write(bburl.build_url(m, "asset"))
```

Output: `asset.bbmodel` + `asset.glb` + `preview.png` + `link.txt`. **Zero errors. Zero warnings.** 🎯

---

## 🛠️ Full pipeline

```
plan silhouette → pick palette → build geometry → paint texture → validate → preview → ship
```

1. **Plan on paper** — silhouette readable at 64px, head 35–50% in "cute" style, tri budget (prop ≤800, character ≤3000).
2. **Palette** — `templates/palettes_cute.json` or ~8–20 colors of your own. **Never** pure `#000000`/`#ffffff`.
3. **Geometry** — `Model.cube` / `Model.mesh`; `from < to`; pivot on the joint when rigged.
4. **Texture** — Canvas with `uv_regions()` as the map: `panel`, `outline_region`, `eyes/blush/mouth_smile`, `spot(snap=True)`.
5. **Validate** — `bbcheck.check(d, style=True)` → aim for **0 errors and 0 warnings**.
6. **Preview + visual QC** — `render_sheet` + `render(..., view="hero")` and **read** the PNGs (check critical pixels in ASCII).
7. **Ship** — `save .bbmodel`, `bbglb.build_glb`, `bburl.build_url` → `link.txt`. Iterate by re-running the build.
8. **Animated?** — call `bbmodel.preserve_animations(prev, m)` before save.

---

## 📚 Essential API

### `bbmodel.py`
- `Model(name, tex_w, tex_h, density=2, format="free")`
- `m.group(name, origin, rotation=..., parent=...)`
- `m.cube(name, frm, to, group, faces=None, uv=None, mirror_uv=False, inflate=0.0)`
- `m.mesh(name, vertices, faces, group, uv="planar")` — `free` only
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

## 🎨 "Cute cartoon refined" style

- Silhouette readable at **64px**
- Head **35–50%** of the body (cute proportions)
- **8–20 colors**, each material with 2–3 tones (base/light/dark) + rim
- Shadow = saturated dark color (never pure black)
- Texel density ~**2 px/unit** equal for everything
- Hidden faces **omitted** (`faces=[...]`)
- 1px bleed (`bleed`) between UV islands touching in 3D
- Small circumferences: radius ≥2.4, integer center (`snap=True`)

---

## 📂 Structure

```
opencode-blockbench-lowpoly/
├── src/index.ts              # OpenCode v2 plugin (registers the skill)
├── skills/blockbench-lowpoly/ # the skill (SKILL.md + scripts + refs + templates + example)
│   ├── SKILL.md
│   ├── scripts/   (bbmodel, bbtex, bbcheck, bbglb, bburl, bbrender)
│   ├── references/ (spec, pitfalls, style, workflow)
│   ├── templates/  (palettes_cute.json, 7 palettes)
│   └── examples/  (mascote_cogumelo end-to-end)
├── package.json
├── LICENSE
└── README.md
```

---

## 🔗 Web app link — the extension is mandatory

```
https://web.blockbench.net/#loadtype=json&loadname=NAME.bbmodel&loaddata=DATA
```

The web app picks the codec by the **extension** of `loadname`. Without `.bbmodel`, no codec matches → **"invalid format"**. `bburl.build_url()` already appends the extension and `bburl.verify()` fails if it's missing. **Never** build the URL by hand.

---

## 🏆 Why this repo deserves a ⭐

- **Deterministic** — fixed seed, deterministic uuids (`det_uuid`), byte-identical rebuilds.
- **Validated** — `bbcheck --style` guarantees 0 errors/0 warnings before shipping.
- **Complete** — geometry + texture + preview + GLB + link in a single script.
- **Zero friction** — pure Python, no MCP, no editor, no dependencies.
- **Shareable** — a link that opens the model straight in the Blockbench web app.
- **Animatable** — preserves animations across rebuilds (`preserve_animations`).

If this project saved you hours of manual modeling, **leave a star** ⭐ — it's the fuel to keep forging.

[![Star this repo](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)

---

## ☕ Support / Donate

If this toolkit helped you ship assets faster, consider supporting its development.

- **Pix**: (configure your Pix key here)
- **GitHub Sponsors**: https://github.com/sponsors/vpnkkpo-lgtm

Every contribution keeps the forge burning. 🔥

---

## 📖 References

- `skills/blockbench-lowpoly/references/bbmodel-spec.md` — canonical format spec
- `skills/blockbench-lowpoly/references/pitfalls.md` — pitfall catalog (symptom → cause → fix)
- `skills/blockbench-lowpoly/references/style-cute-cartoon.md` — art direction
- `skills/blockbench-lowpoly/references/blockbench-workflow.md` — test/edit/export

---

## 🤝 Contributing

Issues and PRs are welcome. If you forged a cool asset with this toolkit, open a PR adding it under `examples/`.

## 📜 License

MIT — do whatever you want, just keep the notice.

---

<p align="center">
  <b>Built with 💜 for the OpenCode community.</b><br>
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers">⭐ Star on GitHub</a> ·
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/issues">🐛 Report a bug</a> ·
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/fork">🍴 Fork</a>
</p>
