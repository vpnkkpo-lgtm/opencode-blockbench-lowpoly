#!/usr/bin/env python3
"""
bburl.py — builds the Blockbench web app link (web.blockbench.net) that opens
the model without downloading.

Format (verified against the web-link.ts source of the blockbench-mcp-plugin):
    https://web.blockbench.net/#loadtype=json&loadname=NAME&loaddata=DATA

The app decodes the hash with a SINGLE decodeURIComponent, splits on '&' and
does JSON.parse on loaddata. Therefore:
- JSON is compact (no spaces)
- every '&' is escaped as \\u0026 (valid JSON escape) BEFORE percent-encoding
- percent-encoding uses the same set as encodeURIComponent

Usage:
    from bburl import build_url, verify
    url = build_url(model)          # bbmodel.Model | dict | path to .bbmodel
    assert verify(url)              # roundtrip: decode -> parse -> dict

    python3 bburl.py model.bbmodel [--out link.txt] [--verify-only URL]
"""

import json
import os
import re
import sys
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "https://web.blockbench.net/#"
SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
MAX_HASH_WARN = 1_500_000
# The web app picks the codec by the EXTENSION of loadname (js/io/io.js: pathToExtension
# + load_filter.extensions). Without ".bbmodel" no codec matches and the app shows
# "invalid format" (unsupportedFileFormatMessage).
PROJECT_EXT = ".bbmodel"


def encode_loaddata(data):
    """data: dict or JSON string -> percent-encoded value safe for the hash."""
    if not isinstance(data, str):
        data = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    data = data.replace("&", "\\u0026")
    return quote(data, safe="!*'()")


def build_url(model, name=None, base=BASE, ext=PROJECT_EXT):
    """Web app URL. `name` becomes the loadname and MUST end in .bbmodel."""
    if hasattr(model, "to_dict"):
        name = name or getattr(model, "name", "model")
        data = model.to_dict()
    elif isinstance(model, dict):
        data = model
    elif isinstance(model, str):
        with open(model, encoding="utf-8") as fh:
            data = json.load(fh)
        name = name or os.path.splitext(os.path.basename(model))[0]
    else:
        raise TypeError("model must be a Model, dict or path to a .bbmodel")
    safe = SAFE_NAME.sub("_", name or "model") or "model"
    if ext and not safe.lower().endswith(ext):
        safe = os.path.splitext(safe)[0] + ext
    enc = encode_loaddata(data)
    url = f"{base}loadtype=json&loadname={quote(safe, safe='')}&loaddata={enc}"
    if len(url) > MAX_HASH_WARN:
        print(f"warning: URL with {len(url)} chars — some browsers/apps truncate long links",
              file=sys.stderr)
    return url


def verify(url):
    r"""Simulates EXACTLY the web app parser (js/web.ts).

    query_string = decodeURIComponent(hash.substring(1)); split('&');
    [key, value] = string.split(/=\s*(.+)/)
    """
    hashpart = url.split("#", 1)[1] if "#" in url else url
    decoded = unquote(hashpart)
    fields = {}
    for pair in decoded.split("&"):
        m = re.split(r"=\s*(.+)", pair)
        if len(m) >= 2 and m[0]:
            fields[m[0]] = m[1]
    assert fields.get("loadtype") == "json", f"loadtype={fields.get('loadtype')!r}"
    loadname = fields.get("loadname") or ""
    assert loadname.lower().endswith(PROJECT_EXT), (
        f"loadname {loadname!r} without {PROJECT_EXT} — the web app rejects with 'invalid format'")
    data = json.loads(fields["loaddata"])
    return data


def check_url(url_or_path):
    """Returns the decoded dict + basic integrity checks."""
    if os.path.exists(url_or_path):
        with open(url_or_path, encoding="utf-8") as fh:
            url = fh.read().strip()
    else:
        url = url_or_path
    data = verify(url)
    assert "meta" in data and "elements" in data, "JSON does not look like a .bbmodel"
    return data


def _demo():
    import bbmodel as bm
    import bbtex
    m = bm.Model("mushroom & co", tex_w=32, tex_h=32, density=1)
    g = m.group("root")
    m.cube("hat", [0, 4, 0], [12, 8, 12], group=g)
    png = bbtex.blank_png(32, 32, color=(220, 70, 90, 255))
    m.attach_texture_bytes(png)
    url = build_url(m)
    data = verify(url)
    assert data == m.to_dict(), "link roundtrip failed"
    assert "&loaddata=" in url and data["name"] == "mushroom & co"
    assert "&loadname=mushroom" in url and ".bbmodel" in url
    assert " " not in url.split("#")[1].split("&loadname=")[1].split("&")[0]
    print(f"bburl smoke OK — {len(url)} chars, loadname and roundtrip ok")
    print(url[:110] + "...")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if argv[0] == "--demo":
        _demo()
        return 0
    if "--verify-only" in argv:
        data = check_url(argv[argv.index("--verify-only") + 1])
        print(f"link ok — model {data.get('name')!r}, {len(data['elements'])} elements")
        return 0
    path = argv[0]
    url = build_url(path)
    if "--verify" in argv:
        check_url(url)
        print("roundtrip ok")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(url)
        print(f"link saved to {out} ({len(url)} chars)")
    else:
        print(url)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _demo()
    else:
        sys.exit(main(sys.argv[1:]))
