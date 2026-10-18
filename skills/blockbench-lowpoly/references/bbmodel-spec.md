# Spec do formato .bbmodel (fatos canônicos)

Fonte: código-fonte do Blockbench (master pós-4.10: `outliner/types/cube.js`, `outliner/abstract/face.ts`, `outliner/outliner.js`, `io/format.ts`, `io/formats/obj.js`; web-link do `blockbench-mcp-plugin`). Tudo abaixo está implementado e testado nos scripts da skill.

## Top-level JSON (format_version 5.0, model_format "free", box_uv false)

```json
{
  "meta": { "format_version": "5.0", "model_format": "free", "box_uv": false, "name": "..." },
  "name": "...",
  "resolution": { "width": 128, "height": 128 },
  "elements": [ ... ],
  "outliner": [ ... ],
  "textures": [ ... ]
}
```

## Cubo

- `from` e `to`: [x,y,z] em unidades de modelagem; **exija `from < to` componente a componente** (o BB normaliza, mas solver/normal assume a ordem).
- `origin`: pivô de rotação (padrão do BB: centro do cubo).
- `rotation`: graus, ordem intrínseca **ZYX** → matriz `R = Rz · Ry · Rx`; rotação em torno do próprio `origin`, depois grupos ancestrais em torno dos seus origins.
- `inflate`: expande a geometria sem mudar UV (anti z-fighting).
- `mirror_uv`: flag cosmética de editor (não usado pelos nossos exports).
- `faces`: chaves exatas `north, east, south, west, up, down`. Face desabilitada = `{ "uv": [0,0,0,0], "texture": null }`. Habilitada = `{ "uv": [u1,v1,u2,v2], "texture": 0, "rotation": 0 }`.
- UV em **pixels da textura**, com **v crescendo para BAIXO** a partir do topo.

### Tabela de vértices (`getGlobalVertexPositions`)

| idx | posição |
|-----|---------|
| 0 | to.x, to.y, to.z |
| 1 | to.x, to.y, from.z |
| 2 | to.x, from.y, to.z |
| 3 | to.x, from.y, from.z |
| 4 | from.x, to.y, from.z |
| 5 | from.x, to.y, to.z |
| 6 | from.x, from.y, from.z |
| 7 | from.x, from.y, to.z |

### Índices por face (`getVertexIndices` — ordem interna v0..v3)

| face | vértices | sentido | normal nominal |
|------|----------|---------|----------------|
| north | 1,4,6,3 | CW visto de fora (−Z) | −Z |
| east  | 0,1,3,2 | CW visto de fora (+X) | +X |
| south | 5,0,2,7 | CW visto de fora (+Z) | +Z |
| west  | 4,5,7,6 | CW visto de fora (−X) | −X |
| up    | 4,1,0,5 | CW visto de fora (+Y) | +Y |
| down  | 7,2,3,6 | CW visto de fora (−Y) | −Y |

### UV por canto

O k-ésimo vértice recebe o k-ésimo canto: **[(u1,v1), (u2,v1), (u2,v2), (u1,v2)]** (TL, TR, BR, BL — v para baixo).
`rotation` (0/90/180/270): os 4 cantos rotacionam `r/90` vezes: `corners = [pop(0)... ]` — cada `r/90` move o primeiro canto para o fim (`corners.push(corners.splice(0,1)[0])`).

### Triangulação de export (igual ao OBJ do BB)

Tris `(v2,v1,v0)` e `(v3,v2,v0)` com os UVs pareados. Em GLB: triângulos **não-indexados** (3 vértices cada), normal flat por triângulo.

## Mirror (nosso `Cube.mirror(axis, c)`)

Com `axis` 0/1/2 (X/Y/Z) e centro `c`:
- `rotation[(axis+1)%3] *= -1` e `rotation[(axis+2)%3] *= -1`;
- `from' = 2c − to`, `to' = 2c − from`, `origin' = 2c − origin`;
- swap de faces: X → west↔east, Y → up↔down, Z → south↔north;
- UVs: flip do eixo (+1)%3 em **todas** as faces; flip do eixo "identidade"/across conforme regra do BB (X: flip U em n/s/e/w e em up/down; Z: flip V em n/s/e/w e U em up/down... implementação exata em `bbmodel.py::Cube.mirror`).

**Consequência verificada**: o espelho produz `u1 > u2` (UV horizontalmente espelhada). Isso é **válido** no bbmodel — exporters e renderizadores consomem as coordenadas direto, sem normalizar. Não "corrija".

## Mesh (só model_format "free")

- `vertices`: lista de [x,y,z] **relativos ao `origin`** do mesh.
- `faces`: `[{ "vertices": [i0,i1,...], "uv": {"i0": [u,v], ...} }]` — índices CCW vistos de fora; **quads planares** (ou tris); "sem uv" → textura sólida (o BB costuma usar o canto (0,0)).
- Sem box_uv: cada face tem UV própria.

## Outliner

- **5.0 (flat)**: `[ { "name", "uuid", "origin", "rotation", "color" }, { "uuid", "isOpen", "children": [...] } ]` — grupos são nós independentes referenciados por uuid dentro de nós `{uuid, children}`. Elementos no outliner referenciam o uuid do ELEMENTO.
- **4.x (nested)**: `[ { name, uuid, children: [...], origin, rotation } ]` — grupo inline.
- Nosso `Model.load` suporta os dois; `to_dict` grava 5.0.
- Elemento fora do outliner (ou com parent inexistente) é re-anexado à raiz com aviso.

## Texturas

```json
{ "path": "", "name": "texture.png", "folder": "", "namespace": "",
  "id": "0", "particle": true, "uuid": "...", "source": "data:image/png;base64,..." }
```
`faces[d].texture` = índice nessa lista (int) ou `null`. A skill sempre usa índice 0.

## Link do web app Blockbench

```
https://web.blockbench.net/#loadtype=json&loadname=NOME.bbmodel&loaddata=DADOS
```

### Parser do hash (`js/web.ts`)

```js
let query_string = location.search || location.hash
query_string = decodeURIComponent(query_string.substring(1))
queries = query_string.split('&')
[key, value] = string.split(/=\s*(.+)/)   // regex COM grupo capturado
```

- **UMA** passada de `decodeURIComponent` e então `split("&")` — logo o payload não pode conter `&` cru. Escape na origem: `&` → `\u0026` **antes** do percent-encode, depois `urllib.parse.quote(data, safe="!*'()")` — é exatamente o que `bburl.py` faz.
- O split usa regex com grupo capturado: o primeiro `=` separa chave e valor, e um `=` dentro do base64 (padding) **não** quebra, porque o casamento começa no primeiro `=`.

### A extensão do `loadname` decide se abre (crítico)

`js/io/io.js::loadModelFile`:

```js
let extension = pathToExtension(file.path)   // file.path = Blockbench.queries.loadname
if (extensions.includes(extension) && ...)   // codec.load_filter.extensions == ['bbmodel']
...
unsupportedFileFormatMessage(file.path)      // ← "invalid format" na UI
```

`loadname` sem `.bbmodel` ⇒ `extension == ""` ⇒ nenhum codec casa ⇒ erro. O
`build_url` normaliza o nome e `verify()` valida a extensão.

- `verify()` faz o roundtrip completo com o mesmo algoritmo do app.
- Limite prático do web app: ~1.5M caracteres de URL (a skill avisa acima disso). Texturas base64 dominam o tamanho.

## Animações

```json
"animations": [{
  "uuid": "...", "name": "idle", "loop": "loop", "length": 2, "snapping": 24,
  "animators": {
    "<uuid do GRUPO>": {
      "name": "asa_l", "type": "bone",
      "keyframes": [{
        "uuid": "...", "channel": "rotation", "time": 0.5, "color": -1,
        "interpolation": "linear", "data_points": [{"x": 0, "y": 0, "z": 18}]
      }]
    }
  }
}]
```

- **`animators` é indexado pelo UUID do grupo (osso)** — daí a necessidade de
  remapear por nome quando a hierarquia é reconstruída (`preserve_animations`).
- Canais: `position`, `rotation`, `scale`.
- `loop`: `"loop"` | `"once"` | `"hold"`.
- Regra de direção do keyframe mudou no **5.0**: antes, valores de posição eram
  invertidos no eixo X e de rotação em X e Y. O loader corrige automaticamente
  arquivos com `format_version < 5.0` (`invertMolang`) — por isso **não** grave
  `format_version` antigo junto com animação já corrigida, ou o movimento sai
  espelhado.

## Mapeamento para GLB (bbglb.py)

- UV direto `(u_px / tex_w, v_px / tex_h)` — **sem** `1 − v` (o bbmodel já usa v para baixo e o glTF v para cima... o exportador do BB inverte; nós replicamos o resultado do BB com o mapeamento direto sobre a tabela de cantos).
- Y-up direto (bbmodel já é Y-up).
- Triângulos não-indexados, normais flat por triângulo, `POSITION` com `min`/`max`.
- Material: `metallicFactor 0`, `roughnessFactor 1`, `doubleSided false`, `alphaMode "MASK"` com `alphaCutoff 0.5` quando a textura tem alpha parcial.
- Sampler `magFilter 9728` (NEAREST), `minFilter 9986` (NEAREST_MIPMAP_NEAREST), wraps 10497 (REPEAT).
- PNG embutido em bufferView; bufferViews alinhados a 4 bytes; chunk JSON (`0x4E4F534A`, pad com espaço) + chunk BIN (`0x004E4942`, pad com zero).

## Formatos e limites

- `free` (nosso) e `java_block` (coordenadas inteiras −16..32 por eixo — bbcheck avisa). Bedrock usa geometria própria; converta dentro do BB se precisar.
- `format_version "5.0"` abre em BB 4.10+ (atual). Versões antigas migram sozinhas (o loader do BB aceita 4.x também).
