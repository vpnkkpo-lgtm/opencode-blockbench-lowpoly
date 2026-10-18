# Style guide — horror / horror low poly

Technical premise: the render (`bbrender`) and the GLB use **neutral lighting** and NEAREST texture — all the horror mood comes from the **painted TEXTURE** and the **silhouette**. Don't rely on scene lighting.

## 1. The "wrong" silhouette

- Intentionally uncomfortable proportions: arm too thin and too long, narrow trunk, tilted head, one shoulder bigger than the other.
- Real asymmetry: one desynced eye (different sizes), mouth torn on one side only, missing ear.
- Tears = 1px notches on the EDGE of the silhouette (on the front face, background-transparent pixels), never in the middle of the face.
- No cute roundness: straight corners, visible edges. If it reads as "threat" at 64px, it's right.

## 2. Palette (horror)

- Desaturated + **1–2 high-charge accents**: blood `#7d2f33`, bile `#c2cf4e`, bioluminescence `#58e0c8`.
- Horror "black" is **wet**: `#120d14`, `#0e1b26` — never `#000000` (the lint rejects it, and flat death reads cheap).
- Skin: pale/dead (gray-green, pink-gray), never a healthy tone.
- Ready palettes: `templates/palettes_horror.json` (`zombie`, `vampire`, `abyssal`, `spectral`, `slime`).

## 3. Surface: dirt, moisture, rot

- **NO clean `panel`.** Light is dirty: `dither` + loose `spot` of `dark`/`accent` tones scattered irregularly over the base.
- Moisture = large dark blotches with irregular edges (`dither` dense, 40–60%) + 1px light on top of each blotch (shine of something wet).
- Blood stains: `spot(r≥2.4, snap=True)` dark red + **dripping**: 2–4px `line_v` descending from the stain, with loose `set` pixels at the tips.
- Rot: 2–3 spots with the `accent` tone + `outline` border (a hole/wound reads better with internal contrast).
- Inverted rim (optional): instead of the light line on top (`panel`), paint the light line at the BOTTOM — light coming from the floor (bonfire, abyss). Cheap and powerful inversion.

## 4. Face

- Empty socket: socket = 3×3 `outline` block with **1 single `glow` pixel** asymmetric inside. Eyes of different sizes (e.g., 2×2 and 3×3).
- Mouth: too big for the head, teeth = 1px `light` `dots(step=2)` (bone).
- **No blush.** No smile. `mouth_o` at double width reads as a scream.
- One detail of strangeness only: neck too thin, stitching on the face, second smaller pair of eyes.

## 5. Details (horror kit)

| effect | recipe |
|---|---|
| stitching | `line_h` + `dots(step=2)` 1px crossing the line |
| bandage | `hstripes` 2 light tones + 1px `outline` between turns |
| exposed bone | `#cfc3a0` blotch with `outline` around + 1px `light` on top |
| dripping | `spot` + descending `line_v` with gaps (isolated pixels) |
| glowing eye | dark socket + 1px `glow`; NEVER cute spark/shadow |

## 6. Budget and QC

- Horror mob budget up to 3000 tris; asymmetry matters more than detail.
- Mandatory QC: `bbrender` and **look** — the test is "does this threaten me?" at 64px. If it turned goofy (big symmetric mouth + centered round eyes = cute, not scary), break the symmetry.
- `bbcheck --style`: 0 errors (pure black/white = rejected) and palette ≤20.

## 7. Don'ts

- Pixel-perfect gore: at 128px it becomes noise. Suggest, don't draw everything.
- Uniform cute outline: here the outline is dirty and broken (1px gaps are welcome).
- "Correct" lighting: horror uses wrong light on purpose (from below, from behind).

Other styles in the skill: `style-cute-cartoon.md`, `style-dark.md`, `style-realistic.md` — same pipeline, different silhouette/painting.
