# Fine detail and direct manipulation — getting close to the reference

The typical gap between "the agent modeled it nicely" and "it's close to the reference" is **not texture or palette**: it's geometry. Blockout of straight boxes = blockout read, no matter how well painted. This guide is the kit to get past that.

## 0. Translating the reference (image) into calls

The reference is already on your screen/context — read it with the `read` tool and run it through this table **before** writing the first line of geometry. It's universal: works for any ref (minecraft, concept art, statue photo, another agent's asset).

| What you see in the image | How to write it |
|---|---|
| the silhouette has N "steps"/masses | one piece per mass (macro), `Model.cube` with silhouette `faces` |
| overall proportion (width/height) | pick the scale: height ≈ 16u is the Blockbench/Minecraft default |
| cut corner, chamfered edge, "live edge" | `bbkit.bevel_box(..., bevel=0.2..0.5)` on THAT piece |
| tip that tapers (hat, beak, chest plate, nose) | `bbkit.taper_box(shrink=...)` or `bbkit.pyramid` |
| rounded top / dome / ball | `bbkit.cylinder` or `bbkit.sphere` |
| ramp, roof, hull nose | `bbkit.wedge(axis=0\|2)` |
| rivets, screws, teeth, bricks, buttons | `bbkit.grid_of(nu, nv)` on the right face |
| tape/belt/rim/molding/band on the piece edge | `bbkit.edge_trim(sides=("top","bottom"))` |
| buckle, patch, plate, pocket, chest plate | `bbkit.on_face(cu, cv, du, dv, depth)` |
| a piece on both sides (2 arms, 2 wings) | `bbkit.mirror_group([...], axis, center)` — 1 line, symmetry guaranteed |
| none of the above, just smooth cubes | **missing micro-detail**: ~1 detail every 2–3u of the largest piece's width |
| detail only on the lit side | replicate only there (detail is directional, not symmetric) |

Work order: silhouette → chamfer/tip → medium masses → detail → texture. Skipping straight to detail on top of a smooth box doesn't close the gap.

## 1. The three scales (the rule that decides fidelity)

| Scale | Size | What it is | Example |
|---|---|---|---|
| **Macro** | 100% | silhouette, proportion, pose | body, head, cape |
| **Meso** | 25–100% | masses breaking the block | shoulder pad, waist, brim, tail |
| **Micro** | ≤25% | detail only visible up close | rivet, groove, button, tooth, belt, buckle |

Rule of `bbcheck --detail --type mob`: micro = piece with edge ≤**20%** of the largest dimension (prop: 30%, vehicle: 15%). If the smallest piece in the model exceeds that, **there is no micro** — the most important lint warning. A 16u-tall hero needs pieces of ~0.5–3u to read.

## 2. Trick #1: kill the "box" with bevel

`bbkit.bevel_box(frm, to, bevel)` cuts the 12 edges at 45° (6 octagons + 12 quads + 8 tris). A single element, a silhouette with life, light catching the corners. `taper_box` (smaller/top offset), `wedge` (ramp), `pyramid`, `cylinder`, `sphere` complete the shape vocabulary.

Practical rule: **bevel the pieces on the silhouette** (shoulder, lid, helmet, base), leave raw boxes on what's hidden.

## 3. Small detail: placement by FACE

Guessing rivet coordinates is where agents stall. Use the face as reference:

```python
bbkit.on_face(m, "buckle", "belt", "north", cu=0.5, cv=0.5, du=0.25, dv=0.18, depth=0.12, group=g)
bbkit.grid_of(m, "rivet", "plate", "north", nu=3, nv=2, du=0.2, dv=0.2, group=g)   # 6 rivets
bbkit.edge_trim(m, "rim", "door", "up", thickness=0.15, group=g, sides=("top","bottom"))
```

- `cu/cv` = fraction 0..1 on the face; `du/dv` = size as fraction; `depth` = how far it protrudes; `sink` = penetration (avoids z-fight).
- Bases per face: `north/south` u→±X, v→+Y; `east/west` u→∓Z, v→+Y; `up` u→+X, v→−Z; `down` u→+X, v→+Z.
- By default the detail generates **only the support face + top** (saves UV and tris — side faces of a 0.25u rivet are junk). Pass `faces=[...]` if you want all.
- Detail is never smaller than **1 texel** (`bbkit` expands to that): at `density=2` the practical minimum is 0.5u, at `density=3` it's 0.33u.

## 4. Cheap symmetry

```python
bbkit.mirror_group(m, ["left_arm", "left_hand"], axis=0, center=8, group=g)   # clone + mirror
```
Mirroring a whole group costs one line and guarantees symmetry (which the human eye reads first).

## 5. Texel density: 2 for masses, 3 for detail

| Scenario | `density` | Texture |
|---|---|---|
| body/large pieces | 2 | 128×128 |
| lots of micro-detail | 3 | 256×256 |
| small prop (<8u) | 3 | 128×128 |

Dense detail on a small texture blows up the UV allocator (`ValueError: texture full`) — that's a signal the texture needs to grow, not to cut detail.

## 6. Post-editing (edit what already exists)

Useful when the model came from Blockbench, another agent, or `Model.load()`:

```python
bbkit.find(m, "trunk")                       # get the element
bbkit.bounds(m, "trunk")                     # (frm, to)
bbkit.translate(m, "trunk", (0, 0.5, 0))     # move (origin follows)
bbkit.resize(m, "trunk", 1, 12, anchor="min") # stretch keeping the base
bbkit.set_extent(m, "lid", 1, 14.0)           # snap the `to` edge to the coordinate
bbkit.rotate(m, "arm", (0, 0, 20))            # add degrees (ZYX)
bbkit.set_origin(m, "arm", (4, 6, 6))         # pivot on the joint, no geometry move
bbkit.duplicate(m, "feather_l", "feather_r", offset=(6, 0, 0), group=g)
bbkit.remove(m, "feather_r")                  # undo the copy
```

`set_origin` + `rotate` is the pair that makes character limbs work: pivot on the joint first, then rotate.

## 7. Fidelity QC

```bash
python3 scripts/bbcheck.py model.bbmodel --detail --type mob --style
```

`--type` calibrates thresholds: `mob` (micro ≤20%, stricter alignment alert) · `prop` (≤30%, more tolerant of boxes) · `vehicle` (≤15%) · `diorama` (≤25%). Without `--type`, generic values apply.

- **missing thin piece** → add micro-detail (`on_face`/`grid_of`) or break masses.
- **everything axis-aligned** → tilt a key piece (5–15° already changes everything) or use `bevel_box`.
- **no beveled shapes** → 100% straight boxes: the model reads as blockout.
- Afterward: render 3/4 (`bbrender ... view="hero"`) and confirm the detail shows up in the **silhouette**, not just from the front.

## 8. Anti-patterns

| Mistake | How to fix |
|---|---|
| "decoration" detail with no function | only detail that tells a story: rivet, buckle, belt, trench |
| rivet the size of the chest | micro ≤25% of the larger scale; if you need zoom to see it, the size is right |
| rotating a cube "to add life" | a rotated cube breaks per-face UV reading; prefer `bevel_box`/`taper_box` |
| perfectly symmetric detail on top | break 1–2 units of position, keep the rest symmetric |
| filling with identical pieces | one repeated detail (`grid_of`) is cheaper and more elegant than 6 manual copies |
