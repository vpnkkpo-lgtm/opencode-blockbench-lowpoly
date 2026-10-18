# Guia de estilo — "realista" em low poly

Premissa técnica: o render/GLB usa luz neutra; o realismo aqui NÃO vem de textura detalhada nem de iluminação de cena — vem de **proporção natural + luz direcional pintada na textura + ausência de contorno**. É "realismo de valor", não de detalhe.

## 1. Proporção natural

- Use referência real como contrato: humano ~7–7,5 cabeças; animal com anatomia correta (ombros/cernelha, quadril, cauda); props com medidas de verdade (cadeira ~1u de assento? escale tudo na mesma unidade de modelagem).
- Nada de chibi: olhos pequenos (1–2px), cabeça proporcional, membros com juntas nos lugares certos.
- Silhueta: o teste muda — aqui ela deve ler como "o objeto real", não como ícone. Detalhe fino pode ficar para a textura.

## 2. Luz direcional pintada (o coração do estilo)

- Escolha UMA direção de luz global (ex.: cima-esquerda-frente) e **respeite em todo o modelo**, em todas as peças.
- Pinte cada face por orientação:
  - `up` → tom `light`
  - `down` → tom `dark`
  - norte/sul → `base`
  - leste/oeste → entre `base` e `light`/`dark` conforme o lado da luz
- Faces opostas NUNCA com o mesmo valor. É isso que faz o olho ler volume em low poly.
- `panel` só com 2 tons aqui (a linha light em cima, dark embaixo) — ou nem isso: `fill_region` + ajuste por face.

## 3. Paleta (realista)

- Naturais e dessaturadas: terra, oliva, ardósia, areia, couro, palha. Verde de folha é `#55703c`, não `#00ff00`.
- Passos de **VALOR** > passos de matiz: os 3 tons do material variam claro/escuro, não mudam de cor.
- 12–20 cores; `accent` = 2º material (madeira numa pedra, ferrugem num ferro, flor num campo).
- Paletas prontas: `templates/palettes_realistic.json` (`floresta`, `rocha`, `couro`, `ferro`, `campo`).

## 4. SEM contorno

- Outline de 1px é linguagem cartoon — o realista **não usa**. Separe peças por valor (peça escura contra peça clara) e por AO.
- `ao` importa mais que nunca: 1–2px na base e no lado não iluminado de cada região que encosta em outra.

## 5. Texturas de material (receitas)

| material | receita |
|----------|---------|
| madeira | `hstripes` irregulares (2 tons, quebre o padrão com `set`) + 1–2 nós (`dots` 1px `dark`) |
| pedra | `dither` 20–30% entre base/dark + 2–3 rachaduras de 1px |
| metal | bandas: 1px `light` no topo, `base` no corpo, 1–2px `dark` na base; risco curto `light` |
| tecido | `vstripes` 2 tons (dobra) + `ao` na barra |
| pele/couro | base lisa + `dither` leve (15%) nas juntas/sombras |
| sujeira | `dither` do `shadow` concentrado nas BASES (pés, rodapé) e cantos internos |

- Detalhe (tábua, tijolo, veio) no MÁXIMO 25% da área — realismo de low poly é valor, não ruído.

## 6. Orçamento e QC

- Props realistas: até 800 tris; personagens até 3000.
- QC do squint test (aperte os olhos/veja a 48px): lê como o objeto real? Se "flutua ou brilha errado", a luz direcional está inconsistente entre as faces/peças — reconserte a direção primeiro.
- Densidade de texel: mantenha ~2 px/unidade como sempre; texel density variável denuncia a mão do artista, não o material.
- `bbcheck --style`: preto/branco puro = erro; use `#26282c` e `#e8e4dc` como extremos.

## 7. Não faça

- Contorno: reprovado no estilo.
- Gradiente/airbrush: este toolkit é chapado (pixels duros); volume vem de face + AO.
- Textura "fotográfica": mancha irregular em excesso vira sujeira em 64px. Valor limpo + 1–2 detalhes certeiros.

Outros estilos da skill: `style-cute-cartoon.md`, `style-horror.md`, `style-dark.md` — mesmo pipeline, outra silhueta/pintura.
