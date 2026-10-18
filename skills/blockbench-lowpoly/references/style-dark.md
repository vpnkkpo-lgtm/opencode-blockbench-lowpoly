# Guia de estilo — sombrio / dark fantasy (grimdark)

Premissa técnica: luz neutra no render/GLB — o clima **bleak** vem da textura: valores escuros, contraste alto, desgaste pintado. Não é terror (orgânico/doente); aqui é **solene, pesado, corroído**.

## 1. Silhueta pesada

- Massa e peso: ombros/ombreiras LARGOS (mais que a cintura), elmo/capuz, babeira/capa como bloco retangular atrás, botas largas.
- Proporção 4–6 cabeças (heroica-monstruosa, não chibi). Postura estática, frontal, imponente.
- Camadas: ombreira sobre braço, cinto sobre manto, capa quebra a silhueta atrás. 2–3 massas, sem detalhe fino.

## 2. Paleta (sombrio)

- Base: charcoal `#3e4450`, ferro `#4a4e59`, couro velho, manto vinho/roxo. Tudo **dessaturado**.
- Contraste ALTO: sombra quase preta (`#14161c`, nunca `#000000`) contra `metal` claro. Meio-tons somem; pule direto do dark pro light.
- **1 acento quente por peça** — brasa `#d87a2a`, runa `#4ec8a0`, sangue seco `#8a3a2e` — é o que dá "vida" no meio do blefe.
- Paletas prontas: `templates/palettes_dark.json` (`cavaleiro`, `necromante`, `forja`, `pantano`).

## 3. Superfície: desgaste e corrosão

- `panel` com 2 tons (light/dark) funciona — mas **assimétrico**: risque com `set` avulso as linhas do panel (falha de 1px) para não parecer novo.
- Quinas superiores: risco de 1px `light` curto (2–3px) nas arestas expostas. É o "metal raspado".
- Base das peças (bainha do manto, solas, saia da armadura): 1–2px de `dither` do tom `shadow` — sujeira de chão.
- Metal: separação DURA por face — topo `light`/`metal`, lateral `base`, fundo `dark`. Sem gradiente; 1px de transição no máximo.
- Tecido: `vstripes` 2 tons (dobras verticais) + `ao` em baixo. Corrente/anel: `dots(step=2)` em coluna.

## 4. Detalhes (kit do grimdark)

| efeito | receita |
|--------|---------|
| rebite | 1 pixel `metal` claro + 1px `outline` abaixo |
| camadas de placa | linha `outline` 1px entre placas + `light` no topo de cada |
| runa | 2–4px do `accent` em forma de risco (L, T, X) — só 1 por peça |
| olho sob elmo | faixa `outline` 1px + 1 pixel `accent`/`glow` |
| emblema | bloco 2×2 do acento com 1px outline; sem simetria perfeita |

## 5. Cara / expressão

- Elmo fechado é o padrão (mais sombrio, menos trabalho). Se tiver rosto: pele pálida dessaturada, olhos = 1px `glow` frio, sem boca (ou linha reta de 1px).
- Cicatriz: `line_v` de 2–3px `dark` com falha no meio.
- Nunca blush, nunca faísca no olho.

## 6. Orçamento e QC

- Até 3000 tris; forma > detalhe. Se o preview virar "borrão cinza", o contraste entre blocos está baixo — suba o `metal`/`accent`.
- QC: valor médio ESCURO é o objetivo, mas todo bloco precisa de 2 valores distintos (200–300% de diferença de luminância entre topo e fundo).
- `bbcheck --style`: preto/branco puro = erro; `#14161c`/`#e8e4dc` são os extremos seguros.

## 7. Não faça

- Dessaturar tudo POR IGUAL: sem o acento quente, o modelo vira sujeira ilegível.
- Contorno cute: aqui o outline é a "fumaça" — escuro mas NÃO preto, e pode ter falhas.
- Detalhe fino em área escura: em 64px não sobrevive. Massa e contraste, só.

Outros estilos da skill: `style-cute-cartoon.md`, `style-horror.md`, `style-realistic.md` — mesmo pipeline, outra silhueta/pintura.
