# blockbench-lowpoly

A pure-Python toolkit for building low-poly 3D assets from code, packaged as an OpenCode v2 skill/plugin.

No Blender, no editor, no MCP. You describe a character, prop, weapon or mob and you get a `.bbmodel` (Blockbench project), a `.glb` (for your engine), preview PNGs and a link that opens the model straight in the Blockbench web app. Everything is deterministic and versionable.

## Install

Add to `opencode.json(c)`:

```jsonc
{
  "plugins": ["github:vpnkkpo-lgtm/opencode-blockbench-lowpoly"]
}
```

Or clone and point locally:

```jsonc
{ "plugins": ["./opencode-blockbench-lowpoly"] }
```

Or just copy `skills/blockbench-lowpoly` into `~/.config/opencode/skills/`.

## Quick example

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

## What's inside

- `scripts/bbmodel.py` — Model/Group/Cube/Mesh builder, UV, mirror, bake, load/save
- `scripts/bbtex.py` — pure PNG encode/decode + cartoon painting canvas
- `scripts/bbcheck.py` — validator (geometry, UV, outliner, style, budgets)
- `scripts/bbglb.py` — GLB exporter (glTF 2.0, embedded texture)
- `scripts/bburl.py` — Blockbench web app link + roundtrip verification
- `scripts/bbrender.py` — software rasterizer (ortho/iso/hero previews)
- `scripts/bbkit.py` — bevel/taper/wedge/pyramid/cylinder/sphere + face-relative detail helpers
- `templates/` — 4 curated palettes (cute, dark, horror, realistic)
- `examples/` — `mascote_cogumelo` and `espada`, end to end
- `references/` — format spec, pitfalls, style guides, workflow

## Style

Cute cartoon by default, but the same pipeline works for horror, dark fantasy and realistic low poly. See `references/style-*.md`. Rules of thumb: silhouette readable at 64px, head 35-50% for cute, 8-20 colors, never pure black/white, hidden faces omitted.

## Support

If this saved you time, a star helps. Pix donations welcome — replace the placeholder below with your key:

```
Pix key: [your-pix-key-here]
```

Suggested key types: a random key (most private), your email, or your phone. Generate one in your bank app and paste it here.

## License

MIT.
