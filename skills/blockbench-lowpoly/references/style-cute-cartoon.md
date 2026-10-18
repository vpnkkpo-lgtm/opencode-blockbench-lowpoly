# Guia de estilo — cute cartoon low poly

Direção de arte aplicada pelo exemplo `mascote_cogumelo`. O objetivo: leitura instantânea, fofo, "feito à mão" — não minimalismo frio.

## 1. Silhueta primeiro (teste dos 64px)

- Renderize a 64px mentalmente (ou de verdade, `size=64` no bbrender): se não dá pra dizer O QUE é, refaça as proporções antes de detalhar.
- Formas-base: cubos empilhados com cantos suaves de leitura (chapéu largo, corpo bojudo). Assimetria leve é permitida em acessórios, nunca no eixo corpo/cabeça.
- Detalhes pendurados para fora da silhueta (orelha, asa, chapéu) — máximo 2 elementos.

## 2. Proporções cute

- **Cabeça 35–50% da altura total.** Exemplo: tronco 8u + chapéu 5u em 15u → cabeça (chapéu) ~33–40%.
- Corpo curto e bojudo; pernas/pés **stubbies** (1–3u), muitas vezes só "pés" sem perna separada.
- Braços curtos colados ao corpo (2–3u), com 1u de "mão" mais clara.
- Olhos abaixo do meio da face (y_frac 0.28–0.45) — espaço de testa grande = infância/fofura.

## 3. Paleta

- 8–20 cores no modelo TODO (texels não-transparentes). Cada material: **3 tons** (base/light/dark) + contorno.
- NUNCA #000/#fff puros. Contorno = versão escura e saturada da base (ex.: contorno do chapéu vermelho = vinho `#a83a4a`, não preto).
- `shade(c, amt)` da bbtex: luz aquece (+R), sombra esfria (+B) — regra clássica de pixel art.
- Paletas prontas: `templates/palettes_cute.json` → `load_palette(path, "cogumelo")` etc.
- Outros estilos da skill: `style-horror.md`, `style-dark.md`, `style-realistic.md` — mesmo pipeline, outra silhueta/pintura.
- Cores-assinatura: um acento vivo (blush rosa, detalhe amarelo) dá vida; use em 1–2 lugares só.

## 4. Superfície e iluminação pintada

- Toda face grande recebe `panel(region, base, light, dark)`: linha light em cima, linha dark embaixo — simula luz de cima SEM depender do render.
- `ao(region, cor, edges="bl")`: 1px de oclusão no canto inferior/interno (onde encosta em outra peça).
- `outline_region`: contorno 1px na face = leitura de pixel art chapada. Use nas faces "de frente" (rosto, chapéu).
- Rim light: a linha light do panel JÁ é o rim. Não crie gradientes.

## 5. Rosto (fórmula do exemplo)

Região do rosto (face norte da cabeça, ~12×8u → 24×16px a density 2):

| traço | parâmetro | exemplo |
|-------|-----------|---------|
| olhos | `eyes(eye, spark, size=2, gap=5, y_frac=0.28)` | olho escuro 2px + faísca clara 1px |
| blush | `blush(cor, y_frac=0.5, inset=0, width=3)` | 3×1px rosa suave |
| boca | `mouth_smile(cor, y_frac=0.62, width=4)` | "U" de 5px (pontas cy, meio cy+1) |

- Rosto ocupa ~60% da largura da face, centrado verticalmente entre 0.25–0.75.
- Variações: `mouth_o` (surpresa), olho fechado (1px line_h), sobrancelha ausente = mais fofo.

## 6. Pintas e padrões

- `spot(region, cx, cy, r, cor, snap=True)`: r 2.4–2.5 = círculo 5px; r 3.5 = círculo 7px; r ≥4 fica blocado.
- Distribua 3–5 pintas de 2 tamanhos em posições assimétricas MAS com margem (não encoste no contorno).
- Listras: `hstripes`/`vstripes` com 2 tons da MESMA família (base + light).
- `dither(c1, c2, density)`: transição pontilhada p/ vender textura em área grande, 50% máx.

## 7. Densidade de texel e resolução

- Alvo: **~2 px/unidade** consistente. Face 6×3u → região 12×6px.
- Textura em potência de 2 (64/128/256) dimensionada ao modelo: some a área das faces + gap; 128×128 serviu um mascote de 7 cubos com folga.
- `bbcheck --style` avisa se a variação de densidade passar de 1.6× — respeite.

## 8. QC final (checklist visual)

1. `bbrender.render_sheet` + `render(view="hero")` e **leia os PNGs** (você vê a imagem).
2. Cheque: silhueta, olhos no lugar, boca correta (U, não bigode), blush visível, pintas redondas, sem face preta/branca chapada, sem stretch.
3. Dump ASCII de 1–2 regiões críticas (rosto) quando o pixel exato importa.
4. `bbcheck --style` → 0 E, 0 W. Só então entregue GLB/link.
