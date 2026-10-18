# Pitfalls — sintoma → causa → correção

Armadilhas reais encontradas construindo esta skill (todas reproduzidas e corrigidas).

## Formato / serialização

1. **`u1 > u2` numa face** — não é bug. O `mirror()` do BB gera UV espelhada de propósito; bbmodel/GLB aceitam. Não "normalize".
2. **Uuid da textura muda a cada `to_dict()`** — causa: uuid gerado na serialização. Correção: fixe `self.texture_uuid = guid()` no `__init__` (serialização determinística; o roundtrip `verify()` depende disso).
3. **`to_dict()` levanta "modelo sem textura"** — cubo com face habilitada e `texture_png=None`. Correção: `attach_texture_bytes(png)` antes de salvar (o BB mostraria rosa/erro).
4. **Face desabilitada com UV real** — referência: face desabilitada deve ser `uv: [0,0,0,0]`, `texture: null`. Se deixar UV válido, o BB "ressuscita" a face ao editar.
5. **Vértice/índice trocado → faces invertidas** — sintoma: buracos escuros no render (backface). Confira tabela + índices em `bbmodel-spec.md`; triângulos exportam `(2,1,0)` e `(3,2,0)`.
6. **Rotação composta errada** — a ordem é **ZYX** (`Rz·Ry·Rx`), rotação em torno do próprio `origin` e DEPOIS dos grupos ancestrais. Não é a ordem "XYZ" do Blender/Maya.

## Loader / iteração

7. **`ValueError: modelo carregado não tem alocador de UV`** — `Model.load()` zera o `alloc` (senão alocaria por cima de UVs existentes). Correção: passe `uv=[...]` explícito em cubos novos, ou `m.reset_alloc()` sabendo que pode sobrepor (resolva pintando por cima).
8. **Grupo sumiu / elemento solto após load** — outliner 4.x (nested) e 5.0 (flat) têm shapes diferentes; refs quebradas são re-anexadas à raiz **com aviso**. Confira o stderr.
9. **Múltiplas texturas no arquivo** — a skill usa só a primeira (aviso em stderr). Se importa com as outras, consolide no BB antes.

## Geometria / UV

10. **Z-fighting em faces coplanares** (ex.: tampa sobre tronco) — use `inflate=0.01..0.05` no menor ou afaste 0.01u.
11. **Borda da textura "puxa" cor da vizinha** — sampler é NEAREST (sem filtro), mas o mip ainda mistura. Correção: `bleed(region, 1)` (sangria 1px de cada lado).
12. **Pinta vazou para a face vizinha** — brushes operam em bbox de região mas pixels das bordas são compartilhados com o padding; sempre deixe `gap ≥ 1` no alocador (padrão) e use `outline_region`/`panel` que respeitam o bbox.
13. **UV stretch** — face quadrada com região retangular (ou vice-versa) distorce. `bbcheck` avisa acima de 1.5×. Regra: a região em px deve ter a mesma proporção da face em unidades × densidade.
14. **Face minúscula some** — `density=2` e face de 0.4u → `max(1, round(...))` colapsa a 1px. Suba a densidade/região ou junte a face.
15. **Mesh com faces não planares / winding errado** — formato `free` espera quads planares CCW vistos de fora. Dobre em tris se a face for torta; `bbcheck` checa planicidade e winding.

## Pixel art / pintura

16. **Pinta virou cruz/losango** — `spot()` com raio ≤2.0 ou centro fracionário. Correção: `snap=True` + raio ≥2.4 (2.4/2.5 → círculo "octógono" 5px; 3.5 → 7px redondo).
17. **Nº de cores estourou (>20 avisos)** — `shade()`/`mix()` gerando tons ad-hoc no meio da pintura. Correção: defina constantes exatas (6–8 cores) e pinte só com elas.
18. **Imagem renderizada escura demais** — uma luz só + ambient baixo. Correção: `ambient=0.58, key=0.45, fill=0.18` (2 luzes + ambiente) — o renderizador já tem esse padrão.
19. **Render "esconde" defeito de pixel** — supersample suaviza bordas. Para QC fino, dump ASCII da região:
    ```python
    reg = m.uv_regions()[("chapeu","north")]
    for y in range(int(reg[1]), int(reg[3])):
        print("".join("#" if dec["rgba"][(y*w+x)*4:i:] else "." for ...))
    ```
20. **Faixa de contorno errada** — `panel` pinta linha light no topo e dark embaixo; é o padrão "cima iluminada". `outline_region` fecha a face toda (silhueta de pixel art).

## Ambiente / processo

21. **`/tmp` não gravável no Termux** — qualquer script que precise de temp: `tempfile.gettempdir()` (ou o dir pré-aprovado `/data/data/com.termux/files/usr/tmp/opencode`).
22. **Closure não muda variável de fora** — faltou `nonlocal` (aconteceu no escritor de GLB). Erro silencioso de lógica, não exceção.
23. **`f"...{expr:...}"` com chaves vazias** — `f"sem faces{}"` é erro de sintaxe; rode `python3 script.py` (smoke) após toda edição grande.
24. **Blockbench aberto com o arquivo antigo** — regenere com o editor fechado; o BB não recarrega automático e você salva por cima perdendo mudanças.
25. **URL não abre no web app** — payload com `&` cru (split quebra), ou link > ~1.5M chars. Use `bburl.build_url` (escapa `\u0026` antes do percent-encode) e `verify()` para o roundtrip.
25b. **Link abre e dá "invalid format"** — o web app escolhe o codec pela **extensão do `loadname`** (`js/io/io.js`: `pathToExtension(file.path)` vs `codec.load_filter.extensions`). `loadname=meu_modelo` sem extensão não casa com nenhum codec → `unsupportedFileFormatMessage`. `build_url` já acrescenta `.bbmodel` e `verify` falha se faltar. (Confirmado no fonte do Blockbench; o `format_version` 5.0 e `model_format: "free"` são válidos.)
26. **Nomes duplicados de elementos** — `Model.cube` levanta erro; uuids sozinhos não bastam porque o outliner e o BB usam nomes na UI.
27. **Animações somem no rebuild** — `to_dict()` grava `m.animations`; se o build reconstrói o modelo do zero sem reler o arquivo anterior, tudo é apagado em silêncio (sem erro do bbcheck). Sintoma: modelo funcionava, rodou `build.py`, e a animação sumiu. Correção: snapshot do JSON anterior + `bbmodel.preserve_animations(prev, m)`.
28. **Animações órfãs depois de renomear osso** — `animations[].animators` é indexado por **UUID do grupo**. `preserve_animations` remapeia por nome e descarta ossos inexistentes (avisa no stderr). Por isso os uuids do `Model` são determinísticos (`det_uuid`): mesmo nome → mesmo UUID entre builds.

27. **Detalhe sub-texel** — peça de 0.25u em `density=2` vira 1px de UV e o `bbcheck` acusa stretch + densidade inconsistente. Correção: detalhe ≥1 texel (0.5u@2, 0.33u@3) ou textura maior.
28. **"Textura cheia" ao criar detalhe** — `ValueError: textura cheia ao alocar` = UV estourou, não é bug do toolkit. Suba `tex_w/tex_h` (256 p/ muito detalhe) ou corte faces escondidas do detalhe.
29. **Malha com winding para dentro** — em mesh, ordem CCW tem que apontar para fora; `bbkit` já ordena/orienta as formas (`_poly`), mas se você escrever mesh na mão, use `--detail`/erro `winding virado para DENTRO` como aviso e reverta os índices.
30. **Modelo "ok mas genérico"** — sintoma: 3/7 cubos, tudo alinhado aos eixos, sem peça pequena. É falta de micro-detalhe, não de textura: use `bbkit.on_face`/`grid_of` + `bevel_box` e rode `bbcheck --detail`.

## Orçamentos (bbcheck)

- Prop: >800 tris = info; personagem: >3000 = aviso. Densidade de texel: variação >1.6× = aviso.
- Preto `#000000`/branco `#ffffff` puros = **erro** de estilo. Magenta `#ff00ff` = aviso (cor-chave de debug/placeholder).
