#!/usr/bin/env python3
"""
bbmodel.py — library to build Blockbench models (.bbmodel 5.0) in pure Python.

Conventions (all verified against the Blockbench source code):
- Y-up coordinates; 16 units = 1 Minecraft block. Author with feet at y=0.
- UV in PIXELS, origin at top-left corner, v grows DOWNWARD.
- face.uv = [u1, v1, u2, v2]; the k-th vertex of the face (FACE_VERTICES order)
  receives the k-th corner of the UV region in the order [TL, TR, BR, BL].
- face.texture is the INTEGER index of the texture (null = disabled face).
- rotation in degrees, euler order 'ZYX' (R = Rz @ Ry @ Rx), extrinsic.
- Output in meta.format_version "5.0": flattened groups + outliner of references
  (group node = {uuid, isOpen, children}; element = uuid string).
- Inflate expands the cube: from = from - inflate, to = to + inflate.

Typical usage:
    from bbmodel import Model
    m = Model("mushroom", tex_w=64, tex_h=64, density=2)
    g = m.group("body")
    cap = m.cube("cap", [4, 8, 4], [12, 12, 12], group=g, origin=[8, 8, 8])
    m.cube("cap_r", [4, 8, 4], [12, 12, 12], group=g).mirror(0, 8)
    m.attach_texture_bytes(png_bytes)
    m.save("mushroom.bbmodel")
    print(m.uv_regions)   # {"cap": {"north": [u1,v1,u2,v2], ...}, ...}
"""

import base64
import json
import math
import os
import sys
import uuid as _uuid

FORMAT_VERSION = "5.0"
DIRECTIONS = ("north", "east", "south", "west", "up", "down")

# Per-face vertex order — CubeFace.getVertexIndices() from Blockbench.
FACE_VERTICES = {
    "north": (1, 4, 6, 3),
    "east": (0, 1, 3, 2),
    "south": (5, 0, 2, 7),
    "west": (4, 5, 7, 6),
    "up": (4, 1, 0, 5),
    "down": (7, 2, 3, 6),
}


def guid():
    return str(_uuid.uuid4())


# Fixed namespace for deterministic uuids: the same names map to the same uuids
# on any machine and on every rebuild. This makes the build byte-identical and
# keeps animation keys — which reference the bone uuid — valid across rebuilds.
DET_NAMESPACE = _uuid.UUID("1b0c8f2e-3a5d-4c7b-9e11-6d2f8a4b7c30")


def det_uuid(kind, name):
    """Stable uuid derived from node type+name (uuid5)."""
    return str(_uuid.uuid5(DET_NAMESPACE, f"{kind}:{name}"))


def _num(x):
    """Clean number: int when integral, otherwise rounded to 4 decimals."""
    x = float(x)
    if x == int(x):
        return int(x)
    return round(x, 4)


def _v3(v, label="vector"):
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise ValueError(f"{label}: expected [x, y, z], got {v!r}")
    return [_num(v[0]), _num(v[1]), _num(v[2])]


def face_uv_corners(uv, rotation=0):
    """UV corners in vertex order [TL, TR, BR, BL], applying face rotation.

    Same logic as the Blockbench OBJ exporter: each 90° rotates the list
    moving the last corner to the front.
    """
    u1, v1, u2, v2 = float(uv[0]), float(uv[1]), float(uv[2]), float(uv[3])
    corners = [(u1, v1), (u2, v1), (u2, v2), (u1, v2)]
    for _ in range(int(rotation // 90) % 4):
        corners.insert(0, corners.pop())
    return corners


def cube_vertex_table(frm, to):
    """8 local vertices in Blockbench's canonical order (getGlobalVertexPositions)."""
    return [
        (to[0], to[1], to[2]),
        (to[0], to[1], frm[2]),
        (to[0], frm[1], to[2]),
        (to[0], frm[1], frm[2]),
        (frm[0], to[1], frm[2]),
        (frm[0], to[1], to[2]),
        (frm[0], frm[1], frm[2]),
        (frm[0], frm[1], to[2]),
    ]


def euler_matrix_zyx(rx_deg, ry_deg, rz_deg):
    """3x3 matrix R = Rz @ Ry @ Rx (Blockbench euler order 'ZYX')."""
    rx, ry, rz = map(math.radians, (rx_deg, ry_deg, rz_deg))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rx_m = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry_m = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz_m = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))
    return _m3_mul(rz_m, _m3_mul(ry_m, rx_m))


def _m3_mul(a, b):
    return tuple(
        tuple(a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] for j in range(3))
        for i in range(3)
    )


def _m3_apply(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def _rotate_around(rotation_deg, origin, v):
    """v rotated around origin by the 'ZYX' euler rotation_deg."""
    rx, ry, rz = rotation_deg
    if not (rx or ry or rz):
        return tuple(v)
    m = euler_matrix_zyx(rx, ry, rz)
    ox, oy, oz = origin
    rel = (v[0] - ox, v[1] - oy, v[2] - oz)
    r = _m3_apply(m, rel)
    return (r[0] + ox, r[1] + oy, r[2] + oz)


# ---------------------------------------------------------------------------
# UV allocator (shelf packing with gap between regions)
# ---------------------------------------------------------------------------

class UVAllocator:
    def __init__(self, width, height, gap=1, margin=1):
        self.w = int(width)
        self.h = int(height)
        self.gap = int(gap)
        self.margin = int(margin)
        self.skyline = [(0, self.margin, self.w)]  # (x, y, width)
        self.rects = {}

    def alloc(self, key, rw, rh, force_rect=None):
        if force_rect is not None:
            rect = [int(force_rect[0]), int(force_rect[1]), int(force_rect[2]), int(force_rect[3])]
            self.rects[key] = rect
            return list(rect)
        rw = max(1, int(round(rw)))
        rh = max(1, int(round(rh)))
        if rw + 2 * self.margin > self.w or rh + 2 * self.margin > self.h:
            raise ValueError(
                f"region '{key}' ({rw}x{rh}px) does not fit in texture {self.w}x{self.h} "
                f"(margin {self.margin}px). Increase tex_w/tex_h or reduce density."
            )
        ew = rw + self.gap
        eh = rh + self.gap

        candidates = {self.margin}
        for (sx, sy, sw) in self.skyline:
            candidates.add(sx)
        best = None
        for cx in sorted(candidates):
            if cx + ew + self.margin > self.w:
                continue
            maxy = 0
            for (sx, sy, sw) in self.skyline:
                ol = max(sx, cx)
                or_ = min(sx + sw, cx + ew)
                if ol < or_:
                    maxy = max(maxy, sy)
            if maxy + eh + self.margin > self.h:
                continue
            if best is None or maxy < best[0]:
                best = (maxy, cx)
        if best is None:
            raise ValueError(
                f"texture {self.w}x{self.h} full while allocating '{key}' ({rw}x{rh}px). "
                f"Increase tex_w/tex_h, reduce density, or split into several models."
            )
        maxy, cx = best
        y = maxy
        # update skyline
        new_sky = []
        for (sx, sy, sw) in self.skyline:
            if sx + sw <= cx or sx >= cx + ew:
                new_sky.append((sx, sy, sw))
            else:
                if sx < cx:
                    new_sky.append((sx, sy, cx - sx))
                if sx + sw > cx + ew:
                    new_sky.append((cx + ew, sy, sx + sw - (cx + ew)))
        new_sky.append((cx, y + eh, ew))
        new_sky.sort()
        merged = []
        for seg in new_sky:
            if merged and merged[-1][0] + merged[-1][2] == seg[0] and merged[-1][1] == seg[1]:
                merged[-1] = (merged[-1][0], merged[-1][1], merged[-1][2] + seg[2])
            else:
                merged.append(seg)
        self.skyline = merged

        rect = [cx, y, cx + rw, y + rh]
        self.rects[key] = rect
        return list(rect)

    def occupied_rects(self):
        return list(self.rects.values())


# ---------------------------------------------------------------------------
# Model nodes
# ---------------------------------------------------------------------------

class FaceState:
    __slots__ = ("uv", "texture", "rotation", "tint")

    def __init__(self, uv, texture=0, rotation=0, tint=None):
        self.uv = [float(uv[0]), float(uv[1]), float(uv[2]), float(uv[3])]
        self.texture = texture
        self.rotation = int(rotation)
        self.tint = tint

    def clone(self):
        return FaceState(self.uv, self.texture, self.rotation, self.tint)

    @property
    def enabled(self):
        return self.texture is not None


class _Node:
    def __init__(self, name, node_type, det_kind=None):
        self.name = name
        self.uuid = det_uuid(det_kind or node_type, name)
        self.node_type = node_type
        self.parent = None

    def __repr__(self):
        return f"<{self.node_type} {self.name!r}>"


class Group(_Node):
    def __init__(self, name, origin=(0, 0, 0), rotation=(0, 0, 0), color=None):
        super().__init__(name, "group")
        self.origin = _v3(origin, f"group({name}) origin")
        self.rotation = _v3(rotation, f"group({name}) rotation")
        self.color = color
        self.children = []

    def _walk(self, out):
        for c in self.children:
            out.append(c)
            if isinstance(c, Group):
                c._walk(out)


class Cube(_Node):
    def __init__(self, name, frm, to, origin, rotation, inflate, mirror_uv, color):
        super().__init__(name, "cube")
        self.frm = _v3(frm, f"cube({name}) from")
        self.to = _v3(to, f"cube({name}) to")
        self.origin = _v3(origin, f"cube({name}) origin")
        self.rotation = _v3(rotation or (0, 0, 0), f"cube({name}) rotation")
        self.inflate = _num(inflate)
        self.mirror_uv = bool(mirror_uv)
        self.color = color
        self.faces = {}  # direction -> FaceState

    @property
    def size(self):
        return [abs(self.to[i] - self.frm[i]) for i in range(3)]

    def center(self):
        return [(self.frm[i] + self.to[i]) / 2 for i in range(3)]

    def mirror(self, axis, center):
        """Mirrors the cube on the plane axis=center, replicating Blockbench's flip().

        axis: 0=X, 1=Y, 2=Z. center is the plane coordinate (e.g., 8 = grid center).
        Face data is swapped between pairs and UVs are mirrored.
        """
        if axis not in (0, 1, 2):
            raise ValueError("axis must be 0 (X), 1 (Y) or 2 (Z)")
        c = float(center)
        r = self.rotation
        r[(axis + 1) % 3] = _num(r[(axis + 1) % 3] * -1)
        r[(axis + 2) % 3] = _num(r[(axis + 2) % 3] * -1)
        f_old, t_old = self.frm[axis], self.to[axis]
        self.frm[axis] = _num(2 * c - t_old)
        self.to[axis] = _num(2 * c - f_old)
        self.origin[axis] = _num(2 * c - self.origin[axis])

        swap = ({0: ("west", "east"), 1: ("up", "down"), 2: ("south", "north")})[axis]
        a, b = self.faces[swap[0]], self.faces[swap[1]]
        self.faces[swap[0]], self.faces[swap[1]] = b.clone(), a.clone()

        def flip_u(fs):
            fs.uv = [fs.uv[2], fs.uv[1], fs.uv[0], fs.uv[3]]

        def flip_v(fs):
            fs.uv = [fs.uv[0], fs.uv[3], fs.uv[2], fs.uv[1]]

        def fx(fs):  # mirror of the face on X
            if fs.rotation in (90, 270):
                flip_v(fs)
            else:
                flip_u(fs)

        def fy(fs):  # mirror of the face on Y
            if fs.rotation in (90, 270):
                flip_u(fs)
            else:
                flip_v(fs)

        if axis == 1:
            for d in DIRECTIONS:
                fy(self.faces[d])
        else:
            for d in ("north", "south", "east", "west"):
                fx(self.faces[d])
            if axis == 0:
                fx(self.faces["up"])
                fx(self.faces["down"])
            else:
                fy(self.faces["up"])
                fy(self.faces["down"])
        return self

    def set_uv(self, face, uv):
        self.faces[face].uv = [float(uv[0]), float(uv[1]), float(uv[2]), float(uv[3])]
        return self


class Mesh(_Node):
    def __init__(self, name, vertices, faces, origin, rotation, color=None):
        super().__init__(name, "mesh")
        self.vertices = [tuple(float(c) for c in v) for v in vertices]  # authored (absolute)
        self.faces = []  # list of dicts {"vertices": (i,...), "uv": [(u,v), ...] | None}
        for f in faces:
            if isinstance(f, dict):
                vis = tuple(int(i) for i in f["vertices"])
                uvs = f.get("uv")
            else:
                vis = tuple(int(i) for i in f)
                uvs = None
            if len(vis) < 3:
                raise ValueError(f"mesh({name}): face with fewer than 3 vertices: {vis}")
            for i in vis:
                if not (0 <= i < len(self.vertices)):
                    raise ValueError(f"mesh({name}): face references non-existent vertex {i}")
            self.faces.append({"vertices": vis, "uv": uvs})
        self.origin = _v3(origin, f"mesh({name}) origin")
        self.rotation = _v3(rotation or (0, 0, 0), f"mesh({name}) rotation")
        self.color = color

    def mirror(self, axis, center):
        if axis not in (0, 1, 2):
            raise ValueError("axis must be 0 (X), 1 (Y) or 2 (Z)")
        c = float(center)
        r = self.rotation
        r[(axis + 1) % 3] = _num(r[(axis + 1) % 3] * -1)
        r[(axis + 2) % 3] = _num(r[(axis + 2) % 3] * -1)
        self.vertices = [
            tuple((2 * c - v[axis]) if i == axis else v[i] for i in range(3))
            for v in self.vertices
        ]
        # mirroring inverts orientation: reverse the vertex order of each face
        # (and the matching UVs) to keep the normal pointing outward.
        new_faces = []
        for f in self.faces:
            vis = tuple(reversed(f["vertices"]))
            uvs = None
            if f["uv"]:
                uvs = list(reversed(f["uv"]))
            new_faces.append({"vertices": vis, "uv": uvs})
        self.faces = new_faces
        self.origin[axis] = _num(2 * c - self.origin[axis])
        return self


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class Model:
    def __init__(self, name="model", tex_w=64, tex_h=64, density=2, gap=1, margin=1):
        if density <= 0:
            raise ValueError("density must be > 0 (pixels per unit)")
        self.name = name
        self.tex_w = int(tex_w)
        self.tex_h = int(tex_h)
        self.density = float(density)
        self.margin = int(margin)
        self.alloc = UVAllocator(tex_w, tex_h, gap=gap, margin=margin)
        self.groups = []
        self.elements = []
        self.root_nodes = []
        self.texture_png = None
        self.texture_name = "texture.png"
        self.texture_uuid = det_uuid("texture", name)
        self.textures = []  # list of (png_bytes, name, uuid) - multi-texture support
        self.animations = []
        # uuid -> group names, as they came from the file (used by preserve_animations)
        self.loaded_group_names = {}

    # -- construction -------------------------------------------------------
    def _resolve_group(self, group):
        if group is None:
            return None
        if isinstance(group, Group):
            return group
        if isinstance(group, str):
            for g in self.groups:
                if g.name == group:
                    return g
            raise ValueError(f"group {group!r} does not exist (create it with m.group first)")
        raise TypeError("group must be a Group, group name or None")

    def _attach(self, node, group):
        g = self._resolve_group(group)
        if g is None:
            self.root_nodes.append(node)
        else:
            g.children.append(node)
            node.parent = g
        if node.node_type == "group":
            self.groups.append(node)
        else:
            self.elements.append(node)

    def locator(self, name, origin=(0, 0, 0), parent=None, rotation=(0, 0, 0)):
        """Creates a locator (empty group used as an attach/effect point)."""
        g = self.group(name, origin=origin, rotation=rotation, parent=parent)
        g._locator = True
        return g

    def group(self, name, origin=(0, 0, 0), rotation=(0, 0, 0), color=None, parent=None):
        g = Group(name, origin=origin, rotation=rotation, color=color)
        self._attach(g, parent)
        return g
        g = Group(name, origin=origin, rotation=rotation, color=color)
        self._attach(g, parent)
        return g

    def _px(self, units):
        return max(1, int(round(units * self.density)))

    def cube(self, name, frm, to, group=None, origin=None, rotation=None,
             inflate=0.0, mirror_uv=False, faces=None, uv=None, color=None):
        """Creates a cube with automatic UV (per face) or explicit UV.

        faces: None = all 6; list to enable a subset (e.g., ["north","up"]).
        uv: None = auto-allocate per face; [u1,v1,u2,v2] = same region for all;
            dict {"north": [u1,v1,u2,v2], ...} = region per face.
        origin: pivot; default = cube center.
        """
        frm = _v3(frm, f"cube({name}) from")
        to = _v3(to, f"cube({name}) to")
        if name in {c.name for c in self.elements}:
            raise ValueError(f"an element named {name!r} already exists (names must be unique)")
        if origin is None:
            origin = [(frm[i] + to[i]) / 2 for i in range(3)]
        cube = Cube(name, frm, to, origin, rotation, inflate, mirror_uv, color)
        enabled = set(DIRECTIONS if faces is None else faces)
        for d in enabled:
            if d not in DIRECTIONS:
                raise ValueError(f"invalid face {d!r}; use {DIRECTIONS}")

        dims = [abs(to[i] - frm[i]) for i in range(3)]
        face_units = {
            "north": (dims[0], dims[1]),
            "east": (dims[2], dims[1]),
            "south": (dims[0], dims[1]),
            "west": (dims[2], dims[1]),
            "up": (dims[0], dims[2]),
            "down": (dims[0], dims[2]),
        }
        for d in DIRECTIONS:
            if d not in enabled:
                cube.faces[d] = FaceState([0, 0, 0, 0], texture=None)
                continue
            rect = None
            if uv is None:
                if self.alloc is None:
                    raise ValueError(
                        f"cube({name!r}): model loaded from file has no UV allocator. "
                        "Pass uv=[u1,v1,u2,v2] (or a dict per face) explicitly, or call "
                        "reset_alloc() first (careful: may overlap existing UVs)."
                    )
                w_px = self._px(face_units[d][0])
                h_px = self._px(face_units[d][1])
                rect = self.alloc.alloc(f"{name}:{d}", w_px, h_px)
            elif isinstance(uv, dict):
                rect = uv[d]
            else:
                rect = uv
            cube.faces[d] = FaceState(rect, texture=0)
        self._attach(cube, group)
        return cube

    def mesh(self, name, vertices, faces, group=None, origin=None, rotation=None,
             uv="planar", color=None):
        """Creates a mesh (only format free). faces = list of lists of CCW indices (front facing out).

        uv: "planar" (auto-project), None (no UV -> solid texture from the corner), or a list
        of [(u,v), ...] per face, aligned with each face's vertices.
        """
        verts = [tuple(float(c) for c in v) for v in vertices]
        if origin is None:
            origin = [
                (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2,
                (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2,
                (min(v[2] for v in verts) + max(v[2] for v in verts)) / 2,
            ]
        m = Mesh(name, verts, faces, origin, rotation, color=color)
        if uv == "planar":
            for fi, f in enumerate(m.faces):
                rect = self._planar_face_rect(name, fi, f["vertices"], verts)
                f["uv"] = rect
        elif isinstance(uv, list):
            for f, uvs in zip(m.faces, uv):
                f["uv"] = uvs
        elif uv is not None:
            raise ValueError("uv must be 'planar', None or a list of UVs per face")
        self._attach(m, group)
        return m

    def _planar_face_rect(self, name, fi, vidx, verts):
        """Auto planar UV: project the face onto a plane and map the bbox to the allocated region."""
        p = [verts[i] for i in vidx]
        n = _face_normal(p)
        up = (0.0, 1.0, 0.0)
        dot = abs(n[0] * up[0] + n[1] * up[1] + n[2] * up[2])
        if dot > 0.999:
            t = (1.0, 0.0, 0.0)
        else:
            t = _cross(up, n)
            t = _norm(t)
        b = _cross(n, t)  # "top of the screen"
        proj = [(_dot(v, t), -_dot(v, b)) for v in p]
        u0 = min(c[0] for c in proj)
        u1 = max(c[0] for c in proj)
        v0 = min(c[1] for c in proj)
        v1 = max(c[1] for c in proj)
        w_px = self._px(max(u1 - u0, 0.01))
        h_px = self._px(max(v1 - v0, 0.01))
        rect = self.alloc.alloc(f"{name}:f{fi}", w_px, h_px)
        uvs = []
        for (pu, pv) in proj:
            fu = (pu - u0) / (u1 - u0) if u1 > u0 else 0.5
            fv = (pv - v0) / (v1 - v0) if v1 > v0 else 0.5
            uvs.append((rect[0] + fu * (rect[2] - rect[0]), rect[1] + fv * (rect[3] - rect[1])))
        return uvs

    # -- texture ------------------------------------------------------------
    def attach_texture_bytes(self, png_bytes, name="texture.png"):
        if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("attach_texture: the bytes are not a valid PNG")
        # skip exact duplicates
        for (p, n, u) in self.textures:
            if p == bytes(png_bytes) and n == name:
                self._sync_primary()
                return self.textures.index((p, n, u))
        uuid = det_uuid("texture", f"{name}:{len(self.textures)}")
        self.textures.append((bytes(png_bytes), name, uuid))
        self._sync_primary()
        return len(self.textures) - 1

    def _sync_primary(self):
        if self.textures:
            self.texture_png = self.textures[0][0]
            self.texture_name = self.textures[0][1]
            self.texture_uuid = self.textures[0][2]
        else:
            self.texture_png = None

    def attach_texture(self, path_or_bytes, name=None):
        if isinstance(path_or_bytes, (str, os.PathLike)):
            with open(path_or_bytes, "rb") as fh:
                data = fh.read()
            if name is None:
                name = os.path.basename(str(path_or_bytes))
        else:
            data = bytes(path_or_bytes)
            name = name or "texture.png"
        return self.attach_texture_bytes(data, name)

    # -- loading from file ---------------------------------------------------
    @classmethod
    def load(cls, path):
        """Loads an existing .bbmodel for editing (format 5.0 or 4.x).

        Note: the UV allocator is not rebuilt — new cubes in a loaded model
        require explicit uv=[...] or reset_alloc().
        """
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    @classmethod
    def from_dict(cls, d):
        meta = d.get("meta") or {}
        res = d.get("resolution") or {}
        m = cls(name=d.get("name") or "model",
                tex_w=res.get("width") or 64, tex_h=res.get("height") or 64)
        textures = d.get("textures") or []
        for t in textures:
            src = (t or {}).get("source") or ""
            if src.startswith("data:image/png;base64,"):
                m.textures.append((base64.b64decode(src.split(",", 1)[1]),
                                 t.get("name") or "texture.png",
                                 t.get("uuid") or det_uuid("texture", t.get("name") or "texture.png")))
        if m.textures:
            m._sync_primary()
        if sum(1 for t in textures if str((t or {}).get("source", "")).startswith("data:")) > 1:
            print("warning: multiple embedded textures; experimental support (UVs on the primary texture)",
                  file=sys.stderr)

        node_by_uuid = {}
        for el in d.get("elements") or d.get("cubes") or []:
            if not isinstance(el, dict):
                continue
            etype = el.get("type", "cube")
            name = el.get("name") or etype
            origin = el.get("origin") or [0, 0, 0]
            rotation = el.get("rotation") or [0, 0, 0]
            color = el.get("color")
            if etype == "cube":
                node = Cube(name, el.get("from") or [0, 0, 0], el.get("to") or [8, 8, 8],
                            origin, rotation, el.get("inflate", 0) or 0,
                            el.get("mirror_uv", False), color)
                for dface in DIRECTIONS:
                    f = (el.get("faces") or {}).get(dface)
                    if not isinstance(f, dict) or f.get("texture") is None:
                        node.faces[dface] = FaceState([0, 0, 0, 0], texture=None)
                    else:
                        node.faces[dface] = FaceState(
                            f.get("uv") or [0, 0, 0, 0], texture=int(f["texture"]),
                            rotation=f.get("rotation", 0), tint=f.get("tint"))
                m.elements.append(node)
            elif etype == "mesh":
                vraw = el.get("vertices") or {}
                keys = sorted(vraw, key=lambda k: int(k))
                idx_of = {k: i for i, k in enumerate(keys)}
                verts = [[vraw[k][0] + origin[0], vraw[k][1] + origin[1], vraw[k][2] + origin[2]]
                         for k in keys]
                faces = []
                for fk in sorted(el.get("faces") or {}, key=lambda x: int(x)):
                    f = el["faces"][fk] or {}
                    vis = []
                    for v in f.get("vertices") or []:
                        if str(v) not in idx_of:
                            raise ValueError(f"mesh {name!r}: face f{fk} references non-existent vertex {v}")
                        vis.append(idx_of[str(v)])
                    uvraw = f.get("uv")
                    uv = None
                    if uvraw:
                        uv = []
                        for v in f.get("vertices") or []:
                            p = uvraw.get(str(v))
                            uv.append((float(p[0]), float(p[1])) if p else (0.0, 0.0))
                    faces.append({"vertices": tuple(vis), "uv": uv})
                node = Mesh(name, verts, faces, origin, rotation, color=color)
                m.elements.append(node)
            else:
                continue
            if el.get("uuid"):
                node.uuid = el["uuid"]
            node_by_uuid[node.uuid] = node

        groups_by_uuid = {}
        for g in d.get("groups") or []:
            if not isinstance(g, dict):
                continue
            node = Group(g.get("name") or "group", g.get("origin") or [0, 0, 0],
                         g.get("rotation") or [0, 0, 0], g.get("color"))
            if g.get("uuid"):
                node.uuid = g["uuid"]
            m.groups.append(node)
            groups_by_uuid[node.uuid] = node
            node_by_uuid[node.uuid] = node

        def attach(node, parent):
            node.parent = parent
            if parent is None:
                m.root_nodes.append(node)
            else:
                parent.children.append(node)

        def walk(node, parent=None):
            if isinstance(node, str):
                n = node_by_uuid.get(node)
                if n is not None:
                    attach(n, parent)
            elif isinstance(node, dict):
                g = groups_by_uuid.get(node.get("uuid"))
                if g is None:
                    g = Group(node.get("name") or "group", node.get("origin") or [0, 0, 0],
                              node.get("rotation") or [0, 0, 0], node.get("color"))
                    if node.get("uuid"):
                        g.uuid = node["uuid"]
                    m.groups.append(g)
                    groups_by_uuid[g.uuid] = g
                attach(g, parent)
                for child in node.get("children") or []:
                    walk(child, g)

        for node in d.get("outliner") or []:
            walk(node)

        placed = set()

        def mark(n):
            placed.add(id(n))
            for c in getattr(n, "children", []):
                mark(c)

        for n in m.root_nodes:
            mark(n)
        for el in list(m.elements) + list(m.groups):
            if id(el) not in placed:
                attach(el, None)

        m.alloc = None
        m._source_meta = meta
        m.animations = list(d.get("animations") or [])
        m.loaded_group_names = {
            (g or {}).get("uuid"): (g or {}).get("name")
            for g in (d.get("groups") or []) if isinstance(g, dict)
        }
        # 4.x outliner nests group data: recover uuid->name from there too
        def _scan_outliner(nodes):
            for n in nodes or []:
                if isinstance(n, dict):
                    if n.get("uuid") and n.get("name"):
                        m.loaded_group_names.setdefault(n["uuid"], n["name"])
                    _scan_outliner(n.get("children") or [])
        _scan_outliner(d.get("outliner") or [])
        return m

    def reset_alloc(self, gap=1, margin=1):
        """Creates a new UV allocator (only for loaded models). May overlap existing UVs."""
        self.alloc = UVAllocator(self.tex_w, self.tex_h, gap=gap, margin=margin)
        return self.alloc

    # -- derived data -------------------------------------------------------
    def uv_regions(self):
        """Map {(element, face): [u1,v1,u2,v2]} for painting the texture."""
        out = {}
        for el in self.elements:
            if isinstance(el, Cube):
                for d, fs in el.faces.items():
                    if fs.enabled:
                        out[(el.name, d)] = list(fs.uv)
            else:
                for i, f in enumerate(el.faces):
                    if f["uv"]:
                        us = [u for (u, _) in f["uv"]]
                        vs = [v for (_, v) in f["uv"]]
                        out[(el.name, f"f{i}")] = [min(us), min(vs), max(us), max(vs)]
        return out

    def stats(self):
        tris = 0
        for el in self.elements:
            if isinstance(el, Cube):
                tris += 2 * sum(1 for fs in el.faces.values() if fs.enabled)
            else:
                tris += sum(len(f["vertices"]) - 2 for f in el.faces)
        used = [list(fs.uv) for el in self.elements if isinstance(el, Cube)
                for fs in el.faces.values() if fs.enabled]
        for el in self.elements:
            if not isinstance(el, Cube):
                for f in el.faces:
                    if f["uv"]:
                        us = [u for (u, _) in f["uv"]]
                        vs = [v for (_, v) in f["uv"]]
                        used.append([min(us), min(vs), max(us), max(vs)])
        area = sum(abs(r[2] - r[0]) * abs(r[3] - r[1]) for r in used)
        total = self.tex_w * self.tex_h
        return {
            "elements": len(self.elements),
            "groups": len(self.groups),
            "tris": tris,
            "uv_regions": len(used),
            "tex_used_pct": round(100.0 * area / total, 1) if total else 0.0,
        }

    def validate(self, style=False, detail=False, tipo="default"):
        """Runs bbcheck on the in-memory model. Returns the check dict."""
        import os, sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bbcheck
        try:
            d = self.to_dict()
        except ValueError:
            d = None
        if d is None:
            return bbcheck.check({}, style=style, detail=detail, tipo=tipo)
        return bbcheck.check(d, style=style, detail=detail, tipo=tipo)

    def animation(self, name, loop="loop", length=1.0):
        for a in self.animations:
            if a.get("name") == name:
                return a
        a = {
            "uuid": det_uuid("animation", name),
            "name": name,
            "loop": loop,
            "length": float(length),
            "animators": {},
        }
        self.animations.append(a)
        return a

    def keyframe(self, anim, bone, channel, time, value):
        if isinstance(anim, str):
            anim = self.animation(anim)
        bone_uuid = None
        for g in self.groups:
            if g.name == bone:
                bone_uuid = g.uuid
                break
        if bone_uuid is None:
            raise ValueError(f"bone/group {bone!r} does not exist")
        animators = anim.setdefault("animators", {})
        an = animators.setdefault(bone_uuid, {"name": bone, "type": "bone", "keyframes": []})
        an["name"] = bone
        an["type"] = "bone"
        v = [float(x) for x in value]
        kf = {
            "uuid": det_uuid("keyframe", f"{anim['name']}:{bone}:{channel}:{time}"),
            "channel": channel,
            "time": float(time),
            "interpolation": "linear",
            "data_points": [{"x": v[0], "y": v[1], "z": v[2]}],
        }
        an.setdefault("keyframes", []).append(kf)
        return kf

    def _ancestor_chain(self, node):
        chain = []
        p = node.parent
        while p is not None:
            chain.append(p)
            p = p.parent
        chain.reverse()
        return chain

    def _element_world_transform(self, el):
        """Returns a function that takes an authored point into world space."""
        el_rot = el.rotation
        el_origin = el.origin
        chain = [(g.rotation, g.origin) for g in self._ancestor_chain(el)]

        def f(v):
            v = _rotate_around(el_rot, el_origin, v)
            for rot, org in chain:
                v = _rotate_around(rot, org, v)
            return v

        return f

    def bake(self):
        """Flattens the model into triangles with per-corner UV. Used by GLB and render.

        Returns dict: tris = [ (p0, p1, p2, uv0, uv1, uv2), ... ] with p in world space
        and uv in texture pixels.
        """
        tris = []
        for el in self.elements:
            world = self._element_world_transform(el)
            if isinstance(el, Cube):
                infl = float(el.inflate)
                frm = [el.frm[i] - infl for i in range(3)]
                to = [el.to[i] + infl for i in range(3)]
                verts = [world(v) for v in cube_vertex_table(frm, to)]
                for d in DIRECTIONS:
                    fs = el.faces[d]
                    if not fs.enabled:
                        continue
                    idx = FACE_VERTICES[d]  # internal order (v0..v3)
                    corners = face_uv_corners(fs.uv, fs.rotation)  # k-th vertex -> k-th corner
                    pts = [verts[i] for i in idx]
                    uvs = corners
                    # winding matches Blockbench's OBJ exporter: tris (2,1,0) and (3,2,0)
                    tris.append((pts[2], pts[1], pts[0], uvs[2], uvs[1], uvs[0]))
                    tris.append((pts[3], pts[2], pts[0], uvs[3], uvs[2], uvs[0]))
            else:
                verts = [world(v) for v in el.vertices]
                for f in el.faces:
                    vis = f["vertices"]
                    pts = [verts[i] for i in vis]
                    cuvs = f["uv"] if f["uv"] else [(0.0, 0.0)] * len(vis)
                    for i in range(1, len(vis) - 1):
                        tris.append((pts[0], pts[i], pts[i + 1],
                                     cuvs[0], cuvs[i], cuvs[i + 1]))
        return {"tris": tris, "tex_w": self.tex_w, "tex_h": self.tex_h, "png": self.texture_png}

    # -- serialization ------------------------------------------------------
    def to_dict(self):
        if any(c.faces and any(fs.enabled for fs in c.faces.values()) for c in self.elements
               if isinstance(c, Cube)) and not self.textures and self.texture_png is None:
            raise ValueError(
                "model has faces with texture but no texture attached. "
                "Call attach_texture(...) before saving."
            )
        elements = []
        for el in self.elements:
            if isinstance(el, Cube):
                d = {
                    "name": el.name,
                    "type": "cube",
                    "uuid": el.uuid,
                    "from": el.frm,
                    "to": el.to,
                    "origin": el.origin,
                    "autouv": 0,
                }
                if any(el.rotation):
                    d["rotation"] = el.rotation
                if el.inflate:
                    d["inflate"] = el.inflate
                if el.mirror_uv:
                    d["mirror_uv"] = True
                if el.color is not None:
                    d["color"] = el.color
                faces = {}
                for face_dir in DIRECTIONS:
                    fs = el.faces[face_dir]
                    if not fs.enabled:
                        faces[face_dir] = {"texture": None}
                    else:
                        fd = {"uv": [_num(x) for x in fs.uv], "texture": int(fs.texture)}
                        if fs.rotation:
                            fd["rotation"] = fs.rotation
                        if fs.tint is not None:
                            fd["tint"] = fs.tint
                        faces[face_dir] = fd
                d["faces"] = faces
                elements.append(d)
            else:
                verts = {}
                for i, v in enumerate(el.vertices):
                    rel = [v[j] - el.origin[j] for j in range(3)]
                    verts[str(i)] = [_num(rel[0]), _num(rel[1]), _num(rel[2])]
                faces = {}
                for fi, f in enumerate(el.faces):
                    fd = {
                        "vertices": list(f["vertices"]),
                        "texture": 0,
                    }
                    if f["uv"]:
                        fd["uv"] = {
                            str(vis): [_num(uv[0]), _num(uv[1])]
                            for vis, uv in zip(f["vertices"], f["uv"])
                        }
                    faces[str(fi)] = fd
                d = {
                    "name": el.name,
                    "type": "mesh",
                    "uuid": el.uuid,
                    "vertices": verts,
                    "faces": faces,
                    "origin": el.origin,
                }
                if any(el.rotation):
                    d["rotation"] = el.rotation
                if el.color is not None:
                    d["color"] = el.color
                elements.append(d)

        def outliner_node(node):
            if isinstance(node, Group):
                return {
                    "uuid": node.uuid,
                    "isOpen": True,
                    "children": [outliner_node(c) for c in node.children],
                }
            return node.uuid

        groups = []
        for g in self.groups:
            gd = {"name": g.name, "uuid": g.uuid, "origin": g.origin}
            if any(g.rotation):
                gd["rotation"] = g.rotation
            if g.color is not None:
                gd["color"] = g.color
            groups.append(gd)

        if not self.textures and self.texture_png is not None:
            self.textures = [(self.texture_png, self.texture_name, self.texture_uuid)]

        model = {
            "meta": {
                "format_version": FORMAT_VERSION,
                "model_format": "free",
                "box_uv": False,
            },
            "name": self.name,
            "resolution": {"width": self.tex_w, "height": self.tex_h},
            "elements": elements,
            "outliner": [outliner_node(n) for n in self.root_nodes],
            "textures": [],
            "groups": groups,
            "animations": list(self.animations),
        }
        for (png, tname, tuuid) in self.textures:
            b64 = base64.b64encode(png).decode("ascii")
            model["textures"].append({
                "path": "",
                "name": tname,
                "folder": "block",
                "namespace": "",
                "id": str(model["textures"].__len__()),
                "particle": False,
                "render_mode": "default",
                "visible": True,
                "mode": "bitmap",
                "saved": False,
                "uuid": tuuid,
                "source": "data:image/png;base64," + b64,
            })
        return model

    def save(self, path, pretty=False):
        d = self.to_dict()
        with open(path, "w", encoding="utf-8") as fh:
            if pretty:
                json.dump(d, fh, indent=2, ensure_ascii=True)
            else:
                json.dump(d, fh, separators=(",", ":"), ensure_ascii=True)
        return path


# ---------------------------------------------------------------------------
# Animation preservation across builds
# ---------------------------------------------------------------------------

def preserve_animations(prev, model):
    """Copies animations from a previous model into the freshly built `model`.

    `prev` can be: a .bbmodel dict, a path to a .bbmodel, or a loaded Model.

    Why it exists: `animations.animators` is indexed by the bone (group) UUID.
    A rebuild reconstructs the hierarchy, so the keys must be remapped by bone
    NAME. Bones that disappeared from the new rig are dropped with a warning
    (the rest of the animation is preserved).

    Golden rule: call BEFORE m.save()/bburl.build_url(), otherwise animations
    vanish from the .bbmodel and from the web app link.
    """
    import copy

    if prev is None:
        return model
    if isinstance(prev, Model):
        name_by_uuid = dict(getattr(prev, "loaded_group_names", {}) or {})
        anims = list(prev.animations or [])
    elif isinstance(prev, dict):
        name_by_uuid = {
            (g or {}).get("uuid"): (g or {}).get("name")
            for g in (prev.get("groups") or []) if isinstance(g, dict)
        }
        anims = list(prev.get("animations") or [])
    elif isinstance(prev, str):
        if not os.path.exists(prev):
            return model
        with open(prev, encoding="utf-8") as fh:
            return preserve_animations(json.load(fh), model)
    else:
        raise TypeError("prev must be a dict, a .bbmodel path or a Model")

    if not anims:
        return model

    uuid_by_name = {g.name: g.uuid for g in model.groups}
    dropped = set()
    out = []
    for anim in anims:
        a = copy.deepcopy(anim)
        animators = {}
        for bone_uuid, animator in (a.get("animators") or {}).items():
            bone_name = (animator or {}).get("name") or name_by_uuid.get(bone_uuid)
            new_uuid = uuid_by_name.get(bone_name)
            if new_uuid is None:
                dropped.add(str(bone_name))
                continue
            animator = dict(animator)
            animator["uuid"] = new_uuid
            animator["name"] = bone_name
            animators[new_uuid] = animator
        if not animators:
            dropped.add(a.get("name", "?"))
            continue
        a["animators"] = animators
        out.append(a)

    if dropped:
        print(f"warning: animation preserved without missing bones: {sorted(dropped)}",
              file=sys.stderr)
    model.animations = out
    return model


# ---------------------------------------------------------------------------
# geometric utilities
# ---------------------------------------------------------------------------

def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(a):
    ln = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def _face_normal(pts, flip_if_needed=None):
    n = _norm(_cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0])))
    if flip_if_needed is not None:
        c = (sum(p[0] for p in pts) / len(pts),
             sum(p[1] for p in pts) / len(pts),
             sum(p[2] for p in pts) / len(pts))
        if _dot(n, _sub(c, flip_if_needed)) < 0:
            n = (-n[0], -n[1], -n[2])
    return n


def _smoke_test():
    import struct
    import zlib

    def tiny_png(w=16, h=16, rgba=(255, 0, 0, 255)):
        raw = b"".join(b"\x00" + bytes(rgba) * w for _ in range(h))

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    m = Model("smoke", tex_w=32, tex_h=32, density=1)
    g_root = m.group("root", origin=[8, 0, 8])
    g_gone = m.group("ghost", origin=[8, 0, 8])
    c = m.cube("block", [6, 0, 6], [10, 4, 10], group=g_root)
    dup = m.cube("block_l", [6, 0, 6], [10, 4, 10], group=g_root, origin=[8, 0, 8])
    dup_east = list(dup.faces["east"].uv)
    dup.mirror(0, 8)
    m.attach_texture_bytes(tiny_png())
    d = m.to_dict()
    assert d["meta"]["format_version"] == "5.0"
    assert len(d["elements"]) == 2
    assert isinstance(d["outliner"][0], dict) and d["outliner"][0]["children"]
    fs = d["elements"][1]["faces"]
    assert fs["west"]["uv"] == [dup_east[2], dup_east[1], dup_east[0], dup_east[3]], \
        "mirror must swap west/east + flip U"
    assert c.faces["north"].enabled and not None
    baked = m.bake()
    assert len(baked["tris"]) == 2 * 2 * 6

    import tempfile
    path = os.path.join(tempfile.gettempdir(), "bbmodel_smoke.bbmodel")
    m.save(path)
    ld = Model.load(path)
    assert ld.to_dict() == d, "save/load roundtrip diverged"
    assert ld.bake()["tris"] == baked["tris"], "save/load roundtrip changed geometry"
    assert ld.groups[0].children and ld.root_nodes and ld.root_nodes[0] is ld.groups[0]
    try:
        ld.cube("new", [0, 0, 0], [2, 2, 2], group="root")
        raise SystemExit("should have refused a cube without UV in a loaded model")
    except ValueError as exc:
        assert "allocator" in str(exc)
    ld.reset_alloc()
    ld.cube("new", [0, 0, 0], [2, 2, 2], group="root")

    # --- deterministic uuids + animation preservation ---------------------
    assert det_uuid("group", "root") == det_uuid("group", "root")
    assert det_uuid("group", "root") != det_uuid("cube", "root")

    # animation with 2 bones; one of them disappears in the rebuild
    anim = [{
        "uuid": guid(), "name": "fly", "loop": "loop", "length": 1,
        "animators": {
            g_root.uuid: {"name": "root", "type": "bone", "keyframes": [
                {"uuid": guid(), "channel": "position", "time": 0,
                 "data_points": [{"x": 0, "y": 0, "z": 0}]}]},
            g_gone.uuid: {"name": "ghost", "type": "bone", "keyframes": [
                {"uuid": guid(), "channel": "rotation", "time": 0,
                 "data_points": [{"x": 0, "y": 0, "z": 90}]}]},
        },
    }]
    m.animations = anim
    assert m.to_dict()["animations"][0]["name"] == "fly", "to_dict must emit animations"

    # rebuild: same hierarchy, same script -> bone keeps its UUID
    m2 = Model("smoke", tex_w=64, tex_h=64, density=2)
    root2 = m2.group("root")
    m2.cube("a", [0, 0, 0], [4, 4, 4], group=root2)
    m2.attach_texture_bytes(tiny_png())
    assert root2.uuid == g_root.uuid, "group uuid must be stable across builds"

    preserve_animations({"groups": [
        {"uuid": g_root.uuid, "name": "root"},
        {"uuid": g_gone.uuid, "name": "ghost"}], "animations": anim}, m2)
    assert len(m2.animations) == 1
    kept = m2.animations[0]["animators"]
    assert list(kept) == [root2.uuid], "only existing bones must remain"
    assert kept[root2.uuid]["name"] == "root"
    assert m2.to_dict()["animations"], "preserved animations must reach to_dict"
    os.unlink(path)
    print("smoke OK —", m.stats())


if __name__ == "__main__":
    _smoke_test()
