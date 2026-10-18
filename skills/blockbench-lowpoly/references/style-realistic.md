# Style guide — "realistic" in low poly

Technical premise: the render/GLB uses neutral lighting; realism here does NOT come from detailed texture or scene lighting — it comes from **natural proportion + directional light painted into the texture + no outline**. It's "value realism", not detail realism.

## 1. Natural proportion

- Use a real reference as a contract: human ~7–7.5 heads; animal with correct anatomy (shoulders/withers, hip, tail); props with real measurements (chair ~1u seat? scale everything in the same modeling unit).
- No chibi: small eyes (1–2px), proportional head, limbs with joints in the right places.
- Silhouette: the test changes — here it must read as "the real object", not as an icon. Fine detail can live in the texture.

## 2. Painted directional light (the heart of the style)

- Pick ONE global light direction (e.g., top-left-front) and **respect it across the whole model**, on every piece.
- Paint each face by orientation:
  - `up` → `light` tone
  - `down` → `dark` tone
  - north/south → `base`
  - east/west → between `base` and `light`/`dark` depending on the light side
- Opposite faces NEVER share the same value. That's what makes the eye read volume in low poly.
- `panel` with only 2 tones here (light line on top, dark on bottom) — or not even that: `fill_region` + per-face adjustment.

## 3. Palette (realistic)

- Natural and desaturated: earth, olive, slate, sand, leather, straw. Leaf green is `#55703c`, not `#00ff00`.
- **VALUE** steps > hue steps: the 3 tones of a material vary light/dark, they don't change color.
- 12–20 colors; `accent` = 2nd material (wood on stone, rust on iron, flower in a field).
- Ready palettes: `templates/palettes_realistic.json` (`forest`, `rock`, `leather`, `iron`, `field`).

## 4. NO outline

- 1px outline is cartoon language — realistic **doesn't use** it. Separate pieces by value (dark piece against light piece) and by AO.
- `ao` matters more than ever: 1–2px at the base and on the unlit side of every region touching another.

## 5. Material textures (recipes)

| material | recipe |
|---|---|
| wood | irregular `hstripes` (2 tones, break the pattern with `set`) + 1–2 knots (`dots` 1px `dark`) |
| stone | `dither` 20–30% between base/dark + 2–3 1px cracks |
| metal | bands: 1px `light` on top, `base` on body, 1–2px `dark` at bottom; short `light` scratch |
| cloth | `vstripes` 2 tones (fold) + `ao` at the hem |
| skin/leather | smooth base + light `dither` (15%) at joints/shadows |
| dirt | `dither` of `shadow` concentrated at BASES (feet, skirting) and inner corners |

- Detail (plank, brick, grain) at MOST 25% of the area — low-poly realism is value, not noise.

## 6. Budget and QC

- Realistic props: up to 800 tris; characters up to 3000.
- QC with the squint test (squint/look at 48px): does it read as the real object? If it "floats or shines wrong", directional light is inconsistent across faces/pieces — fix the direction first.
- Texel density: keep ~2 px/unit as always; variable texel density betrays the artist's hand, not the material.
- `bbcheck --style`: pure black/white = error; use `#26282c` and `#e8e4dc` as extremes.

## 7. Don'ts

- Outline: rejected in this style.
- Gradient/airbrush: this toolkit is flat (hard pixels); volume comes from face + AO.
- "Photographic" texture: excessive irregular blotching becomes dirt at 64px. Clean value + 1–2 well-placed details.

Other styles in the skill: `style-cute-cartoon.md`, `style-horror.md`, `style-dark.md` — same pipeline, different silhouette/painting.
