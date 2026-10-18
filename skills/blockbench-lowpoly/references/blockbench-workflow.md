# Blockbench workflow (import, edit, export)

## Opening the generated project

1. Generate `link.txt` with `python3 bburl.py model.bbmodel --out link.txt --verify`.
2. Open the link in the browser → Blockbench web loads the model as a new project (loadtype=json).
3. Limit: ~1.5M chars of URL. Exceeded it? Save the `.bbmodel` and open it via *File → Open model* (drag & drop in the desktop/web app with local registry).

## Hand-editing and going back to code

1. Adjust in Blockbench (UV editor, paint mode, move/rotate).
2. *File → Save Model* → `.bbmodel` back to disk.
3. In code: `m = Model.load("model.bbmodel")` — `m.uv_regions()` reflects what's there; **do not** touch cubes without passing explicit `uv=` or calling `m.reset_alloc()` (see pitfalls 7).

## Exporting from Blockbench (when you need the app)

- **glTF/GLB**: *File → Export → Export GLTF*. `bbglb.py` generates the same target without opening the app — use it by default; BB's serves for cross-checking.
- **OBJ**: good for checking tri count (BB also shows the count in the footer).

## Running the GLB in engines

- **Godot 4**: drop the `.glb` into the project (auto-import). Material comes with nearest → set `Filter` on import; texture embedded. If the model looks "lying down", check Y-up (our export is Y-up direct).
- **three.js**: `GLTFLoader.load("asset.glb")` — the NEAREST sampler avoids blur; `alphaMode MASK` cuts transparency hard (ideal for pixel art).
- **Unity/Unreal**: standard glTF import; scale in modeling units (16u ≈ 1 Minecraft block ≈ 1m in free).

## Version compatibility

- `format_version: "5.0"` — opens in Blockbench 4.10+ (current stable). Older 4.x versions migrate the outliner automatically.
- `model_format: "free"` + `box_uv: false`: independent UV per face (what we paint). If opened as `java_block`, BB complains about coords outside the grid — use only for explicit conversion.
- Textures: the file embeds a base64 PNG; exporting to Camera0/BlueMap etc. requires its own format (Bedrock/Java) — convert inside BB (Convert Project).

## Cautions

- Don't regenerate the `.bbmodel` while Blockbench is open holding the old file — save/close before re-running the build.
- The web app re-renders disabled faces "resurrected" if they come back with valid UV — our serializer writes `uv: [0,0,0,0]` + `texture: null` (correct).
- `link.txt` is not stable across generations (base64 texture changes) — that's fine, it's disposable; the canonical artifact is the `.bbmodel`.
