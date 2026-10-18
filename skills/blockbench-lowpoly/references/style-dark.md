# Style guide — dark / dark fantasy (grimdark)

Technical premise: neutral lighting in render/GLB — the **bleak** mood comes from the texture: dark values, high contrast, painted wear. This is not horror (organic/sick); here it's **solemn, heavy, corroded**.

## 1. Heavy silhouette

- Mass and weight: shoulders/pauldrons WIDE (wider than the waist), helmet/hood, gorget/cape as a rectangular block behind, wide boots.
- Proportion 4–6 heads (heroic-monstrous, not chibi). Static, frontal, imposing pose.
- Layers: pauldron over arm, belt over cloak, cape breaking the silhouette behind. 2–3 masses, no fine detail.

## 2. Palette (dark)

- Base: charcoal `#3e4450`, iron `#4a4e59`, old leather, wine/purple cloak. Everything **desaturated**.
- HIGH contrast: shadow almost black (`#14161c`, never `#000000`) against light `metal`. Mid-tones vanish; jump straight from dark to light.
- **1 warm accent per piece** — ember `#d87a2a`, rune `#4ec8a0`, dried blood `#8a3a2e` — that's what gives "life" in the middle of the bleakness.
- Ready palettes: `templates/palettes_dark.json` (`knight`, `necromancer`, `forge`, `swamp`).

## 3. Surface: wear and corrosion

- `panel` with 2 tones (light/dark) works — but **asymmetric**: scratch the panel lines with loose `set` calls (1px gaps) so it doesn't read as new.
- Upper edges: short 1px `light` scratch (2–3px) on exposed edges. That's the "scraped metal".
- Base of pieces (cloak hem, soles, armor skirt): 1–2px of `dither` in the `shadow` tone — ground dirt.
- Metal: HARD separation per face — top `light`/`metal`, side `base`, bottom `dark`. No gradient; 1px transition at most.
- Cloth: `vstripes` 2 tones (vertical folds) + `ao` at the bottom. Chain/ring: `dots(step=2)` in a column.

## 4. Details (grimdark kit)

| effect | recipe |
|---|---|
| rivet | 1 `metal` light pixel + 1px `outline` below |
| plate layers | 1px `outline` line between plates + `light` on top of each |
| rune | 2–4px of `accent` as a scratch (L, T, X) — only 1 per piece |
| eye under helmet | 1px `outline` band + 1 `accent`/`glow` pixel |
| emblem | 2×2 `accent` block with 1px outline; not perfectly symmetric |

## 5. Face / expression

- Closed helmet is the default (darker, less work). If there's a face: pale desaturated skin, eyes = 1px cold `glow`, no mouth (or 1px straight line).
- Scar: 2–3px `dark` `line_v` with a gap in the middle.
- Never blush, never eye spark.

## 6. Budget and QC

- Up to 3000 tris; form > detail. If the preview turns into "gray blur", contrast between blocks is low — raise `metal`/`accent`.
- QC: DARK average value is the goal, but every block needs 2 distinct values (200–300% luminance difference between top and bottom).
- `bbcheck --style`: pure black/white = error; `#14161c`/`#e8e4dc` are the safe extremes.

## 7. Don'ts

- Desaturating everything EQUALLY: without the warm accent, the model reads as illegible dirt.
- Cute outline: here the outline is "smoke" — dark but NOT black, and gaps are welcome.
- Fine detail in dark areas: doesn't survive at 64px. Mass and contrast only.

Other styles in the skill: `style-cute-cartoon.md`, `style-horror.md`, `style-realistic.md` — same pipeline, different silhouette/painting.
