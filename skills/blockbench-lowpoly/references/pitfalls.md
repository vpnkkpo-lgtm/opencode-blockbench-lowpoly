# Pitfall catalog (symptom → cause → fix)

## Geometry

- **"invalid format" when opening the link** → `loadname` without `.bbmodel`. Fix: always use `bburl.build_url` (it adds the extension) and `bburl.verify`.
- **Mesh with inverted normals / black faces** → vertices not CCW seen from outside. Fix: reverse the vertex order in the face.
- **Cube "flipped" after mirror** → forgetting to swap faces. `Cube.mirror` already does it; don't hand-build mirrors.
- **`from > to`** → BB normalizes but the solver/normal assumes the order; fix the order at the source.
- **Mesh with vertices in world space** → `vertices` are relative to `origin`; subtract the origin.
- **Group origin wrong** → rotation pivots on the wrong point; set `origin` to the joint.

## UV

- **Texture "bleeding" between islands** → no 1px bleed. Fix: `bleed(region, px=1)`.
- **`u1 > u2` after mirror** → **valid**, do not "correct". Exporters consume directly.
- **Stretch >1.5×** → face UV too distorted; redesign the face or split.
- **UV out of bounds** → region outside the texture; check `uv_regions()`.

## Texture

- **Pure black/white** → breaks the style; use saturated dark/light colors.
- **`ValueError: texture full`** → texture too small for the detail; grow the texture (density 3 / 256×256).
- **Spots become diamond/cross** → `snap=False` or r<2.4. Fix: `snap=True`, r≥2.4, integer center.
- **Magenta in the texture** → warning; replace with palette colors.

## Outliner

- **Element outside the outliner** → re-attached to root with warning; check uuid/parent.
- **Group not found** → uuid mismatch; `Model.load` supports 4.x and 5.0.

## Animations

- **Animations vanish on rebuild** → forgot `preserve_animations`. Fix: snapshot + relink.
- **Mirrored motion** → wrote old `format_version` with corrected animation. Keep 5.0.

## URL / web app

- **"invalid format"** → missing `.bbmodel` in `loadname`.
- **URL too long** → ~1.5M chars limit; base64 textures dominate. Reduce texture or save the `.bbmodel`.
- **`verify()` fails** → extension missing or bad encoding.

## Performance

- **Too many tris** → omit hidden faces (`faces=[...]`), reduce bevel on hidden pieces.
- **Stretch >1.5×** → warning; redesign.

## General

- **Non-deterministic build** → use `det_uuid` (already default); fixed seed.
- **Loaded model edits break UV** → use `uv=` explicit or `reset_alloc()`.
