#!/usr/bin/env python3
"""
bbkit.py — kit for FINE DETAIL and DIRECT MANIPULATION for blockbench-lowpoly.

Why it exists: modeling with only large `Model.cube` calls gives a "box". The
distance to a quality reference comes from (a) shapes with cut corners/bevel,
(b) small details (rivets, grooves, teeth, buckles) and (c) being able to place
those details **on the face of another piece** without guessing coordinates.

Primitives:

    Shapes (become "free" Mesh, 1 element, planar UV):
        bevel_box  taper_box  wedge  pyramid  cylinder  sphere

    Detail relative to a FACE (the heart of "direct manipulation"):
        face_rect  on_face  grid_of  edge_trim
        FACE_BASIS: north/east/south/west/up/down

    Symmetry and copies:
        duplicate  mirror_group

    Post-editing (edit a loaded model without rewriting the build):
        translate  resize  set_extent  set_origin  rotate  remove  find  bounds

UV rule: detail < 0.5u on a 1px face is illegible. Build detail islands with
`Model(density=3)` (or higher) — the rest of the model can stay at 2.
"""

import copy
import math

DIRECTIONS = ("north", "east", "south", "west", "up", "down")

# face -> (normal, right(u+), up(v+))  — unit vectors in world space
FACE_BASIS = {
    "north": ((0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "east":  ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "south": ((0.0, 0.0, 1.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "west":  ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "up":    ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, -1.0)),
    "down":  ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
}


# ---------------------------------------------------------------- utilities

def find(model, name):
    """Element (Cube/Mesh) by name; raises KeyError if it doesn't exist."""
    for el in model.elements:
        if el.name == name:
            return el
    raise KeyError(f"element {name!r} does not exist in the model")


def _bounds(el):
    if hasattr(el, "frm"):
        return list(el.frm), list(el.to)
    vs = el.vertices
    return ([min(v[i] for v in vs) for i in range(3)],
            [max(v[i] for v in vs) for i in range(3)])


def bounds(model, name):
    """(frm, to) of the element — including meshes."""
    return _bounds(find(model, name))


def snap(v, step=0.25, mode="nearest"):
    """Snaps a value (or triple) to a grid. mode: nearest|min|max."""
    if step <= 0:
        return v
    fn = {"nearest": lambda x: round(x / step) * step,
          "min": lambda x: math.floor(x / step) * step,
          "max": lambda x: math.ceil(x / step) * step}[mode]
    if isinstance(v, (list, tuple)):
        return [fn(x) for x in v]
    return fn(v)


def _round_pt(p, nd=6):
    return tuple(round(x, nd) for x in p)


# --------------------------------------------------- detail relative to face

def _face_point(frm, to, face, u, v):
    """Maps (u,v) in fraction 0..1 of the face to a world point."""
    n, r, up = FACE_BASIS[face]
    p = []
    for a in range(3):
        span = to[a] - frm[a]
        if r[a]:
            p.append(frm[a] + u * span if r[a] > 0 else to[a] - u * span)
        elif up[a]:
            p.append(frm[a] + v * span if up[a] > 0 else to[a] - v * span)
        else:
            p.append(to[a] if n[a] > 0 else frm[a])
    return p


def face_rect(model, name, face, cu=0.5, cv=0.5, du=1.0, dv=1.0,
              depth=0.1, sink=0.02, grid=0.0):
    """Rectangle (frm, to) of a block resting on face `face` of element `name`.

    cu/cv: center as a fraction of the face (0..1). du/dv: size as a fraction.
    depth: how far it PROTRUDES out of the face. sink: penetration (avoids z-fight).
    grid: 0 = free; e.g. 0.25 = coordinates snapped to the grid.
    """
    if face not in FACE_BASIS:
        raise ValueError(f"invalid face {face!r}; use {DIRECTIONS}")
    frm, to = _bounds(find(model, name))
    du = min(max(float(du), 1e-6), 1.0)
    dv = min(max(float(dv), 1e-6), 1.0)
    cu = min(max(float(cu), 0.0), 1.0)
    cv = min(max(float(cv), 0.0), 1.0)
    du = min(du, 2 * cu, 2 * (1 - cu))
    dv = min(dv, 2 * cv, 2 * (1 - cv))

    corners = [(cu - du / 2, cv - dv / 2), (cu + du / 2, cv - dv / 2),
               (cu + du / 2, cv + dv / 2), (cu - du / 2, cv + dv / 2)]
    pts = [_face_point(frm, to, face, u, v) for (u, v) in corners]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]

    n = FACE_BASIS[face][0]
    a_n = next(a for a in range(3) if n[a])
    depth = max(float(depth), 0.0)
    sink = max(float(sink), 0.0)
    if n[a_n] > 0:
        hi[a_n] = to[a_n] + depth
        lo[a_n] = to[a_n] - sink
    else:
        lo[a_n] = frm[a_n] - depth
        hi[a_n] = frm[a_n] + sink

    for i in range(3):
        if grid:
            lo[i] = math.floor(lo[i] / grid) * grid
            hi[i] = math.ceil(hi[i] / grid) * grid
        else:
            # never smaller than 1 texel: sub-texel detail breaks UV density
            min_side = 1.0 / max(float(getattr(model, "density", 2) or 2), 0.01)
            if hi[i] - lo[i] < min_side:
                ctr = (lo[i] + hi[i]) / 2
                lo[i], hi[i] = ctr - min_side / 2, ctr + min_side / 2
        if hi[i] - lo[i] < 1e-4:
            lo[i] -= 0.0005
            hi[i] += 0.0005
    return _round_pt(lo), _round_pt(hi)


def _default_faces(face):
    """Fine detail only needs the support face + top (the rest is UV junk)."""
    return [face] if face == "up" else [face, "up"]


def on_face(model, name, parent, face, cu=0.5, cv=0.5, du=1.0, dv=1.0,
            depth=0.1, sink=0.02, grid=0.0, faces=None, **cube_kw):
    """Creates a cube resting on another element's face (the "small detail")."""
    frm, to = face_rect(model, parent, face, cu, cv, du, dv, depth, sink, grid)
    return model.cube(name, frm, to,
                      faces=faces if faces is not None else _default_faces(face),
                      **cube_kw)


def grid_of(model, prefix, parent, face, nu=3, nv=2, du=0.6, dv=0.6,
            depth=0.1, sink=0.02, grid=0.0, span_u=0.8, span_v=0.8, **cube_kw):
    """nu x nv blocks distributed over the face (rivets, teeth, bricks...)."""
    out = []
    k = 0
    for j in range(nv):
        for i in range(nu):
            cu = 0.5 if nu == 1 else 0.5 - span_u / 2 + span_u * (i + 0.5) / nu
            cv = 0.5 if nv == 1 else 0.5 - span_v / 2 + span_v * (j + 0.5) / nv
            out.append(on_face(model, f"{prefix}_{k}", parent, face, cu, cv,
                               du, dv, depth, sink, grid, **cube_kw))
            k += 1
    return out


def edge_trim(model, prefix, parent, face, thickness=0.1, depth=0.06,
              sink=0.02, grid=0.0, sides=("top", "bottom", "left", "right"), **cube_kw):
    """Trims glued to the edges of the face (rim, belt, molding)."""
    out = []
    t = max(float(thickness), 0.0)
    rects = {
        "top": (0.5, 1 - t, 1.0, t),
        "bottom": (0.5, t, 1.0, t),
        "left": (t, 0.5, t, 1.0),
        "right": (1 - t, 0.5, t, 1.0),
    }
    for side in sides:
        cu, cv, du, dv = rects[side]
        out.append(on_face(model, f"{prefix}_{side}", parent, face, cu, cv, du, dv,
                           depth, sink, grid, **cube_kw))
    return out


# ------------------------------------------------------------------- copies

def duplicate(model, name, new_name, offset=(0.0, 0.0, 0.0), group=None):
    """Clones a Cube/Mesh (with UVs) shifted by `offset`."""
    el = find(model, name)
    off = [float(o) for o in offset]
    if hasattr(el, "frm"):
        frm = [el.frm[i] + off[i] for i in range(3)]
        to = [el.to[i] + off[i] for i in range(3)]
        origin = [el.origin[i] + off[i] for i in range(3)]
        new = type(el)(new_name, frm, to, origin, list(el.rotation),
                       float(el.inflate), bool(getattr(el, "mirror_uv", False)),
                       getattr(el, "color", None))
        new.faces = {d: fs.clone() for d, fs in el.faces.items()}
    else:
        origin = [el.origin[i] + off[i] for i in range(3)]
        new = type(el)(new_name, [tuple(v[i] + off[i] for i in range(3))
                                  for v in el.vertices],
                       copy.deepcopy(el.faces), origin, list(el.rotation),
                       color=getattr(el, "color", None))
    model._attach(new, group if group is not None else el.parent)
    return new


def mirror_group(model, names, axis=0, center=0.0, suffix="_mir", group=None):
    """Clones `names` mirrored around `axis`/`center` (cheap symmetry)."""
    out = []
    for n in names:
        dup = duplicate(model, n, f"{n}{suffix}", group=group)
        dup.mirror(axis, center)
        out.append(dup)
    return out


# ---------------------------------------------------------------- post-editing

def translate(model, name, d=(0.0, 0.0, 0.0)):
    """Moves the element (and re-anchors the origin along with it)."""
    el = find(model, name)
    d = [float(x) for x in d]
    if hasattr(el, "frm"):
        el.frm = _round_pt([el.frm[i] + d[i] for i in range(3)])
        el.to = _round_pt([el.to[i] + d[i] for i in range(3)])
    else:
        el.vertices = [_round_pt([v[i] + d[i] for i in range(3)]) for v in el.vertices]
    el.origin = _round_pt([el.origin[i] + d[i] for i in range(3)])
    return el


def resize(model, name, axis, size, anchor="min"):
    """Sets the size on the axis (anchor: min|max|center) keeping the other end."""
    el = find(model, name)
    frm, to = _bounds(el)
    size = abs(float(size))
    if anchor == "min":
        frm[axis], to[axis] = frm[axis], frm[axis] + size
    elif anchor == "max":
        frm[axis], to[axis] = to[axis] - size, to[axis]
    else:
        c = (frm[axis] + to[axis]) / 2
        frm[axis], to[axis] = c - size / 2, c + size / 2
    return _set_box(model, el, frm, to)


def set_extent(model, name, axis, value, end="to"):
    """Snaps the edge (to|frm) of the axis to the given coordinate."""
    el = find(model, name)
    frm, to = _bounds(el)
    v = float(value)
    if end == "to":
        to[axis] = v
    elif end == "frm":
        frm[axis] = v
    else:
        c = v
        size = to[axis] - frm[axis]
        frm[axis], to[axis] = c - size / 2, c + size / 2
    return _set_box(model, el, frm, to)


def _set_box(model, el, frm, to):
    if frm[0] > to[0] or frm[1] > to[1] or frm[2] > to[2]:
        raise ValueError(f"{el.name}: from < to required (received {frm} -> {to})")
    if hasattr(el, "frm"):
        el.frm, el.to = _round_pt(frm), _round_pt(to)
    else:  # mesh: remap the bbox by affine (vertices are relative to the origin)
        old_f, old_t = _bounds(el)
        scale, shift = [], []
        for i in range(3):
            old_span = max(old_t[i] - old_f[i], 1e-9)
            k = (to[i] - frm[i]) / old_span
            scale.append(k)
            shift.append(frm[i] - old_f[i] * k)
        el.vertices = [_round_pt([v[i] * scale[i] + shift[i] for i in range(3)])
                       for v in el.vertices]
    return el


def set_origin(model, name, p):
    """Moves only the pivot (rotation now spins around p)."""
    el = find(model, name)
    el.origin = _round_pt([float(x) for x in p])
    return el


def rotate(model, name, d=(0.0, 0.0, 0.0)):
    """Adds degrees on X/Y/Z (same ZYX order as Blockbench)."""
    el = find(model, name)
    el.rotation = [round(el.rotation[i] + float(d[i]), 6) for i in range(3)]
    return el


def remove(model, name):
    """Removes an element (cube or mesh) from the model."""
    el = find(model, name)
    model.elements = [e for e in model.elements if e is not el]
    for g in model.groups:
        g.children = [c for c in g.children if c is not el]
    model.root_nodes = [n for n in model.root_nodes if n is not el]
    return el


# -------------------------------------------------------------------- shapes
# Mesh helpers: normals via Newell (order-independent), angular sorting of
# vertices (convex polygon) and outward orientation by the volume center.

def _plane_normal(pts):
    """Plane normal from ANY non-collinear triple (convex planar polygon)."""
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                t = _cross(_sub3(pts[j], pts[i]), _sub3(pts[k], pts[i]))
                ln = math.sqrt(sum(c * c for c in t))
                if ln > 1e-9:
                    return [c / ln for c in t]
    return None


def _sub3(a, b):
    return [a[i] - b[i] for i in range(3)]


def _basis(n):
    ref = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    t = _cross(n, ref)
    ln = math.sqrt(sum(c * c for c in t))
    t = [c / ln for c in t]
    b = _cross(n, t)
    return t, b


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _poly(idxs, verts, center):
    """Sorts the indices into a convex polygon and ensures an outward normal.

    Must NOT depend on input order: find the plane from a triple, sort by angle
    around the center, and only then orient outward.
    """
    pts = [verts[i] for i in idxs]
    c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    n = _plane_normal(pts)
    if n is None:
        return idxs  # truly degenerate: let bbcheck report it
    t, b = _basis(n)
    order = sorted(range(len(pts)),
                   key=lambda k: math.atan2(sum((pts[k][i] - c[i]) * b[i] for i in range(3)),
                                            sum((pts[k][i] - c[i]) * t[i] for i in range(3))))
    idxs = [idxs[k] for k in order]
    if sum(n[i] * (c[i] - center[i]) for i in range(3)) < 0:
        idxs.reverse()
    return idxs


def _box_center(frm, to):
    return [(frm[i] + to[i]) / 2 for i in range(3)]


def bevel_box(model, name, frm, to, bevel=0.2, group=None, uv="planar", **kw):
    """Box with all 12 edges chamfered at 45° (6 octagons + 12 quads + 8 tris).

    Highest-return trick: removes the "box" look without leaving low poly.
    """
    frm = [float(x) for x in frm]
    to = [float(x) for x in to]
    b = float(bevel)
    span = [to[i] - frm[i] for i in range(3)]
    b = min([b] + [s / 2.5 for s in span])
    if b <= 0:
        raise ValueError("bevel must be > 0 and <= 1/2.5 of the smallest edge")
    verts, tags = [], []
    for ci in range(8):
        c = [(ci >> k) & 1 for k in range(3)]
        for pulled in range(3):
            p = []
            for a in range(3):
                if a == pulled:
                    p.append(frm[a] + b if c[a] == 0 else to[a] - b)
                else:
                    p.append(frm[a] if c[a] == 0 else to[a])
            verts.append(_round_pt(p))
            tags.append((ci, pulled))

    def idx(pred):
        return [i for i, (ci, k) in enumerate(tags) if pred(ci, k)]

    faces = []
    center = _box_center(frm, to)
    for a in range(3):
        for s in (0, 1):
            faces.append(_poly(idx(lambda ci, k, a=a, s=s: ((ci >> a) & 1) == s and k != a),
                              verts, center))
    for a in range(3):
        for b2 in range(a + 1, 3):
            for sa in (0, 1):
                for sb in (0, 1):
                    faces.append(_poly(idx(lambda ci, k, a=a, b2=b2, sa=sa, sb=sb:
                                            ((ci >> a) & 1) == sa and ((ci >> b2) & 1) == sb
                                            and k in (a, b2)), verts, center))
    for ci in range(8):
        faces.append(_poly(idx(lambda ci2, k, ci=ci: ci2 == ci), verts, center))
    return model.mesh(name, verts, faces, group=group, uv=uv, **kw)


def taper_box(model, name, frm, to, shrink=(0.5, 0.5), offset=(0.0, 0.0), group=None,
              uv="planar", **kw):
    """Tapered box: smaller top (shrink as a fraction per X/Z axis) and offset."""
    frm = [float(x) for x in frm]
    to = [float(x) for x in to]
    sx = to[0] - frm[0]
    sz = to[2] - frm[2]
    cx = (frm[0] + to[0]) / 2 + float(offset[0])
    cz = (frm[2] + to[2]) / 2 + float(offset[1])
    top = [cx - sx * (1 - float(shrink[0])) / 2, to[1],
           cz - sz * (1 - float(shrink[1])) / 2]
    top_span = [sx * float(shrink[0]), sz * float(shrink[1])]
    verts = [_round_pt(frm), _round_pt([to[0], frm[1], frm[2]]),
             _round_pt([to[0], frm[1], to[2]]), _round_pt([frm[0], frm[1], to[2]]),
             _round_pt([top[0] - top_span[0] / 2, top[1], top[2] - top_span[1] / 2]),
             _round_pt([top[0] + top_span[0] / 2, top[1], top[2] - top_span[1] / 2]),
             _round_pt([top[0] + top_span[0] / 2, top[1], top[2] + top_span[1] / 2]),
             _round_pt([top[0] - top_span[0] / 2, top[1], top[2] + top_span[1] / 2])]
    faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    center = _box_center(frm, to)
    return model.mesh(name, verts, [_poly(f, verts, center) for f in faces],
                      group=group, uv=uv, **kw)


def wedge(model, name, frm, to, axis=0, group=None, uv="planar", **kw):
    """Ramp: triangular prism. The top drops to the base at the `max` end of the axis.

    axis: 0 = drops along X, 2 = drops along Z (height is always Y).
    Use for roofs, hull noses, chute ramps, tapering feet.
    """
    frm = [float(x) for x in frm]
    to = [float(x) for x in to]
    if axis == 0:
        verts = [_round_pt([frm[0], frm[1], frm[2]]), _round_pt([frm[0], to[1], frm[2]]),
                 _round_pt([frm[0], to[1], to[2]]), _round_pt([frm[0], frm[1], to[2]]),
                 _round_pt([to[0], frm[1], frm[2]]), _round_pt([to[0], frm[1], to[2]])]
    elif axis == 2:
        verts = [_round_pt([frm[0], frm[1], frm[2]]), _round_pt([frm[0], to[1], frm[2]]),
                 _round_pt([to[0], to[1], frm[2]]), _round_pt([to[0], frm[1], frm[2]]),
                 _round_pt([frm[0], frm[1], to[2]]), _round_pt([to[0], frm[1], to[2]])]
    else:
        raise ValueError("wedge: axis must be 0 (drops along X) or 2 (drops along Z)")
    tris = [[0, 1, 4], [2, 3, 5]]
    faces = [[0, 1, 2, 3], [0, 3, 5, 4], [1, 2, 5, 4]] + tris
    center = [0.0, (frm[1] + to[1]) / 2, 0.0]
    return model.mesh(name, verts, [_poly(f, verts, center) for f in faces],
                      group=group, uv=uv, **kw)


def pyramid(model, name, frm, to, apex=None, group=None, uv="planar", **kw):
    """Rectangular-base pyramid with apex (default: center of the top face)."""
    frm = [float(x) for x in frm]
    to = [float(x) for x in to]
    apex = apex or [(frm[0] + to[0]) / 2, to[1], (frm[2] + to[2]) / 2]
    verts = [_round_pt(frm), _round_pt([to[0], frm[1], frm[2]]),
             _round_pt([to[0], frm[1], to[2]]), _round_pt([frm[0], frm[1], to[2]]),
             _round_pt(apex)]
    faces = [[0, 1, 2, 3], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    return model.mesh(name, verts, [_poly(f, verts, apex) for f in faces],
                      group=group, uv=uv, **kw)


def cylinder(model, name, center, radius, height, sides=8, axis=1, group=None,
             uv="planar", **kw):
    """Low-poly cylinder (n sides), n-gon caps. axis: 0=X, 1=Y, 2=Z."""
    n = max(3, int(sides))
    cx, cy, cz = [float(c) for c in center]
    r, h = float(radius), float(height)
    others = [a for a in range(3) if a != axis]
    ring = []
    for k in range(n):
        ang = 2 * math.pi * k / n + math.pi / n
        off = [0.0, 0.0, 0.0]
        off[others[0]] = r * math.cos(ang)
        off[others[1]] = r * math.sin(ang)
        p = [0.0, 0.0, 0.0]
        p[axis] = -h / 2
        p[others[0]] = off[others[0]]
        p[others[1]] = off[others[1]]
        ring.append(p)
    verts = [_round_pt([cx + ring[k][a] for a in range(3)]) for k in range(n)]
    verts += [_round_pt([cx + ring[k][a] + (h if a == axis else 0) for a in range(3)])
              for k in range(n)]
    faces = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    faces.append(list(range(n)))
    faces.append(list(range(2 * n - 1, n - 1, -1)))
    center_pt = (cx, cy, cz)
    return model.mesh(name, verts, [_poly(f, verts, center_pt) for f in faces],
                      group=group, uv=uv, **kw)


def sphere(model, name, center, radius, rings=4, sides=8, group=None, uv="planar", **kw):
    """Low-poly sphere (lat×long). Good for eyes, domes, rounded heads."""
    rows = max(2, int(rings))
    cols = max(3, int(sides))
    cx, cy, cz = [float(c) for c in center]
    r = float(radius)
    verts = [[cx, cy + r, cz]]
    for j in range(1, rows):
        phi = math.pi * j / rows
        for k in range(cols):
            th = 2 * math.pi * k / cols
            verts.append([cx + r * math.sin(phi) * math.cos(th),
                          cy + r * math.cos(phi),
                          cz + r * math.sin(phi) * math.sin(th)])
    verts.append([cx, cy - r, cz])
    south = len(verts) - 1
    faces = []
    for k in range(cols):
        faces.append([0, 1 + (k + 1) % cols, 1 + k])
    for j in range(rows - 2):
        b0 = 1 + j * cols
        b1 = b0 + cols
        for k in range(cols):
            k2 = (k + 1) % cols
            faces.append([b0 + k, b0 + k2, b1 + k2, b1 + k])
    last = 1 + (rows - 2) * cols
    for k in range(cols):
        faces.append([south, last + k, last + (k + 1) % cols])
    return model.mesh(name, [_round_pt(p) for p in verts],
                      [_poly(f, verts, (cx, cy, cz)) for f in faces],
                      group=group, uv=uv, **kw)


# ---------------------------------------------------------------- smoke test

def _smoke_test():
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import bbcheck
    import bbmodel

    # dense detail: larger texture + density 3 (otherwise UV overflows)
    m = bbmodel.Model("kit_smoke", tex_w=256, tex_h=256, density=3)
    g = m.group("body", origin=(8, 0, 8))
    m.cube("box", (4, 0, 4), (12, 6, 12), group=g)
    bevel_box(m, "lid", (3.5, 6, 3.5), (12.5, 8, 12.5), bevel=0.5, group=g)
    taper_box(m, "tower", (6, 8, 6), (10, 14, 10), shrink=(0.6, 0.6), group=g)
    pyramid(m, "tip", (6, 14, 6), (10, 18, 10), group=g)
    grid_of(m, "rivet", "box", "north", nu=3, nv=2, du=0.25, dv=0.25, group=g)
    edge_trim(m, "rim", "box", "up", thickness=0.12, group=g, sides=("top", "bottom"))
    cylinder(m, "barrel", (8, 8, 13), 1.2, 4, sides=6, axis=2, group=g)
    sphere(m, "eye", (6, 12, 5), 1.0, rings=4, sides=6, group=g)
    wedge(m, "ramp", (12, 0, 4), (18, 4, 10), axis=0, group=g)
    wedge(m, "roof", (12, 0, 12), (18, 4, 18), axis=2, group=g)
    duplicate(m, "rivet_0", "rivet_0_side", offset=(8, 0, 0), group=g)
    mirror_group(m, ["rivet_0", "rivet_1"], axis=0, center=8, group=g)
    translate(m, "ramp", (0, 0, -1))
    rotate(m, "barrel", (0, 0, 15))
    set_origin(m, "barrel", (8, 10, 13))
    resize(m, "lid", 1, 3.0, anchor="min")

    st = m.stats()
    assert st["elements"] >= 12, st
    # shapes are coherent meshes: no degenerate face, outward normals
    for el in m.elements:
        if hasattr(el, "frm"):
            assert all(el.frm[i] < el.to[i] for i in range(3)), el.name
    c = None
    import bbtex
    c = bbtex.Canvas.for_model(m)
    for reg in m.uv_regions().values():
        c.fill_region(reg, "#8a7f6a")
    png = c.to_png()
    m.attach_texture_bytes(png)
    rep = bbcheck.check(m.to_dict(), style=True)
    assert not rep["errors"], rep["errors"]
    print("bbkit smoke OK —", st)


if __name__ == "__main__":
    _smoke_test()
