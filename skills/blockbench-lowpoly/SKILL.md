---
name: blockbench-lowpoly
description: Toolkit Python puro (sem MCP, sem dependências) para autorar assets 3D low poly por código em diversos estilos de arte (cute cartoon, terror/horror, sombrio/dark fantasy, realista, etc) — gera .bbmodel (JSON), pinta a textura via Canvas, valida (bbcheck), renderiza previews PNG (bbrender), exporta GLB (bbglb), monta o link do web app Blockbench (bburl) e gera card de divulgação multi-tema (bbcard). Use ao criar personagens, props, mobs, ícones 3D, dioramas, armas, veículos ou qualquer modelo para Blockbench/glTF sem abrir o editor. Gatilhos: blockbench, bbmodel, glb pixel art, asset 3D procedural, card de divulgação, vitrine de asset.
---

# Blockbench LowPoly — Gênese Procedural de Assets Low Poly (multi-estilo)

Toolkit 100% Python puro para o agente **autorar assets 3D low poly por código** — em qualquer estilo de arte (cute, terror, sombrio, realista...) — e entregar em 4 formatos: `.bbmodel` (projeto nativo Blockbench), `.glb` (motor/engine), PNGs de preview e um link que abre o modelo direto no web app Blockbench. Zero dependências externas, zero MCP, zero editor.

> **Escolha o estilo ANTES de modelar.** Cada estilo tem guia próprio em `references/style-*.md` (proporções, paleta, superfície, QC). O pipeline é o mesmo para todos; o que muda é silhueta + pintura. O clima vem SEMPRE da textura pintada (render/GLB usam luz neutra).

## Estrutura

```
scripts/bbmodel.py   builder: Model/Group/Cube/Mesh, UV, mirror, bake, load/save
scripts/bbkit.py     fidelidade: formas (bevel/taper/wedge/pyramid/cylinder/sphere), detalhe por FACE (on_face/grid_of/edge_trim), simetria e pós-edição
scripts/bbtex.py     PNG puro (encode/decode) + Canvas de pintura cartoon
scripts/bbcheck.py   validador (geometria, UV, outliner, estilo, fidelidade, budgets)
scripts/bbglb.py     exportador GLB (glTF 2.0 binário, textura embutida)
scripts/bburl.py     link do web app Blockbench + roundtrip de verificação
scripts/bbrender.py  rasterizador software: previews ortho/iso/hero
scripts/bbcard.py    card de divulgação (vibe loja, multi-tema) a partir do .bbmodel
templates/palettes_cute.json      7 paletas cute (roles: outline/base/light/dark/accent/blush/shadow)
templates/palettes_horror.json    5 paletas terror (roles: .../accent/glow/shadow)
templates/palettes_dark.json      4 paletas sombrias (roles: .../accent/metal/shadow)
templates/palettes_realistic.json 5 paletas realistas (roles: .../accent/shadow, sem contorno)
references/           spec do formato, pitfalls, workflow + guias de estilo (cute, terror, sombrio, realista)
examples/mascote_cogumelo/build.py  exemplo DIDÁTICO da ESTRUTURA do pipeline — leia para entender e crie o seu do zero (não é base p/ copiar/retexturar)
```

## Quickstart

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.config/opencode/skills/blockbench-lowpoly/scripts"))
from bbmodel import Model
import bbtex, bbcheck, bbrender, bburl

m = Model("cogumelo", tex_w=128, tex_h=128, density=2)   # density = px por unidade
corpo = m.group("corpo", origin=(8, 0, 8))
m.cube("tronco", (5, 0, 5), (11, 8, 11), group=corpo,
       faces=["north","east","south","west"])            # up/down omitidos = econômicos

c = bbtex.Canvas.for_model(m)
c.panel(m.uv_regions()[("tronco","north")], "#f6ddb8", light="#fdefd6", dark="#e8c894")
png = c.to_png()
m.attach_texture_bytes(png)

rep = bbcheck.check(m.to_dict(), style=True, tex_override=png)  # E/W/I + lint de estilo
bbrender.render_sheet(m, "preview.png", size=384)
m.save("asset.bbmodel")
with open("asset.glb","wb") as f: f.write(__import__("bbglb").build_glb(m.bake(), "asset"))
open("link.txt","w").write(bburl.build_url(m, "asset"))
```

## Fluxo de trabalho recomendado

1. **Planeje no papel**: silhueta legível a 64px, proporções (cabeça 35–50% em "cute"), orçamento de tris (prop ≤800, personagem ≤3000).
2. **Estilo, paleta e referência** — guia em `references/style-<estilo>.md`, paletas em `templates/palettes_<estilo>.json` (`bbtex.load_palette`). Se houver referência (imagem), LEIA com a tool `read` e traduza antes de modelar: `references/detail-and-manipulation.md` seção 0 tem a tabela "o que você vê → qual chamada de bbkit". NUNCA #000000/#ffffff puros (reprova em QUALQUER estilo).
3. **Construa a geometria em 3 escalas** — macro (silhueta) com `Model.cube`, meso (massas que quebram o bloco) e **micro (detalhe ≤25% da escala)**. `Model.cube` sozinho dá blockout: use `bbkit` — `bevel_box`/`taper_box`/`wedge`/`cylinder`/`sphere` nas peças de silhueta e `on_face`/`grid_of`/`edge_trim` para detalhe pequeno apoiado na face de outra peça (nunca adivinhe coordenada). `from < to` sempre; pivô (`origin`) na junta quando fizer parte de rig. Guia: `references/detail-and-manipulation.md`.
4. **Pinte a textura** com o Canvas usando `uv_regions()` como mapa. Use `panel()` nas faces, `outline_region()` para contorno, `eyes/blush/mouth_smile` p/ a cara, `spot(snap=True)` p/ pintas.
5. **Valide**: `bbcheck.check(d, style=True, detail=True, tex_override=png)` — persiga 0 erros e 0 avisos. O `--detail` mede fidelidade (peça fina, rotação, bevel).
6. **Preview e QC visual**: `bbrender.render_sheet` + `render(..., view="hero")` e LEIA os PNGs (mas confira pixels críticos em ASCII: render suaviza e esconde defeito de pixel art).
7. **Entregue**: save `.bbmodel`, `bbglb.build_glb`, `bburl.build_url` → `link.txt`. Itere rodando o build de novo (tudo é determinístico).
8. **Card de divulgação** (opcional, se pedirem vitrine/preço): `python3 scripts/bbcard.py --model asset.bbmodel --preview preview.png --theme <vibe> --desc "..." --out card.png [--price "R$ 19,90"]`. O `--model` puxa nome e stats sozinho; o tema só muda o visual.
9. **Se o modelo é animado**: chame `bbmodel.preserve_animations(prev, m)` antes do save (seção "Animações").

## API essencial

### bbmodel.py
- `Model(name, tex_w, tex_h, density=2, format="free")` — textura e resolução.
- `m.group(name, origin, rotation=(0,0,0), color=None, parent=None)`
- `m.cube(name, frm, to, group, origin=None, rotation=None, inflate=0.0, mirror_uv=False, faces=None, uv=None)` — `faces` = subconjunto das 6 direções; `uv=None` auto-aloca por face; dict por face p/ manual.
- `m.mesh(name, vertices, faces, group, uv="planar")` — só `free`; faces CCW vistas de fora; quads planares.
- `Cube.mirror(axis, center)` / `Mesh.mirror(axis, center)` — espelha DO cubo para o centro (axis 0/1/2 = X/Y/Z).
- `m.uv_regions()` — `{(elemento, face): [u1,v1,u2,v2]}` para pintar.
- `m.bake()` — tris em espaço mundo com UV por canto (usado por GLB/render).
- `m.stats()` — elements/groups/tris/uv_regions/tex_used_pct.
- `m.save(path)`, `Model.load(path)`, `m.reset_alloc()` (só p/ carregados; ver pitfalls).
- `m.validate(style=False, detail=False, tipo="padrao")` — roda bbcheck em memória.
- `m.animations` — lista de dicts de animação no formato do BB; `to_dict()` já emite (não zera).
- `m.animation(name, loop="loop", length=1.0)` — cria/retorna animação.
- `m.keyframe(anim, bone, channel, time, value)` — adiciona keyframe.
- `bbmodel.preserve_animations(prev, m)` — **obrigatório em rebuild de modelo animado** (ver seção abaixo).
- `m.locator(name, origin, parent, rotation)` — ponto de attach/efeito (grupo vazio).
- `bbmodel.det_uuid(kind, name)` — uuid determinístico (uuid5); é o que mantém ossos estáveis entre builds.

### bbkit.py — fidelidade + manipulação direta
- Formas (viram Mesh): `bevel_box(frm,to,bevel=0.2)` (mata o ar de caixote), `taper_box(shrink,offset)`, `wedge(axis=0|2)`, `pyramid(apex)`, `cylinder(center,radius,height,sides=8,axis)`, `sphere(center,radius,rings,sides)`.
- Detalhe por face: `on_face(m, name, parent, face, cu, cv, du, dv, depth, sink, grid)`; `grid_of(m, prefix, parent, face, nu, nv, ...)` (rebites/dentes); `edge_trim(m, prefix, parent, face, thickness, sides)` (frisos/aros). Bases u/v por face em `bbkit.FACE_BASIS`. Detalhe nunca menor que 1 texel; faces laterais vêm desligadas por default.
- Simetria/cópias: `duplicate(m, name, new, offset)`, `mirror_group(m, [nomes], axis, center)`, `Cube.mirror`, `Mesh.mirror`.
- Pós-edição: `find/bounds/translate/resize/set_extent/set_origin/rotate/remove/snap`.
- Guia completo + regras de densidade: `references/detail-and-manipulation.md`.

### bbtex.py
- `Canvas.for_model(m)`, `encode_png`/`decode_png`, `col/hexof/shade/mix/load_palette`.
- Escrita: `set/rect/line_h/line_v/ellipse/fill_region`.
- Regiões: `region_bbox/fill_region/panel(base,light,dark)/ao/outline_region/hstripes/vstripes/dots/checker/dither`.
- Cara: `eyes(eye_color, spark_color, size, gap, y_frac)/blush/mouth_smile/mouth_o`.
- Pintas: `spot(region, cx_frac, cy_frac, r, snap=True)` — use `snap=True` e r≥2.4 (senão vira losango/cruz), `spots()` para lote.
- Finalização: `bleed(region, px=1)` (sangra borda 1px nas junções), `to_png(indexed=None)`, `palette_used()`.

### bbcheck.py
- `bbcheck.check(path_ou_dict, style=False, tex_override=None) -> dict(errors/warnings/infos/report)`.
- CLI: `python3 bbcheck.py modelo.bbmodel [--style] [--tex textura.png]` (exit 1 se houver erro).
- Checa: uuid/refs do outliner, texture index, UV dentro dos bounds, from<to, faces duplicadas, área zero, stretch >1.5×, planicidade/winding de mesh, Java-block −16..32, budgets de tris.
- `--style`: preto/branco puro = ERRO; magenta = aviso; paleta >20 = aviso; densidade de texel com variação >1.6× = aviso.
- `--detail` (fidelidade): peça fina ausente (>8% da maior dimensão), tudo alinhado aos eixos, nenhuma forma com bevel/taper.
- Checa também: UV overlap (info), z-fighting/coplanar (info), `--json` para CI, `--fix` para corrigir preto/branco puros.

### bbglb.py / bburl.py / bbrender.py
- `bbrender.render(model_ou_baked, path, view="iso"|"front"|"side"|"hero"|..., size, supersample=2, outline=False)`; `bbrender.render_sheet(model, path)` = front+iso+side.
- `bbglb.build_glb(baked, name) -> bytes` (indexado, KHR_materials_unlit, sampler NEAREST, CLAMP); `bbglb.check_glb(data)`; CLI `--export modelo.bbmodel saida.glb`.
- `bburl.build_url(model, nome) -> str`; `bburl.verify(url)` roundtrip; CLI `--out link.txt --verify`.

### bbcard.py — card de divulgação (vibe "quero isso no meu jogo")
- `python3 bbcard.py --model asset.bbmodel --preview preview.png --theme casual --desc "..." --out card.png`
- `--model` lê o `.bbmodel` e preenche **nome + stats automáticos** (polígonos, textura, formato, elementos). `--info` explícito tem prioridade e entra depois.
- `--theme` só muda o **visual** (paleta, fundo, decoração); textos são padrão em todos: `casual | horror | dark_fantasy | sci_fi | natureza | royal`.
- `--preview` = PNG do `bbrender.render(..., view="hero")`. Sem preview cai num placeholder circular.
- `--price "R$ 19,90" [--old-price "R$ 39,90"]` → etiqueta de preço no lugar do selo grátis + CTA vira "COMPRAR AGORA".
- `--badge` / `--cta` sobrepõem os textos padrão de selo e botão.
- Uso programático: `import bbcard` e monte o canvas chamando `hero_panel/title_block/checklist/stat_bar/cta_button/seal/price_tag`; temas em `bbcard.THEMES`.
- O preview do card vem do `bbrender.render_sheet`/`render` — rode o render antes do card.

## Animações — preservar no rebuild (NÃO pule)

Modelos animados às vezes são authoring por script e depois animados por tool
externa (ex.: `bbanim_*`), que grava `animations` direto no `.bbmodel`. O script
`build.py` reconstrói o modelo do zero, então **sem os 3 passos abaixo toda
animação é apagada silenciosamente**.

1. **Snapshot** do arquivo anterior no início do `main()`:
   ```python
   prev = None
   if os.path.exists(bb_path):
       prev = json.load(open(bb_path, encoding="utf-8"))
   ```
2. **Construa** o modelo novo normalmente (`m = build()`).
3. **Religue** as animações por NOME de osso, antes de `save`/`build_url`:
   ```python
   if prev and prev.get("animations"):
       bbmodel.preserve_animations(prev, m)
   ```

Por que funciona: `animations[].animators` é indexado pelo **UUID do osso**, e o
build reconstrói a hierarquia. Como `Model` usa **uuid determinístico**
(`det_uuid`, derivado do nome), ossos de mesmo nome mantêm o mesmo UUID — e o
`preserve_animations` ainda remapeia por nome e descarta ossos que sumiram
(avisa no stderr). Efeito colateral bom: build vira byte-idêntico entre execuções.

`preserve_animations` aceita dict, caminho `.bbmodel` ou `Model` carregado.

## Link do web app — a extensão é obrigatória

```
https://web.blockbench.net/#loadtype=json&loadname=NOME.bbmodel&loaddata=DADOS
```

O web app escolhe o codec pela **extensão do `loadname`** (`js/io/io.js`:
`pathToExtension(file.path)` contra `codec.load_filter.extensions`). Sem
`.bbmodel` no `loadname`, nenhum codec casa e o app mostra **"invalid format"**
(`unsupportedFileFormatMessage`). `bburl.build_url()` já acrescenta a extensão e
`bburl.verify()` falha se ela faltar — então nunca gere a URL à mão.

O `verify()` reproduz o parser real do app (`js/web.ts`): um `decodeURIComponent`
no hash inteiro, `split('&')` e `re.split(r'=\s*(.+)')` por campo.

## Regras de ouro

1. `from < to` em todo cubo; pivô na junta quando rigado.
2. Nunca preto/branco puro — sombra é cor escura saturada da paleta.
3. Alvo 8–20 cores; cada material com 2–3 tons (base/light/dark) + rim.
4. Densidade de texel (~2 px/unidade) igual para todos os elementos.
5. Faces escondidas OMITIDAS (`faces=[...]`) — economia de tris e UV.
6. Sangria de 1px (`bleed`) entre ilhas de UV que se tocam em 3D.
7. Circunferências pequenas: raio ≥2.4 e centro inteiro (`snap=True`).
8. Sempre rodar `bbcheck --style` e LER os previews antes de entregar.
9. Modelo determinístico: seed fixa, mesmas cores → mesmo byte output. Uuids já são determinísticos (`det_uuid`), então rebuilds são byte-idênticos.
10. **Modelo animado**: preserve as animações no rebuild (snapshot + `preserve_animations`) — sem isso elas somem sem erro.
11. **Link do web app**: sempre via `bburl.build_url` (ele garante o `.bbmodel` no `loadname`); URL montada à mão abre "invalid format".
12. **Todo asset tem 3 escalas**: macro, meso e micro (peça ≤20% da maior dimensão em mob, 15% em veículo). Sem micro, o modelo lê como blockout — rode `bbcheck --detail --type <tipo>` e persiga 0 avisos.

## Estilos de arte

| Estilo | Guia | Paletas | Assinatura |
|--------|------|---------|------------|
| Cute cartoon | `references/style-cute-cartoon.md` | `palettes_cute.json` | fofo, chapado, contorno 1px, blush |
| Terror / horror | `references/style-horror.md` | `palettes_horror.json` | orgânico, doente, assimétrico, rim invertido |
| Sombrio / dark fantasy | `references/style-dark.md` | `palettes_dark.json` | pesado, desgastado, contraste alto + 1 acento quente |
| Realista | `references/style-realistic.md` | `palettes_realistic.json` | proporção natural, luz direcional pintada, SEM contorno |

- O pipeline (geometria → UV → pintura → `bbcheck` → GLB → preview → link) é idêntico em todos os estilos; muda a silhueta + a pintura.
- Regras transversais valem sempre: preto/branco puro reprovam no `--style`, alvo 8–20 cores, densidade ~2 px/unidade, faces escondidas omitidas.
- **Estilo novo?** Copie a estrutura de um guia existente (silhueta → paleta → superfície → detalhes → QC) e crie `templates/palettes_<estilo>.json` — o resto do toolkit não muda.

## Referências

- `references/bbmodel-spec.md` — fatos canônicos do formato (vértices, winding, UV, rotação, outliner, GLB, URL).
- `references/detail-and-manipulation.md` — **comece por aqui se o modelo está "ok mas genérico"**: 3 escalas, bevel, detalhe por face, simetria, pós-edição, QC de fidelidade.
- `references/pitfalls.md` — catálogo de armadilhas (com sintoma → causa → correção).
- `references/style-cute-cartoon.md` — direção de arte cute: proporções, paleta, luz, leitura em 64px.
- `references/style-horror.md` — direção de arte terror/horror: sujeira, assimetria, umidade.
- `references/style-dark.md` — direção de arte sombria/dark fantasy: peso, desgaste, acento quente.
- `references/style-realistic.md` — direção de arte realista: proporção, luz direcional, zero contorno.
- `references/blockbench-workflow.md` — testar/editar no Blockbench, exportar para engines, limites do web app.
