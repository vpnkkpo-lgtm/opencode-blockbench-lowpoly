# Style guide — cute cartoon low poly

Art direction applied by the `mascote_cogumelo` example. Goal: instant readability, cute, "hand-made" — not cold minimalism.

## 1. Silhouette first (64px test)

- Render at 64px mentally (or for real, `size=64` in bbrender): if you can't tell WHAT it is, fix the proportions before detailing.
- Base shapes: stacked cubes with softly readable corners (wide hat, chubby body). Slight asymmetry allowed on accessories, never on the body/head axis.
- Details hanging out of the silhouette (ear, wing, hat) — at most 2 elements.

## 2. Cute proportions

- **Head 35–50% of total height.** Example: trunk 8u + hat 5u in 15u → head (hat) ~33–40%.
- Short chubby body; legs/feet **stubbies** (1–3u), often just "feet" with no separate leg.
- Short arms glued to the body (2–3u), with 1u of lighter "hand".
- Eyes below the middle of the face (y_frac 0.28–0.45) — large forehead space = childhood/cuteness.

## 3. Palette

- 8–20 colors in the whole model (non-transparent texels). Each material: **3 tones** (base/light/dark) + outline.
- NEVER pure #000/#fff. Outline = dark saturated version of the base (e.g., red hat outline = wine `#a83a4a`, not black).
- `bbtex.shade(c, amt)`: light warms (+R), shadow cools (+B) — classic pixel art rule.
- Ready palettes: `templates/palettes_cute.json` → `load_palette(path, "mushroom")` etc.
- Other styles in the skill: `style-horror.md`, `style-dark.md`, `style-realistic.md` — same pipeline, different silhouette/painting.
- Signature colors: one vivid accent (pink blush, yellow detail) brings life; use in 1–2 places only.

## 4. Painted surface and lighting

- Every large face gets `panel(region, base, light, dark)`: light line on top, dark line on bottom — simulates top light WITHOUT depending on the render.
- `ao(region, color, edges="bl")`: 1px occlusion in the bottom/inner corner (where it touches another piece).
- `outline_region`: 1px outline on the face = flat pixel-art readability. Use on "front" faces (face, hat).
- Rim light: the panel's light line IS the rim. Don't create gradients.

## 5. Face (formula from the example)

Face region (north face of the head, ~12×8u → 24×16px at density 2):

| feature | parameter | example |
|---|---|---|
| eyes | `eyes(eye, spark, size=2, gap=5, y_frac=0.28)` | dark 2px eye + light 1px spark |
| blush | `blush(color, y_frac=0.5, inset=0, width=3)` | 3×1px soft pink |
| mouth | `mouth_smile(color, y_frac=0.62, width=4)` | 5px "U" (tips cy, middle cy+1) |

- Face occupies ~60% of the face width, vertically centered between 0.25–0.75.
- Variations: `mouth_o` (surprise), closed eye (1px line_h), no eyebrow = cuter.

## 6. Spots and patterns

- `spot(region, cx, cy, r, color, snap=True)`: r 2.4–2.5 = 5px circle; r 3.5 = 7px circle; r ≥4 gets blocky.
- Distribute 3–5 spots of 2 sizes in asymmetric positions BUT with margin (don't touch the outline).
- Stripes: `hstripes`/`vstripes` with 2 tones of the SAME family (base + light).
- `dither(c1, c2, density)`: dotted transition to sell texture on large areas, 50% max.

## 7. Texel density and resolution

- Target: **~2 px/unit** consistent. 6×3u face → 12×6px region.
- Texture in power of 2 (64/128/256) sized to the model: sum face areas + gap; 128×128 served a 7-cube mascot with room to spare.
- `bbcheck --style` warns if density variation exceeds 1.6× — respect it.

## 8. Final QC (visual checklist)

1. `bbrender.render_sheet` + `render(view="hero")` and **read the PNGs** (you see the image).
2. Check: silhouette, eyes in place, mouth correct (U, not mustache), blush visible, round spots, no flat black/white face, no stretch.
3. ASCII dump of 1–2 critical regions (face) when exact pixel matters.
4. `bbcheck --style` → 0 E, 0 W. Only then ship GLB/link.
