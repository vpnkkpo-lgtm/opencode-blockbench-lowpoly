#!/usr/bin/env python3
"""
bbglb.py — pure-Python GLB exporter (no three.js, no node).

Takes the dict from bbmodel.Model.bake() and writes a valid .glb (glTF 2.0):
- 1 mesh, triangulated, non-indexed, flat normal per triangle
- Direct UV: glTF uses top-left origin -> uv = (u_px/tex_w, v_px/tex_h), no 1-v
- PBR material: metallic 0, roughness 1; alphaMode MASK if any alpha < 255
- sampler with NEAREST (9728/9986) to preserve the pixel look
- embedded PNG texture in a bufferView

Usage:
    from bbglb import export_glb
    export_glb(model, "output.glb")     # model = bbmodel.Model
    export_glb(model.bake(), "output.glb")

    python3 bbglb.py --demo            # build + export + validates roundtrip
"""

import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


def _pad4(b, fill=b"\x00"):
    extra = (-len(b)) % 4
    return b + fill * extra


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normal(p0, p1, p2):
    n = _cross((p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]),
               (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]))
    ln = (n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) ** 0.5
    if ln < 1e-12:
        return (0.0, 1.0, 0.0)
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def build_glb(baked, name="model", generator="blockbench-lowpoly (pure python)"):
    """baked: dict with tris/tex_w/tex_h/png (output of bbmodel.Model.bake())."""
    tris = baked["tris"]
    if not tris:
        raise ValueError("model has no triangles to export")
    tex_w = baked.get("tex_w") or 16
    tex_h = baked.get("tex_h") or 16
    png = baked.get("png")

    # unique vertices (pos, normal, uv) with index
    unique = {}
    indices = []
    positions = bytearray()
    normals = bytearray()
    uvs = bytearray()
    min_p = [1e30, 1e30, 1e30]
    max_p = [-1e30, -1e30, -1e30]
    for (p0, p1, p2, uv0, uv1, uv2) in tris:
        n = _normal(p0, p1, p2)
        for p, uv in ((p0, uv0), (p1, uv1), (p2, uv2)):
            key = (tuple(round(c, 6) for c in p), tuple(round(c, 6) for c in n), (round(uv[0], 6), round(uv[1], 6)))
            idx = unique.get(key)
            if idx is None:
                idx = len(unique)
                unique[key] = idx
                positions += struct.pack("<fff", *p)
                normals += struct.pack("<fff", *n)
                uvs += struct.pack("<ff", uv[0] / tex_w, uv[1] / tex_h)
                for i in range(3):
                    min_p[i] = min(min_p[i], p[i])
                    max_p[i] = max(max_p[i], p[i])
            indices.append(idx)
    count = len(unique)
    index_count = len(indices)

    bin_data = bytearray()
    views = []

    def add_view(data, target=None):
        nonlocal bin_data
        while len(bin_data) % 4:
            bin_data.append(0)
        off = len(bin_data)
        bin_data += data
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    v_pos = add_view(bytes(positions), 34962)
    v_nrm = add_view(bytes(normals), 34962)
    v_uv = add_view(bytes(uvs), 34962)

    # index buffer
    idx_bytes = struct.pack("<" + "I" * len(indices), *indices) if indices else b""
    v_idx = add_view(idx_bytes, 34963)

    accessors = [
        {"bufferView": v_pos, "componentType": 5126, "count": count, "type": "VEC3",
         "min": [round(v, 6) for v in min_p], "max": [round(v, 6) for v in max_p]},
        {"bufferView": v_nrm, "componentType": 5126, "count": count, "type": "VEC3"},
        {"bufferView": v_uv, "componentType": 5126, "count": count, "type": "VEC2"},
    ]
    # index accessor
    accessors.append({"bufferView": v_idx, "componentType": 5125, "count": len(indices), "type": "SCALAR"})

    material = {
        "name": f"{name}_mat",
        "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 1.0},
        "doubleSided": False,
        "extensions": {"KHR_materials_unlit": {}},
    }
    samplers = [{"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}]
    textures = []
    images = []
    if png:
        alpha = _min_alpha(png)
        if alpha < 255:
            material["alphaMode"] = "MASK"
            material["alphaCutoff"] = 0.5
        v_img = add_view(png)
        images.append({"bufferView": v_img, "mimeType": "image/png"})
        textures.append({"sampler": 0, "source": 0})
        material["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0, "texCoord": 0}

    gltf = {
        "asset": {"version": "2.0", "generator": generator},
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0}],
        "meshes": [{
            "name": name,
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                "indices": 3,
                "material": 0,
                "mode": 4,
            }],
        }],
        "materials": [material],
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(bin_data)}],
    }
    if png:
        gltf["samplers"] = samplers
        gltf["textures"] = textures
        gltf["images"] = images

    gltf["extensionsUsed"] = ["KHR_materials_unlit"]

    json_bytes = _pad4(json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
                       b" ")
    bin_bytes = _pad4(bytes(bin_data))
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out = struct.pack("<III", GLB_MAGIC, 2, total)
    out += struct.pack("<II", len(json_bytes), CHUNK_JSON) + json_bytes
    out += struct.pack("<II", len(bin_bytes), CHUNK_BIN) + bin_bytes
    return out


def _min_alpha(png):
    try:
        import bbtex
        return bbtex.png_min_alpha(png)
    except Exception:
        return 255


def parse_glb(data):
    """Read a GLB back (for tests): returns {'json':..., 'bin': bytes}."""
    if len(data) < 12:
        raise ValueError("GLB too short")
    magic, version, total = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC:
        raise ValueError("invalid magic")
    if version != 2:
        raise ValueError(f"glTF version {version} != 2")
    if total != len(data):
        raise ValueError(f"header length ({total}) != actual bytes ({len(data)})")
    pos = 12
    gltf = None
    binchunk = b""
    while pos < len(data):
        ln, typ = struct.unpack("<II", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        pos += 8 + ln
        if typ == CHUNK_JSON:
            gltf = json.loads(body.decode("utf-8"))
        elif typ == CHUNK_BIN:
            binchunk = body
    if gltf is None:
        raise ValueError("no JSON chunk")
    return {"json": gltf, "bin": binchunk}


def check_glb(data, verbose=False):
    """Structural sanity check of a GLB. Returns (ok, [problems])."""
    problems = []

    def bad(msg):
        problems.append(msg)

    try:
        parsed = parse_glb(data)
    except Exception as exc:
        return False, [f"parse: {exc}"]
    g, binchunk = parsed["json"], parsed["bin"]
    if g.get("asset", {}).get("version") != "2.0":
        bad("asset.version != 2.0")
    prims = g.get("meshes", [{}])[0].get("primitives", [])
    if not prims:
        bad("no primitives")
        return False, problems
    prim = prims[0]
    if prim.get("mode", 4) != 4:
        bad("mode != TRIANGLES")
    for attr, acc_i in prim.get("attributes", {}).items():
        acc = g["accessors"][acc_i]
        bv = g["bufferViews"][acc["bufferView"]]
        comp_size = {5126: 4, 5123: 2, 5125: 4}.get(acc["componentType"], 0)
        n_comp = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[acc["type"]]
        expect = acc["count"] * comp_size * n_comp
        if bv["byteLength"] < expect:
            bad(f"{attr}: bufferView too short ({bv['byteLength']} < {expect})")
        if attr == "POSITION" and ("min" not in acc or "max" not in acc):
            bad("POSITION without min/max")
        if attr == "TEXCOORD_0":
            off = bv.get("byteOffset", 0)
            for i in range(acc["count"]):
                u, v = struct.unpack_from("<ff", binchunk, off + i * 8)
                if not (-0.001 <= u <= 1.001 and -0.001 <= v <= 1.001):
                    bad(f"UV[{i}] out of [0,1]: {u:.3f},{v:.3f}")
                    break
    if "images" in g:
        img_bv = g["bufferViews"][g["images"][0]["bufferView"]]
        off = img_bv.get("byteOffset", 0)
        png = binchunk[off:off + img_bv["byteLength"]]
        if not png.startswith(b"\x89PNG"):
            bad("embedded image is not PNG")
        want_idx = g["materials"][0].get("pbrMetallicRoughness", {}).get("baseColorTexture", {}).get("index")
        if want_idx is None:
            bad("image present but material has no baseColorTexture")
    if verbose:
        print(f"GLB ok: {len(problems)} problem(s), {len(data)} bytes")
    return not problems, problems


def export_glb(model_or_baked, path, name=None):
    if hasattr(model_or_baked, "bake"):
        name = name or getattr(model_or_baked, "name", "model")
        baked = model_or_baked.bake()
    else:
        baked = model_or_baked
    data = build_glb(baked, name=name or "model")
    with open(path, "wb") as fh:
        fh.write(data)
    return path, len(data)


def _demo():
    import bbmodel as bm
    import bbtex
    m = bm.Model("glb_demo", tex_w=64, tex_h=64, density=1)
    g = m.group("root")
    m.cube("base", [0, 0, 0], [16, 4, 16], group=g)
    m.cube("top", [2, 4, 2], [14, 12, 14], group=g)
    png = bbtex.blank_png(64, 64, color=(230, 80, 100, 255))
    m.attach_texture_bytes(png)
    import tempfile
    path, size = export_glb(m, os.path.join(tempfile.gettempdir(), "bbglb_demo.glb"))
    data = open(path, "rb").read()
    ok, problems = check_glb(data, verbose=True)
    assert ok, problems

    baked = m.bake()
    parsed = parse_glb(data)
    acc = parsed["json"]["accessors"][0]
    assert acc["count"] > 0, "POSITION count wrong"
    off = parsed["json"]["bufferViews"][0]["byteOffset"]
    x, y, z = struct.unpack_from("<fff", parsed["bin"], off)
    assert abs(y - min(acc["min"][1], y)) < 1e-6
    m1 = m.stats()["tris"]
    assert m1 == len(baked["tris"]), "stats.tris != bake"
    print(f"bbglb smoke OK — {len(baked['tris'])} tris, {size} bytes")


if __name__ == "__main__":
    if "--export" in sys.argv:
        idx = sys.argv.index("--export")
        in_path = sys.argv[idx + 1]
        out_path = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else None
        import bbmodel as bm
        model = bm.Model.load(in_path)
        out = out_path or in_path.replace(".bbmodel", ".glb")
        path, size = export_glb(model, out)
        print(f"GLB exported: {path} ({size} bytes)")
    elif "--demo" in sys.argv or len(sys.argv) == 1:
        _demo()
    else:
        in_path, out_path = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
        data = open(in_path, "rb").read()
        ok, problems = check_glb(data, verbose=True)
        for p in problems:
            print(" -", p)
        sys.exit(0 if ok else 1)
