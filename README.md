# 🧱 Blockbench LowPoly

### Forje assets 3D cute-cartoon por código — direto no OpenCode.

[![GitHub stars](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenCode Plugin](https://img.shields.io/badge/OpenCode-v2%20plugin-7c3aed)](https://opencode.ai)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://python.org)
[![Zero Deps](https://img.shields.io/badge/deps-zero-brightgreen)](#)
[![Blockbench](https://img.shields.io/badge/Blockbench-web%20app-0ea5e9)](https://web.blockbench.net)

> **Sem Blender. Sem editor. Sem MCP. Sem dependências.** Só Python puro e um agente que obedece.
> Descreva um personagem, um prop, uma arma, um mob — e receba `.bbmodel`, `.glb`, previews PNG e um link que abre o modelo **direto no web app do Blockbench**. Tudo determinístico, tudo versionável, tudo em código.

---

## ⚡ O que você ganha

| Entrega | Arquivo | Pra quê |
|---|---|---|
| Projeto nativo | `.bbmodel` | Abrir/editar no Blockbench |
| Motor/engine | `.glb` | Unity, Godot, Unreal, Three.js |
| Preview | `preview_sheet.png` | QC visual rápido (front/iso/side) |
| Link compartilhável | `link.txt` | Abre o modelo no web app do Blockbench |

Um único `build.py`. Roda de novo, byte-idêntico. Itera em segundos.

---

## 🚀 Instalação (OpenCode v2)

### Opção A — como plugin (recomendado)

Adicione ao seu `opencode.json(c)`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "github:vpnkkpo-lgtm/opencode-blockbench-lowpoly"
  ]
}
```

Ou clone e aponte localmente:

```jsonc
{
  "plugins": ["./opencode-blockbench-lowpoly"]
}
```

Pronto. A skill `blockbench-lowpoly` é registrada automaticamente e o agente passa a saber forjar assets low poly.

### Opção B — como skill solta

Copie a pasta `skills/blockbench-lowpoly` para `~/.config/opencode/skills/` (global) ou `.opencode/skills/` (projeto). Funciona sem plugin.

---

## 🎬 Quickstart (30 segundos)

```python
import sys, os
sys.path.insert(0, "skills/blockbench-lowpoly/scripts")
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl

m = Model("cogumelo", tex_w=128, tex_h=128, density=2)
corpo = m.group("corpo", origin=(8, 0, 8))
m.cube("tronco", (5, 0, 5), (11, 8, 11), group=corpo,
       faces=["north", "east", "south", "west"])

c = bbtex.Canvas.for_model(m)
c.panel(m.uv_regions()[("tronco", "north")], "#f6ddb8", light="#fdefd6", dark="#e8c894")
png = c.to_png()
m.attach_texture_bytes(png)

rep = bbcheck.check(m.to_dict(), style=True, tex_override=png)  # 0 erros, 0 avisos
bbrender.render_sheet(m, "preview.png", size=384)
m.save("asset.bbmodel")
open("asset.glb", "wb").write(__import__("bbglb").build_glb(m.bake(), "asset"))
open("link.txt", "w").write(bburl.build_url(m, "asset"))
```

Saída: `asset.bbmodel` + `asset.glb` + `preview.png` + `link.txt`. **Zero erros. Zero avisos.** 🎯

---

## 🛠️ Pipeline completo

```
planeje silhueta → escolha paleta → construa geo → pinte textura → valide → preview → entregue
```

1. **Planeje no papel** — silhueta legível a 64px, cabeça 35–50% em "cute", orçamento de tris (prop ≤800, personagem ≤3000).
2. **Paleta** — `templates/palettes_cute.json` ou ~8–20 cores próprias. **Nunca** `#000000`/`#ffffff` puros.
3. **Geometria** — `Model.cube` / `Model.mesh`; `from < to`; pivô na junta quando rigado.
4. **Textura** — Canvas com `uv_regions()` como mapa: `panel`, `outline_region`, `eyes/blush/mouth_smile`, `spot(snap=True)`.
5. **Valide** — `bbcheck.check(d, style=True)` → persiga **0 erros e 0 avisos**.
6. **Preview + QC visual** — `render_sheet` + `render(..., view="hero")` e **leia** os PNGs (confira pixels críticos em ASCII).
7. **Entregue** — `save .bbmodel`, `bbglb.build_glb`, `bburl.build_url` → `link.txt`. Itere rodando o build de novo.
8. **Animado?** — chame `bbmodel.preserve_animations(prev, m)` antes do save.

---

## 📚 API essencial

### `bbmodel.py`
- `Model(name, tex_w, tex_h, density=2, format="free")`
- `m.group(name, origin, rotation=..., parent=...)`
- `m.cube(name, frm, to, group, faces=None, uv=None, mirror_uv=False, inflate=0.0)`
- `m.mesh(name, vertices, faces, group, uv="planar")` — só `free`
- `Cube.mirror(axis, center)` / `Mesh.mirror(axis, center)`
- `m.uv_regions()` · `m.bake()` · `m.stats()` · `m.save(path)` · `Model.load(path)`
- `bbmodel.preserve_animations(prev, m)` · `bbmodel.det_uuid(kind, name)`

### `bbtex.py`
- `Canvas.for_model(m)` · `encode_png`/`decode_png` · `load_palette`
- Escrita: `set/rect/line_h/line_v/ellipse/fill_region`
- Regiões: `panel/ao/outline_region/hstripes/vstripes/dots/checker/dither`
- Cara: `eyes/blush/mouth_smile/mouth_o`
- Pintas: `spot(region, cx_frac, cy_frac, r, snap=True)` (r≥2.4)
- Final: `bleed(region, px=1)` · `to_png()` · `palette_used()`

### `bbcheck.py`
- `check(path_ou_dict, style=False, tex_override=None)` → `{errors, warnings, infos, report}`
- CLI: `python3 bbcheck.py modelo.bbmodel --style --tex textura.png` (exit 1 se erro)
- Checa uuid/refs, UV, from<to, faces duplicadas, área zero, stretch >1.5×, winding, Java-block, budgets

### `bbglb.py` · `bburl.py` · `bbrender.py`
- `build_glb(baked, name) -> bytes` · `check_glb(data)`
- `build_url(model, nome) -> str` · `verify(url)` (roundtrip)
- `render(model, path, view="iso"|"front"|"side"|"hero", size, supersample=2)` · `render_sheet(model, path)`

---

## 🎨 Estilo "cute cartoon refinado"

- Silhueta legível a **64px**
- Cabeça **35–50%** do corpo (proporção cute)
- **8–20 cores**, cada material com 2–3 tons (base/light/dark) + rim
- Sombra = cor escura saturada (nunca preto puro)
- Densidade de texel ~**2 px/unidade** igual para tudo
- Faces escondidas **omitidas** (`faces=[...]`)
- Sangria de 1px (`bleed`) entre ilhas de UV que se tocam em 3D
- Circunferências pequenas: raio ≥2.4, centro inteiro (`snap=True`)

---

## 📂 Estrutura

```
opencode-blockbench-lowpoly/
├── src/index.ts              # plugin OpenCode v2 (registra a skill)
├── skills/blockbench-lowpoly/ # a skill (SKILL.md + scripts + refs + templates + example)
│   ├── SKILL.md
│   ├── scripts/   (bbmodel, bbtex, bbcheck, bbglb, bburl, bbrender)
│   ├── references/ (spec, pitfalls, estilo, workflow)
│   ├── templates/  (palettes_cute.json, 7 paletas)
│   └── examples/  (mascote_cogumelo end-to-end)
├── package.json
├── LICENSE
└── README.md
```

---

## 🔗 Link do web app — a extensão é obrigatória

```
https://web.blockbench.net/#loadtype=json&loadname=NOME.bbmodel&loaddata=DADOS
```

O web app escolhe o codec pela **extensão** do `loadname`. Sem `.bbmodel`, nenhum codec casa → **"invalid format"**. `bburl.build_url()` já acrescenta a extensão e `bburl.verify()` falha se faltar. **Nunca** monte a URL à mão.

---

## 🏆 Por que este repo merece uma ⭐

- **Determinístico** — seed fixa, uuids determinísticos (`det_uuid`), rebuilds byte-idênticos.
- **Validado** — `bbcheck --style` garante 0 erros/0 avisos antes de entregar.
- **Completo** — geometria + textura + preview + GLB + link em um único script.
- **Zero atrito** — Python puro, sem MCP, sem editor, sem dependências.
- **Compartilhável** — link que abre o modelo direto no web app do Blockbench.
- **Animável** — preserva animações entre rebuilds (`preserve_animations`).

Se este projeto te economizou horas de modelagem manual, **deixe uma star** ⭐ — é o combustível para continuar forjando.

[![Star this repo](https://img.shields.io/github/stars/vpnkkpo-lgtm/opencode-blockbench-lowpoly?style=social)](https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers)

---

## 📖 Referências

- `skills/blockbench-lowpoly/references/bbmodel-spec.md` — spec canônica do formato
- `skills/blockbench-lowpoly/references/pitfalls.md` — catálogo de armadilhas (sintoma → causa → correção)
- `skills/blockbench-lowpoly/references/style-cute-cartoon.md` — direção de arte
- `skills/blockbench-lowpoly/references/blockbench-workflow.md` — testar/editar/exportar

---

## 🤝 Contribuir

Issues e PRs são bem-vindos. Se você forjou um asset legal com este toolkit, abra um PR adicionando-o em `examples/`.

## 📜 Licença

MIT — faça o que quiser, só mantenha o aviso.

---

<p align="center">
  <b>Feito com 💜 para a comunidade OpenCode.</b><br>
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/stargazers">⭐ Star no GitHub</a> ·
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/issues">🐛 Reportar bug</a> ·
  <a href="https://github.com/vpnkkpo-lgtm/opencode-blockbench-lowpoly/fork">🍴 Fork</a>
</p>
