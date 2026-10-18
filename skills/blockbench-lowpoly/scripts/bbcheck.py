#!/usr/bin/env python3
"""
bbcheck.py — validator for .bbmodel files (format 5.0, tolerant to 4.x).

Checks invariants that break in Blockbench or in the game engine:
uuids, outliner, texture refs, UVs out of bounds, degenerate faces,
texel stretch, non-planar/flipped meshes, and style lint
(pure black/white, too-large palette) with --style.

The lint applies to ANY style (cute, horror, dark, realistic):
pure black/white fail in all of them — shadow has hue, light has hue.

`--detail` measures FIDELITY (the gap between "box blockout" and a reference):
missing thin piece, everything axis-aligned, no beveled shape.

Usage:
    python3 bbcheck.py model.bbmodel [--style] [--detail] [--type mob|prop|vehicle|diorama]
                                  [--tex texture.png]

Output: [E]/[W]/[I] lines and a summary. Exit code 1 if there is an error.
Module usage:
    from bbcheck import check
    r = check("m.bbmodel", style=True)
    assert not r["errors"]
"""

import base64
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbtex  # noqa: E402

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
KNOWN_FORMATS = {"free", "java_block", "bedrock", "bedrock_old", "modded_entity",
                 "optifine_entity", "optifine_jpm", "skin", "image", "generic"}
KNOWN_FACES = {"north", "east", "south", "west", "up", "down"}
PROP_TRI_BUDGET = 800
CHAR_TRI_BUDGET = 3000


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []

    def E(self, code, msg):
        self.errors.append((code, msg))

    def W(self, code, msg):
        self.warnings.append((code, msg))

    def I(self, code, msg):
        self.infos.append((code, msg))

    @property
    def ok(self):
        return not self.errors

    def print(self, verbose=True):
        for level, items in (("E", self.errors), ("W", self.warnings), ("I", self.infos)):
            for code, msg in items:
                print(f"[{level}] {code}: {msg}")
        c = f"{len(self.errors)} error(s), {len(self.warnings)} warning(s), {len(self.infos)} info(s)"
        print(c)
        return self.ok


def _num3(v):
    return isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


DETAIL_TYPES = {
    # returns (micro_fraction, thin_piece_fraction, alignment_alert)
    "mob": (0.20, 0.05, 0.85),
    "character": (0.20, 0.05, 0.85),
    "prop": (0.30, 0.10, 1.01),
    "vehicle": (0.15, 0.06, 0.90),
    "diorama": (0.25, 0.08, 0.95),
}


def _detail_lint(rep, elements, kind="default"):
    """Fidelity: thin detail present, silhouette with rotation, shapes with bevel.

    kind = mob|prop|vehicle|diorama calibrates thresholds; "default" uses the
    generic values (micro ≤25% of the largest dimension, no thin piece >8%).
    """
    micro, min_frac, align_max = DETAIL_TYPES.get(kind, (0.25, 0.08, 1.01))
    dims = []
    aligned = total = meshes = 0
    for el in elements:
        if el.get("type", "cube") == "mesh":
            meshes += 1
            continue
        frm, to = el.get("from"), el.get("to")
        if not (_num3(frm) and _num3(to)):
            continue
        d = [abs(to[i] - frm[i]) for i in range(3)]
        if min(d) <= 1e-6:
            continue
        dims.append((el.get("name", "?"), min(d), max(d)))
        total += 1
        rot = el.get("rotation") or [0, 0, 0]
        if all(abs(float(r)) < 1e-6 for r in rot):
            aligned += 1
    if not dims:
        return
    scale = max(d[2] for d in dims)
    min_edge = min(d[1] for d in dims)
    fine = [n for (n, mn, mx) in dims if mn <= micro * scale]
    if min_edge > min_frac * scale:
        rep.W("detail", f"[{kind}] no small piece: smallest edge {min_edge:.2f}u = "
                        f"{100 * min_edge / scale:.0f}% of the largest dimension ({scale:.1f}u); "
                        f"micro must be ≤{100 * micro:.0f}% — use bbkit.on_face/grid_of")
    else:
        rep.I("detail", f"[{kind}] {len(fine)} detail pieces (≤{100 * micro:.0f}%); "
                        f"smallest edge {min_edge:.2f}u at scale {scale:.1f}u")
    if total >= 5 and aligned / total >= align_max:
        rep.W("detail", f"[{kind}] {aligned}/{total} cubes axis-aligned — generic "
                        f"silhouette; tilt a key piece (5-15°) or use bbkit.bevel_box/taper_box")
    if meshes == 0 and total >= 5:
        rep.W("detail", f"[{kind}] no beveled/tapered/cylinder shape — 100% straight "
                        f"boxes read as blockout (bbkit.bevel_box fixes that)")


def check(path_or_dict, style=False, tex_override=None, detail=False, kind="default"):
    rep = Report()
    if isinstance(path_or_dict, dict):
        model = path_or_dict
        name = "<dict>"
    else:
        name = os.path.basename(str(path_or_dict))
        with open(path_or_dict, encoding="utf-8") as fh:
            try:
                model = json.load(fh)
            except json.JSONDecodeError as exc:
                rep.E("json", f"invalid JSON: {exc}")
                return {"errors": rep.errors, "warnings": rep.warnings, "infos": rep.infos, "report": rep}

    meta = model.get("meta") or {}
    fv = str(meta.get("format_version", "?"))
    fmt = meta.get("model_format", "free")
    if fv == "?":
        rep.W("meta", "no meta.format_version (Blockbench assumes old and may migrate wrong)")
    if fmt not in KNOWN_FORMATS:
        rep.W("meta", f"unknown model_format {fmt!r}")

    tex_w = tex_h = None
    res = model.get("resolution")
    if isinstance(res, dict):
        tex_w, tex_h = res.get("width"), res.get("height")
    elif model.get("textures"):
        rep.W("resolution", "no resolution{width,height} with textures present")

    # --- textures -----------------------------------------------------------
    textures = model.get("textures") or []
    tex_pngs = {}
    for i, t in enumerate(textures):
        if not isinstance(t, dict):
            rep.E("tex", f"textures[{i}] is not an object")
            continue
        if not isinstance(t.get("id"), str):
            rep.W("tex", f"textures[{i}].id should be a string, got {t.get('id')!r}")
        src = t.get("source") or ""
        if src.startswith("data:image/png;base64,"):
            try:
                png = base64.b64decode(src.split(",", 1)[1])
                dec = bbtex.decode_png(png)
                tex_pngs[i] = dec
                if tex_w and tex_h and (dec["width"] != tex_w or dec["height"] != tex_h):
                    rep.W("tex", f"textures[{i}] is {dec['width']}x{dec['height']} "
                                 f"but resolution is {tex_w}x{tex_h}")
            except Exception as exc:
                rep.E("tex", f"textures[{i}].source does not decode as PNG: {exc}")
        elif src:
            rep.W("tex", f"textures[{i}].source is an external path (not portable); embed as base64")
        else:
            rep.W("tex", f"textures[{i}] has no source")

    # --- elements ----------------------------------------------------------
    elements = model.get("elements") or model.get("cubes") or []
    by_uuid = {}
    for i, el in enumerate(elements):
        if not isinstance(el, dict):
            rep.E("el", f"elements[{i}] is not an object")
            continue
        u = el.get("uuid")
        label = el.get("name") or f"elements[{i}]"
        if not u:
            rep.E("uuid", f"{label}: no uuid")
        elif not UUID_RE.match(str(u)):
            rep.W("uuid", f"{label}: uuid outside the standard: {u}")
        elif u in by_uuid:
            rep.E("uuid", f"duplicate uuid in {label} and {by_uuid[u]}")
        by_uuid[u] = label

        etype = el.get("type", "cube")
        if etype == "cube":
            _check_cube(rep, el, label, tex_w, tex_h, len(textures), textures, fmt)
        elif etype == "mesh":
            _check_mesh(rep, el, label, tex_w, tex_h, len(textures))
        else:
            rep.I("el", f"{label}: type {etype!r} ignored by the validator")

    # --- groups / outliner --------------------------------------------------
    groups = model.get("groups") or []
    group_uuids = set()
    for i, g in enumerate(groups):
        u = g.get("uuid")
        if not u:
            rep.E("group", f"groups[{i}] ({g.get('name')!r}) has no uuid")
        elif not UUID_RE.match(str(u)):
            rep.W("uuid", f"group {g.get('name')!r}: uuid outside the standard")
        else:
            group_uuids.add(u)
        if "children" in g:
            rep.W("group", f"group {g.get('name')!r} has children in groups[] "
                           f"(format 5.0 separates the outliner; children go in the outliner)")

    outliner = model.get("outliner") or []
    referenced = set()

    def walk_outliner(node, depth=0):
        if depth > 16:
            rep.E("outliner", "depth > 16 (likely cycle)")
            return
        if isinstance(node, str):
            referenced.add(node)
            if node not in by_uuid and node not in group_uuids:
                rep.E("outliner", f"outliner references non-existent uuid: {node}")
        elif isinstance(node, dict):
            u = node.get("uuid")
            referenced.add(u)
            if u not in group_uuids:
                rep.E("outliner", f"group node with uuid {u} is not in groups[]")
            if "name" in node:
                rep.W("outliner", f"group node {u} repeats 'name' (redundant in 5.0)")
            for c in node.get("children") or []:
                walk_outliner(c, depth + 1)
        else:
            rep.E("outliner", f"invalid node: {node!r}")

    for node in outliner:
        walk_outliner(node)

    for u, label in by_uuid.items():
        if u not in referenced:
            rep.W("outliner", f"element {label} exists but is not in the outliner (invisible in BB)")

    # --- style --------------------------------------------------------------
    tri_count = _tri_count(elements)
    if tri_count > CHAR_TRI_BUDGET:
        rep.W("budget", f"{tri_count} triangles — above the character ceiling ({CHAR_TRI_BUDGET})")
    elif tri_count > PROP_TRI_BUDGET:
        rep.I("budget", f"{tri_count} triangles — ok for character, high for prop")

    if style:
        _style_lint(rep, elements, tex_pngs, tex_override, tex_w, tex_h, fv)

    if detail:
        _detail_lint(rep, elements, kind)

    _uv_overlap_check(rep, elements)
    _zfight_check(rep, elements)

    return {"errors": rep.errors, "warnings": rep.warnings, "infos": rep.infos, "report": rep}


def _check_cube(rep, el, label, tex_w, tex_h, n_tex, textures, fmt):
    for key in ("from", "to"):
        if not _num3(el.get(key)):
            rep.E("cube", f"{label}: field '{key}' must be numeric [x,y,z], got {el.get(key)!r}")
    if _num3(el.get("from")) and _num3(el.get("to")):
        frm, to = el["from"], el["to"]
        for ax in range(3):
            if frm[ax] == to[ax]:
                rep.E("cube", f"{label}: ZERO thickness on axis {'xyz'[ax]} — invisible/degenerate face")
            elif abs(to[ax] - frm[ax]) > 8:
                rep.I("cube", f"{label}: {abs(to[ax]-frm[ax]):g} units on axis {'xyz'[ax]} is quite large")
            if to[ax] < frm[ax]:
                rep.W("cube", f"{label}: negative size on axis {'xyz'[ax]} (from>to) — confusing, prefer inverting")
        if fmt == "java_block":
            for v in list(frm) + list(to):
                if v != int(v):
                    rep.E("cube", f"{label}: java_block requires integer coordinates ({v})")
                elif not (-16 <= v <= 32):
                    rep.W("cube", f"{label}: {v} outside the classic java_block range -16..32")
    if el.get("origin") is not None and not _num3(el.get("origin")):
        rep.E("cube", f"{label}: origin must be [x,y,z]")
    if el.get("rotation") is not None and not _num3(el.get("rotation")):
        rep.E("cube", f"{label}: rotation must be [x,y,z] in degrees")

    faces = el.get("faces")
    if not isinstance(faces, dict):
        rep.E("cube", f"{label}: no faces")
        return
    for missing in KNOWN_FACES - set(faces):
        rep.W("cube", f"{label}: face {missing} missing (Blockbench draws it as null)")
    for fkey, f in faces.items():
        where = f"{label}.{fkey}"
        if fkey not in KNOWN_FACES:
            rep.W("cube", f"{where}: unknown face name")
            continue
        if not isinstance(f, dict):
            rep.E("cube", f"{where}: not an object")
            continue
        uv = f.get("uv")
        if uv is not None:
            if not (isinstance(uv, list) and len(uv) == 4 and all(_num(x) for x in uv)):
                rep.E("cube", f"{where}: uv must be numeric [u1,v1,u2,v2], got {uv!r}")
            else:
                u1, v1, u2, v2 = uv
                if u1 == u2 or v1 == v2:
                    rep.E("cube", f"{where}: UV region with zero area {uv} (face draws no texture)")
                if tex_w and tex_h:
                    lo_u, hi_u = min(u1, u2), max(u1, u2)
                    lo_v, hi_v = min(v1, v2), max(v1, v2)
                    if lo_u < 0 or lo_v < 0 or hi_u > tex_w or hi_v > tex_h:
                        rep.E("cube", f"{where}: uv {uv} out of texture {tex_w}x{tex_h}")
                    else:
                        stretch = ((hi_u - lo_u) / max(1e-6, hi_v - lo_v))
                        _stretch_check(rep, el, fkey, where, stretch)
        tex = f.get("texture", None)
        if tex is None:
            pass
        elif not _num(tex) or int(tex) != tex:
            rep.E("cube", f"{where}: texture must be an integer index or null, got {tex!r}")
        elif not (0 <= int(tex) < max(n_tex, 1)):
            rep.E("cube", f"{where}: texture={tex} but there are {n_tex} texture(s)")
        rot = f.get("rotation", 0)
        if rot not in (0, 90, 180, 270):
            rep.E("cube", f"{where}: face rotation must be 0/90/180/270, got {rot!r}")


def _stretch_check(rep, el, fkey, where, ratio_uv):
    if not (_num3(el.get("from")) and _num3(el.get("to"))):
        return
    d = [abs(el["to"][i] - el["from"][i]) for i in range(3)]
    dims = {"north": (d[0], d[1]), "east": (d[2], d[1]), "south": (d[0], d[1]),
            "west": (d[2], d[1]), "up": (d[0], d[2]), "down": (d[0], d[2])}[fkey]
    if dims[1] < 1e-6:
        return
    ratio_face = dims[0] / dims[1]
    if ratio_uv > 0 and ratio_face > 0:
        r = ratio_uv / ratio_face
        if r > 1.5 or r < 1 / 1.5:
            rep.W("stretch", f"{where}: UV stretched ({r:.2f}x) — region proportion differs from the face")


def _check_mesh(rep, el, label, tex_w, tex_h, n_tex):
    verts = el.get("vertices")
    if not isinstance(verts, dict) or not verts:
        rep.E("mesh", f"{label}: no vertices")
        return
    vmap = {}
    for k, v in verts.items():
        if not _num3(v):
            rep.E("mesh", f"{label}: invalid vertex {k}: {v!r}")
        else:
            vmap[k] = v
    faces = el.get("faces")
    if not isinstance(faces, dict) or not faces:
        rep.E("mesh", f"{label}: no faces")
        return
    all_pts = list(vmap.values())
    centroid = [sum(p[i] for p in all_pts) / len(all_pts) for i in range(3)]
    for fk, f in faces.items():
        where = f"{label}.f{fk}"
        if not isinstance(f, dict):
            rep.E("mesh", f"{where}: not an object")
            continue
        vids = f.get("vertices")
        if not (isinstance(vids, list) and len(vids) >= 3):
            rep.E("mesh", f"{where}: vertices needs 3+ ids (CCW order seen from outside)")
            continue
        if len(set(map(str, vids))) != len(vids):
            rep.E("mesh", f"{where}: repeated vertex ids: {vids}")
        pts = []
        for vid in vids:
            if str(vid) not in vmap:
                rep.E("mesh", f"{where}: vertex {vid} does not exist")
            else:
                pts.append(vmap[str(vid)])
        if len(pts) < 3:
            continue
        uv = f.get("uv")
        if uv is not None:
            if not isinstance(uv, dict):
                rep.E("mesh", f"{where}: uv must be a dict vid->[u,v]")
            else:
                for vid, p in uv.items():
                    if str(vid) not in [str(x) for x in vids]:
                        rep.W("mesh", f"{where}: uv for vertex {vid} outside the face")
                    if not (isinstance(p, list) and len(p) == 2 and all(_num(x) for x in p)):
                        rep.E("mesh", f"{where}: invalid uv for {vid}: {p!r}")
                    elif tex_w and tex_h and (p[0] < 0 or p[1] < 0 or p[0] > tex_w or p[1] > tex_h):
                        rep.E("mesh", f"{where}: uv for {vid} out of texture: {p}")
        # planarity
        n = _normal(pts)
        if n is None:
            rep.E("mesh", f"{where}: degenerate face (collinear points)")
        else:
            dmax = max(abs(_dot(_sub(p, pts[0]), n)) for p in pts[1:])
            if dmax > 0.02:
                rep.W("mesh", f"{where}: non-planar face (deviation {dmax:.3f}u) — unpredictable triangulation")
            c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
            if _dot(n, _sub(c, centroid)) < -1e-6:
                rep.W("mesh", f"{where}: winding flipped INWARD (CCW order must point outward)")
        tex = f.get("texture")
        if tex is not None and (_num(tex) and not (0 <= int(tex) < max(n_tex, 1))):
            rep.E("mesh", f"{where}: texture={tex} invalid")


def _tri_count(elements):
    n = 0
    for el in elements:
        if el.get("type", "cube") == "cube":
            for f in (el.get("faces") or {}).values():
                if isinstance(f, dict) and f.get("texture") is not None:
                    n += 2
        else:
            for f in (el.get("faces") or {}).values():
                if isinstance(f, dict) and isinstance(f.get("vertices"), list):
                    n += max(0, len(f["vertices"]) - 2)
    return n


def _uv_overlap_check(rep, elements):
    rects = []
    for el in elements:
        etype = el.get("type", "cube")
        name = el.get("name", "?")
        if etype == "cube":
            for fkey, f in (el.get("faces") or {}).items():
                if not isinstance(f, dict) or f.get("texture") is None:
                    continue
                uv = f.get("uv")
                if not (isinstance(uv, list) and len(uv) == 4 and all(isinstance(x, (int, float)) for x in uv)):
                    continue
                u1, v1, u2, v2 = uv
                rects.append((f"{name}.{fkey}", min(u1, u2), min(v1, v2), max(u1, u2), max(v1, v2)))
        else:
            for fk, f in (el.get("faces") or {}).items():
                uv = f.get("uv")
                if not isinstance(uv, dict) or not uv:
                    continue
                us = [p[0] for p in uv.values() if isinstance(p, (list, tuple)) and len(p) == 2]
                vs = [p[1] for p in uv.values() if isinstance(p, (list, tuple)) and len(p) == 2]
                if not us:
                    continue
                rects.append((f"{name}.f{fk}", min(us), min(vs), max(us), max(vs)))
    overlaps = 0
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            if (a[1], a[2], a[3], a[4]) == (b[1], b[2], b[3], b[4]):
                continue
            if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
                overlaps += 1
                if overlaps <= 12:
                    rep.I("uv_overlap", f"overlapping UVs (partial): {a[0]} and {b[0]}")
    if overlaps > 12:
        rep.I("uv_overlap", f"... and {overlaps - 12} more partial overlaps")


def _zfight_check(rep, elements):
    # collect cube faces as (axis, plane, u_lo, u_hi, v_lo, v_hi, name)
    faces = []
    for el in elements:
        if el.get("type", "cube") != "cube":
            continue
        frm = el.get("from"); to = el.get("to")
        if not (_num3(frm) and _num3(to)):
            continue
        name = el.get("name", "?")
        for plane, (a1, a2) in ((frm[0], (1, 2)), (to[0], (1, 2))):
            faces.append((0, plane, frm[a1], to[a1], frm[a2], to[a2], name))
        for plane, (a1, a2) in ((frm[2], (0, 1)), (to[2], (0, 1))):
            faces.append((2, plane, frm[a1], to[a1], frm[a2], to[a2], name))
        for plane, (a1, a2) in ((frm[1], (0, 2)), (to[1], (0, 2))):
            faces.append((1, plane, frm[a1], to[a1], frm[a2], to[a2], name))
    hits = 0
    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            a, b = faces[i], faces[j]
            if a[0] != b[0]:
                continue
            if abs(a[1] - b[1]) > 1e-3:
                continue
            if a[6] == b[6]:
                continue
            # 2D overlap
            if a[2] < b[3] and b[2] < a[3] and a[4] < b[5] and b[4] < a[5]:
                hits += 1
                if hits <= 8:
                    rep.I("zfight", f"overlapping coplanar faces: {a[6]} and {b[6]} (axis {a[0]}, plane {a[1]:g})")
    if hits > 8:
        rep.I("zfight", f"... and {hits-8} more cases")


def _style_lint(rep, elements, tex_pngs, tex_override, tex_w, tex_h, fv):
    png = None
    if tex_override:
        with open(tex_override, "rb") as fh:
            png = bbtex.decode_png(fh.read())
    elif 0 in tex_pngs:
        png = tex_pngs[0]
    if png is None:
        rep.W("style", "no embedded texture for style lint")
        return
    w, h, rgba = png["width"], png["height"], png["rgba"]

    n_black = n_white = 0
    first_black = first_white = None
    colors = set()
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i + 4]
        if a == 0:
            continue
        colors.add((r, g, b))
        if (r, g, b) == (0, 0, 0) and a == 255:
            n_black += 1
            first_black = first_black or (i // 4 % w, i // 4 // w)
        elif (r, g, b) == (255, 255, 255) and a == 255:
            n_white += 1
            first_white = first_white or (i // 4 % w, i // 4 // w)
    if n_black:
        rep.E("style", f"{n_black} px of PURE BLACK (#000) — use a dark colored tone "
                       f"(first at {first_black})")
    if n_white:
        rep.E("style", f"{n_white} px of PURE WHITE (#fff) — use cream/off-white "
                       f"(first at {first_white})")
    if (255, 0, 255) in colors:
        rep.W("style", "pure magenta (#ff00ff) present — it's the transparency key color; use real alpha")
    if len(colors) > 20:
        rep.W("style", f"palette with {len(colors)} colors — target is 8-20 in a low-poly asset")
    elif len(colors) > 0:
        rep.I("style", f"palette with {len(colors)} colors")

    # texel density: px per unit on cube faces
    dens = []
    for el in elements:
        if el.get("type", "cube") != "cube" or not (_num3(el.get("from")) and _num3(el.get("to"))):
            continue
        d = [abs(el["to"][i] - el["from"][i]) for i in range(3)]
        dims = {"north": (d[0], d[1]), "east": (d[2], d[1]), "south": (d[0], d[1]),
                "west": (d[2], d[1]), "up": (d[0], d[2]), "down": (d[0], d[2])}
        for fkey, f in (el.get("faces") or {}).items():
            if not isinstance(f, dict) or f.get("texture") is None or not f.get("uv"):
                continue
            uv = f["uv"]
            for axis, dim in enumerate(dims.get(fkey, (0, 0))):
                size_px = abs(uv[2] - uv[0]) if axis == 0 else abs(uv[3] - uv[1])
                if dim > 1e-6:
                    dens.append(size_px / dim)
    if dens:
        dmin, dmax = min(dens), max(dens)
        if dmax / max(dmin, 1e-6) > 1.6:
            rep.W("style", f"inconsistent texel density: {dmin:.1f} to {dmax:.1f} px/unit "
                           f"(target: constant across the whole model)")
        else:
            rep.I("style", f"consistent texel density (~{sum(dens)/len(dens):.1f} px/unit)")


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normal(pts):
    n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
    ln = (_dot(n, n)) ** 0.5
    if ln < 1e-9:
        return None
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def _apply_fix(path, argv):
    """Automatically fixes pure black/white pixels in the embedded texture."""
    import base64, json as _j, os
    with open(path, encoding="utf-8") as fh:
        model = _j.load(fh)
    changed = 0
    for t in (model.get("textures") or []):
        src = t.get("source") or ""
        if not src.startswith("data:image/png;base64,"):
            continue
        import sys as _s
        _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bbtex
        png = base64.b64decode(src.split(",", 1)[1])
        dec = bbtex.decode_png(png)
        rgba = bytearray(dec["rgba"])
        for i in range(0, len(rgba), 4):
            r, g, b, a = rgba[i:i + 4]
            if a == 0:
                continue
            if (r, g, b) == (0, 0, 0):
                rgba[i:i + 3] = bytes((18, 18, 28))
                changed += 1
            elif (r, g, b) == (255, 255, 255):
                rgba[i:i + 3] = bytes((240, 240, 235))
                changed += 1
        new_png = bbtex.encode_png(dec["width"], dec["height"], rgba)
        t["source"] = "data:image/png;base64," + base64.b64encode(new_png).decode("ascii")
    out = path
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    else:
        root, ext = os.path.splitext(path)
        out = root + ".fixed" + (ext or ".bbmodel")
    with open(out, "w", encoding="utf-8") as fh:
        _j.dump(model, fh, separators=(",", ":"))
    print(f"fix applied: {changed} px corrected -> {out}", file=__import__("sys").stderr)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path = argv[0]
    style = "--style" in argv
    detail = "--detail" in argv
    kind = "default"
    if "--type" in argv:
        kind = argv[argv.index("--type") + 1]
        detail = True
    tex = None
    if "--tex" in argv:
        tex = argv[argv.index("--tex") + 1]
    json_out = "--json" in argv
    fix = "--fix" in argv
    if fix:
        _apply_fix(path, argv)
    r = check(path, style=style, tex_override=tex, detail=detail, kind=kind)
    ok = r["report"].print() if not json_out else (not r["errors"])
    if json_out:
        import json as _j
        print(_j.dumps({"errors": r["errors"], "warnings": r["warnings"],
                        "infos": r["infos"], "ok": ok}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
