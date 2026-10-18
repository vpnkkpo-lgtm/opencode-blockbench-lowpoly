# .bbmodel format spec (canonical facts)

Source: Blockbench source code (master post-4.10: `outliner/types/cube.js`, `outliner/abstract/face.ts`, `outliner/outliner.js`, `io/format.ts`, `io/formats/obj.js`; web-link from `blockbench-mcp-plugin`). Everything below is implemented and tested in the skill scripts.

## Top-level JSON (format_version 5.0, model_format "free", box_uv false)

```json
{
  "meta": { "format_version": "5.0", "model_format": "free", "box_uv": false, "name": "..." },
  "name": "...",
  "resolution": { "width": 128, "height": 128 },
  "elements": [ ... ],
  "outliner": [ ... ],
  "textures": [ ... ]
}
```

## Cube

- `from` and `to`: [x,y,z] in modeling units; **require `from < to` component-wise** (BB normalizes, but solver/normal assumes the order).
- `origin`: rotation pivot (BB default: cube center).
- `rotation`: degrees, intrinsic order **ZYX** → matrix `R = Rz · Ry · Rx`; rotation around its own `origin`, then ancestor groups around their origins.
- `inflate`: expands geometry without changing UV (anti z-fighting).
- `mirror_uv`: cosmetic editor flag (not used by our exports).
- `faces`: exact keys `north, east, south, west, up, down`. Disabled face = `{ "uv": [0,0,0,0], "texture": null }`. Enabled = `{ "uv": [u1,v1,u2,v2], "texture": 0, "rotation": 0 }`.
- UV in **texture pixels**, with **v growing DOWNWARD** from the top.

### Vertex table (`getGlobalVertexPositions`)

| idx | position |
|-----|----------|
| 0 | to.x, to.y, to.z |
| 1 | to.x, to.y, from.z |
| 2 | to.x, from.y, to.z |
| 3 | to.x, from.y, from.z |
| 4 | from.x, to.y, from.z |
| 5 | from.x, to.y, to.z |
| 6 | from.x, from.y, from.z |
| 7 | from.x, from.y, to.z |

### Indices per face (`getVertexIndices` — internal order v0..v3)

| face | vertices | sense | nominal normal |
|------|----------|-------|----------------|
| north | 1,4,6,3 | CW seen from outside (−Z) | −Z |
| east  | 0,1,3,2 | CW seen from outside (+X) | +X |
| south | 5,0,2,7 | CW seen from outside (+Z) | +Z |
| west  | 4,5,7,6 | CW seen from outside (−X) | −X |
| up    | 4,1,0,5 | CW seen from outside (+Y) | +Y |
| down  | 7,2,3,6 | CW seen from outside (−Y) | −Y |

### UV per corner

The k-th vertex receives the k-th corner: **[(u1,v1), (u2,v1), (u2,v2), (u1,v2)]** (TL, TR, BR, BL — v downward).
`rotation` (0/90/180/270): the 4 corners rotate `r/90` times: `corners = [pop(0)... ]` — each `r/90` moves the first corner to the end (`corners.push(corners.splice(0,1)[0])`).

### Export triangulation (same as BB's OBJ)

Tris `(v2,v1,v0)` and `(v3,v2,v0)` with paired UVs. In GLB: **non-indexed** triangles (3 vertices each), flat normal per triangle.

## Mirror (our `Cube.mirror(axis, c)`)

With `axis` 0/1/2 (X/Y/Z) and center `c`:
- `rotation[(axis+1)%3] *= -1` and `rotation[(axis+2)%3] *= -1`;
- `from' = 2c − to`, `to' = 2c − from`, `origin' = 2c − origin`;
- face swap: X → west↔east, Y → up↔down, Z → south↔north;
- UVs: flip axis (+1)%3 on **all** faces; flip the "identity"/across axis per BB rule (X: flip U on n/s/e/w and on up/down; Z: flip V on n/s/e/w and U on up/down... exact implementation in `bbmodel.py::Cube.mirror`).

**Verified consequence**: the mirror produces `u1 > u2` (UV horizontally mirrored). This is **valid** in bbmodel — exporters and renderers consume coordinates directly without normalizing. Do NOT "fix" it.

## Mesh (only model_format "free")

- `vertices`: list of [x,y,z] **relative to the mesh `origin`**.
- `faces`: `[{ "vertices": [i0,i1,...], "uv": {"i0": [u,v], ...} }]` — indices CCW seen from outside; **planar quads** (or tris); "no uv" → solid texture (BB usually uses corner (0,0)).
- No box_uv: each face has its own UV.

## Outliner

- **5.0 (flat)**: `[ { "name", "uuid", "origin", "rotation", "color" }, { "uuid", "isOpen", "children": [...] } ]` — groups are independent nodes referenced by uuid inside `{uuid, children}` nodes. Elements in the outliner reference the ELEMENT's uuid.
- **4.x (nested)**: `[ { name, uuid, children: [...], origin, rotation } ]` — inline group.
- Our `Model.load` supports both; `to_dict` writes 5.0.
- An element outside the outliner (or with a non-existent parent) is re-attached to the root with a warning.

## Textures

```json
{ "path": "", "name": "texture.png", "folder": "", "namespace": "",
  "id": "0", "particle": true, "uuid": "...", "source": "data:image/png;base64,..." }
```
`faces[d].texture` = index in that list (int) or `null`. The skill always uses index 0.

## Blockbench web app link

```
https://web.blockbench.net/#loadtype=json&loadname=NAME.bbmodel&loaddata=DATA
```

### Hash parser (`js/web.ts`)

```js
let query_string = location.search || location.hash
query_string = decodeURIComponent(query_string.substring(1))
queries = query_string.split('&')
[key, value] = string.split(/=\s*(.+)/)   // regex WITH captured group
```

- **ONE** pass of `decodeURIComponent` then `split("&")` — so the payload cannot contain a raw `&`. Escape at source: `&` → `\u0026` **before** percent-encoding, then `urllib.parse.quote(data, safe="!*'()")` — that's exactly what `bburl.py` does.
- The split uses a regex with a captured group: the first `=` separates key and value, and an `=` inside the base64 (padding) **does not** break, because matching starts at the first `=`.

### The `loadname` extension decides whether it opens (critical)

`js/io/io.js::loadModelFile`:

```js
let extension = pathToExtension(file.path)   // file.path = Blockbench.queries.loadname
if (extensions.includes(extension) && ...)   // codec.load_filter.extensions == ['bbmodel']
...
unsupportedFileFormatMessage(file.path)      // ← "invalid format" in the UI
```

`loadname` without `.bbmodel` ⇒ `extension == ""` ⇒ no codec matches ⇒ error. `build_url` normalizes the name and `verify()` validates the extension.

- `verify()` performs the full roundtrip with the same algorithm as the app.
- Practical web app limit: ~1.5M characters of URL (the skill warns above that). Base64 textures dominate the size.

## Animations

```json
"animations": [{
  "uuid": "...", "name": "idle", "loop": "loop", "length": 2, "snapping": 24,
  "animators": {
    "<GROUP uuid>": {
      "name": "left_wing", "type": "bone",
      "keyframes": [{
        "uuid": "...", "channel": "rotation", "time": 0.5, "color": -1,
        "interpolation": "linear", "data_points": [{"x": 0, "y": 0, "z": 18}]
      }]
    }
  }
}]
```

- **`animators` is indexed by the group (bone) UUID** — hence the need to remap by name when the hierarchy is rebuilt (`preserve_animations`).
- Channels: `position`, `rotation`, `scale`.
- `loop`: `"loop"` | `"once"` | `"hold"`.
- Keyframe direction rule changed in **5.0**: previously, position values were inverted on the X axis and rotation on X and Y. The loader auto-corrects files with `format_version < 5.0` (`invertMolang`) — so **do not** write an old `format_version` together with an already-corrected animation, or the motion comes out mirrored.

## GLB mapping (bbglb.py)

- UV direct `(u_px / tex_w, v_px / tex_h)` — **no** `1 − v` (bbmodel already uses v downward and glTF v upward... the BB exporter inverts; we replicate BB's result with the direct mapping over the corner table).
- Y-up direct (bbmodel is already Y-up).
- Non-indexed triangles, flat normal per triangle, `POSITION` with `min`/`max`.
- Material: `metallicFactor 0`, `roughnessFactor 1`, `doubleSided false`, `alphaMode "MASK"` with `alphaCutoff 0.5` when the texture has partial alpha.
- Sampler `magFilter 9728` (NEAREST), `minFilter 9986` (NEAREST_MIPMAP_NEAREST), wraps 10497 (REPEAT).
- PNG embedded in a bufferView; bufferViews aligned to 4 bytes; JSON chunk (`0x4E4F534A`, padded with space) + BIN chunk (`0x004E4942`, padded with zero).

## Formats and limits

- `free` (ours) and `java_block` (integer coordinates −16..32 per axis — bbcheck warns). Bedrock uses its own geometry; convert inside BB if needed.
- `format_version "5.0"` opens in BB 4.10+ (current). Older versions migrate on their own (BB's loader also accepts 4.x).
