# Detalhe fino e manipulação direta — como chegar perto da referência

O gap típico entre "o agente modelou legal" e "está perto da referência" **não é textura nem paleta**: é geometria. Blockout de caixas retas = leitura de blockout, por mais bem pintado que esteja. Este guia é o kit para sair disso.

## 0. Traduzindo a referência (imagem) em chamadas

A referência já está na sua tela/contexto — leia com a tool `read` e passe por esta tabela **antes** de escrever a primeira linha de geometria. Ela é universal: serve para qualquer ref (minecraft, concept art, foto de estátua, asset de outro agente).

| O que você vê na imagem | Como escreve |
|---|---|
| a silhueta tem N "degraus"/massas | uma peça por massa (macro), `Model.cube` com `faces` da silhueta |
| proporção geral (largura/altura) | escolhe a escala: altura ≈ 16u é o padrão Blockbench/Minecraft |
| canto cortado, quina chanfrada, "aresta viva" | `bbkit.bevel_box(..., bevel=0.2..0.5)` NAQUELA peça |
| ponta que afina (chapéu, bico, peitoral, nariz) | `bbkit.taper_box(shrink=...)` ou `bbkit.pyramid` |
| topo arredondado / dome / bolinha | `bbkit.cylinder` ou `bbkit.sphere` |
| rampa, telhado, bico de casco | `bbkit.wedge(axis=0\|2)` |
| rebites, parafusos, dentes, tijolos, botões | `bbkit.grid_of(nu, nv)` na face certa |
| fita/cinto/aro/moldura/banda na borda da peça | `bbkit.edge_trim(sides=("top","bottom"))` |
| fivela, remendo, placa, bolso, placa de peito | `bbkit.on_face(cu, cv, du, dv, depth)` |
| uma peça dos dois lados (2 braços, 2 asas) | `bbkit.mirror_group([...], axis, center)` — 1 linha, simetriagarantida |
| nada disso, só cubos lisos | **falta micro-detalhe**: ~1 detalhe a cada 2–3u de largura da peça maior |
| detalhe só do lado da luz | replica só ali (detalhe é direcional, não simétrico) |

Ordem de trabalho: silhueta → chanfro/ponta → massas médias → detalhe → textura. Pular direto pro detalhe em cima de caixa lisa não fecha o gap.

## 1. As três escalas (regra que decide a fidelidade)

| Escala | Tamanho | O que é | Exemplo |
|---|---|---|---|
| **Macro** | 100% | silhueta, proporção, pose | corpo, cabeça, capa |
| **Meso** | 25–100% | massas que quebram o bloco | ombreira, cintura, aba, rabo |
| **Micro** | ≤25% | detalhe que só aparece de perto | rebite, friso, botão, dente, cinto, fivela |

Regra do `bbcheck --detail --type mob`: micro = peça com aresta ≤**20%** da maior dimensão (prop: 30%, veículo: 15%). Se a menor peça do modelo passa disso, **não existe micro** — é o aviso mais importante do lint. Um herói de 16u de altura precisa de peças de ~0.5–3u para ler.

## 2. Truque nº1: mate o "caixote" com bevel

`bbkit.bevel_box(frm, to, bevel)` corta as 12 arestas a 45° (6 octógonos + 12 quads + 8 tris). Um único elemento, silhueta com vida, luz pegando os cantos. `taper_box` (topo menor/offset), `wedge` (rampa), `pyramid`, `cylinder`, `sphere` completam o vocabulário de formas.

Regra prática: **bevella as peças que ficam na silhueta** (ombro, tampa, capacete, base), deixe caixas cruas no que fica escondido.

## 3. Detalhe pequeno: placement por FACE

Adivinhar coordenadas de um rebite é onde os agentes travam. Use a face como referência:

```python
bbkit.on_face(m, "fivela", "cinto", "north", cu=0.5, cv=0.5, du=0.25, dv=0.18, depth=0.12, group=g)
bbkit.grid_of(m, "rebite", "placa", "north", nu=3, nv=2, du=0.2, dv=0.2, group=g)   # 6 rebites
bbkit.edge_trim(m, "aro", "porta", "up", thickness=0.15, group=g, sides=("top","bottom"))
```

- `cu/cv` = fração 0..1 na face; `du/dv` = tamanho em fração; `depth` = quanto avança para fora; `sink` = penetração (evita z-fight).
- Bases por face: `north/south` u→±X, v→+Y; `east/west` u→∓Z, v→+Y; `up` u→+X, v→−Z; `down` u→+X, v→+Z.
- Por default o detalhe só gera **a face de apoio + topo** (economiza UV e tris — faces laterais de um rebite de 0.25u são lixo). Passe `faces=[...]` se quiser todas.
- Detalhe nunca é menor que **1 texel** (o `bbkit` expande pra isso): em `density=2` o mínimo prático é 0.5u, em `density=3` é 0.33u.

## 4. Simetria barata

```python
bbkit.mirror_group(m, ["braco_e", "mao_e"], axis=0, center=8, group=g)   # clona + espelha
```
Espelhar grupo inteiro custa uma linha e garante simetria (que o olho humano lê antes de tudo).

## 5. Densidade de texel: 2 para massa, 3 para detalhe

| Cenário | `density` | Textura |
|---|---|---|
| corpo/pieces grandes | 2 | 128×128 |
| com muito micro-detalhe | 3 | 256×256 |
| prop pequeno (<8u) | 3 | 128×128 |

Detalhe denso em textura pequena estoura o alocador de UV (`ValueError: textura cheia`) — é sinal de que a textura precisa crescer, não de cortar detalhe.

## 6. Pós-edição (edite o que já existe)

Útil quando o modelo veio do Blockbench, de outro agente, ou do `Model.load()`:

```python
bbkit.find(m, "tronco")                       # pega o elemento
bbkit.bounds(m, "tronco")                     # (frm, to)
bbkit.translate(m, "tronco", (0, 0.5, 0))     # move (origin acompanha)
bbkit.resize(m, "tronco", 1, 12, anchor="min") # estica mantendo a base
bbkit.set_extent(m, "tampa", 1, 14.0)         # snapa a borda `to` na coordenada
bbkit.rotate(m, "braco", (0, 0, 20))          # soma graus (ZYX)
bbkit.set_origin(m, "braco", (4, 6, 6))       # pivô na junta, sem mover geometria
bbkit.duplicate(m, "pena_e", "pena_d", offset=(6, 0, 0), group=g)
bbkit.remove(m, "pena_d")                     # desfaça a cópia
```

`set_origin` + `rotate` é o par que faz membro de personagem funcionar: pivô na junta primeiro, rotação depois.

## 7. QC de fidelidade

```bash
python3 scripts/bbcheck.py modelo.bbmodel --detail --type mob --style
```

`--type` calibra os limiares: `mob` (micro ≤20%, alerta de alinhamento mais rígido) · `prop` (≤30%, mais tolerante a caixas) · `veiculo` (≤15%) · `diorama` (≤25%). Sem `--type` valem os genéricos.

- **peça fina ausente** → adiciona micro-detalhe (`on_face`/`grid_of`) ou quebra massas.
- **tudo alinhado aos eixos** → incline uma peça-chave (5–15° já muda tudo) ou use `bevel_box`.
- **nenhuma forma com bevel** → 100% caixas retas: o modelo lê como blockout.
- Depois: render 3/4 (`bbrender ... view="hero"`) e confirme que o detalhe aparece **na silhueta**, não só de frente.

## 8. Anti-padrões

| Erro | Como acerta |
|---|---|
| detalhe "enfeite" sem função | só detalhe que conta história: rebite, fivela, cinto, trincheira |
| rebite do tamanho do peito | micro ≤25% da escala maior; se precisa de zoom pra ver, é o tamanho certo |
| rotacionar cubo pra "dar vida" | cubo rotacionado quebra a leitura de UV por face; prefira `bevel_box`/`taper_box` |
| detalhe simétrico perfeito em cima | quebra 1–2 unidades de posição, mantém o resto simétrico |
| encher de peças iguais | 1 detalhe repetido (grid_of) é mais barato e mais elegante que 6 cópias manuais |