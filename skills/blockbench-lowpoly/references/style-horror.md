# Guia de estilo — terror / horror low poly

Premissa técnica: o render (`bbrender`) e o GLB usam **luz neutra** e textura NEAREST — todo o clima de terror vem da **TEXTURA pintada** e da **silhueta**. Não conte com iluminação de cena.

## 1. Silhueta do "errado"

- Proporção desconfortável DE PROPÓSITO: braço fino longo demais, tronco estreito, cabeça inclinada, um ombro maior que o outro.
- Assimetria real: um olho dessincronizado (tamanhos diferentes), boca rasgada de um só lado, orelha faltando.
- Rasgos = entalhes de 1px na BORDA da silhueta (na face frontal, pixels de fundo transparente), nunca no meio da face.
- Nada de roundness fofo: cantos retos, arestas aparentes. Se lê como "ameaça" a 64px, está certo.

## 2. Paleta (terror)

- Dessaturada + **1–2 acentos de alta carga**: sangue `#7d2f33`, bile `#c2cf4e`, bioluz `#58e0c8`.
- O "preto" do terror é **molhado**: `#120d14`, `#0e1b26` — nunca `#000000` (o lint reprova, e morte chapada lê barata).
- Pele: pálida/morta (verde-acinzentada, cinza-rosado), nunca tom saudável.
- Paletas prontas: `templates/palettes_horror.json` (`zumbi`, `vampiro`, `abissal`, `espectral`, `gosma`).

## 3. Superfície: sujeira, umidade, podridão

- **SEM `panel` limpo.** A luz é suja: `dither` + `spot` de tons `dark`/`accent` espalhados irregularmente por cima da base.
- Umidade = manchas escuras grandes de bordas irregulares (`dither` denso, 40–60%) + 1px claro no topo de cada mancha (brilho de coisa úmida).
- Manchas de sangue: `spot(r≥2.4, snap=True)` vermelho-escuro + **gotejamento**: `line_v` de 2–4px descendo da mancha, com `set` avulso nas pontas.
- Podridão: 2–3 pintas com o tom `accent` + borda `outline` (buraco/ferida lê melhor com contraste interno).
- Rim invertido (opcional): em vez da linha light no topo (`panel`), pinte a linha light na BASE — luz vinda do chão (fogueira, abismo). É uma inversão barata e poderosa.

## 4. Rosto

- Órbita vazia: socket = bloco `outline` 3×3 com **1 único pixel `glow`** assimétrico dentro. Olhos com tamanhos diferentes (ex.: 2×2 e 3×3).
- Boca: grande demais para a cabeça, dentes = `dots(step=2)` de 1px do tom `light` (osso).
- **Sem blush.** Sem sorriso. `mouth_o` com o dobro da largura lê como grito.
- Um detalhe só de estranheza: pescoço fino demais, costura na cara, segundo par de olhos menores.

## 5. Detalhes (kit do horror)

| efeito | receita |
|--------|---------|
| costura | `line_h` + `dots(step=2)` de 1px cruzando a linha |
| bandagem | `hstripes` 2 tons claros + 1px `outline` entre voltas |
| osso exposto | mancha `#cfc3a0` com `outline` em volta + 1px `light` no topo |
| gotejamento | `spot` + `line_v` descendente com falhas (pixels isolados) |
| olho brilhante | socket escuro + 1px `glow`; NUNCA sombrinha/faísca cute |

## 6. Orçamento e QC

- Orçamento: mob de terror até 3000 tris; assimetria vale mais que detalhe.
- QC obrigatório: `bbrender` e **olhar** — o teste é "isso me ameaça?" a 64px. Se ficou goofy (boca simétrica grande + olhos redondos centrados = fofo, não assustador), quebre a simetria.
- `bbcheck --style`: 0 erros (preto/branco puro = reprovado) e paleta ≤20.

## 7. Não faça

- Gore pixel-perfect: em 128px vira ruído. Sugira, não desenhe tudo.
- Contorno cute uniforme: aqui o outline é sujo e quebrado (falhas de 1px são bem-vindas).
- Iluminação "certa": o horror usa luz errada de propósito (de baixo, de trás).

Outros estilos da skill: `style-cute-cartoon.md`, `style-dark.md`, `style-realistic.md` — mesmo pipeline, outra silhueta/pintura.
