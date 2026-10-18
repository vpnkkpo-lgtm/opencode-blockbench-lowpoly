# Workflow Blockbench (importar, editar, exportar)

## Abrir o projeto gerado

1. Gere `link.txt` com `python3 bburl.py modelo.bbmodel --out link.txt --verify`.
2. Abra o link no navegador → Blockbench web carrega o modelo como projeto novo (loadtype=json).
3. Limite: ~1.5M chars de URL. Estourou? Salve o `.bbmodel` e abra via *File → Open model* (drag & drop no app desktop/web registro local).

## Editar à mão e voltar pro código

1. Ajuste no Blockbench (UV editor, paint mode, move/rotate).
2. *File → Save Model* → `.bbmodel` de volta ao disco.
3. No código: `m = Model.load("modelo.bbmodel")` — `m.uv_regions()` reflete o que está lá; **não** mexa em cubos sem passar `uv=` explícito ou `m.reset_alloc()` (ver pitfalls 7).

## Exportar do Blockbench (quando precisar do app)

- **glTF/GLB**: *File → Export → Export GLTF*. O `bbglb.py` gera o mesmo alvo sem abrir o app — use-o por padrão; o do BB serve p/ conferência cruzada.
- **OBJ**: bom p/ checar contagem de tris (o BB mostra a contagem também no rodapé).

## Rodar o GLB nas engines

- **Godot 4**: jogue o `.glb` no projeto (import automático). Material vem com nearest → flag `Filter` no import; textura embutida. Se o modelo estiver "deitado", confira Y-up (nosso export é Y-up direto).
- **three.js**: `GLTFLoader.load("asset.glb")` — o sampler NEAREST evita borrão; `alphaMode MASK` corta transparência duro (ideal pixel art).
- **Unity/Unreal**: import padrão glTF; escala em unidades de modelagem (16u ≈ 1 bloco do Minecraft ≈ 1m no free).

## Compatibilidade de versão

- `format_version: "5.0"` — abre no Blockbench 4.10+ (estável atual). Versões 4.x antigas migram o outliner automaticamente.
- `model_format: "free"` + `box_uv: false`: UV por face independente (o que pintamos). Se abrir como `java_block`, o BB reclama de coords fora do grid — use só p/ conversão explícita.
- Texturas: o arquivo embute PNG base64; exportado para camera0/BlueMap etc. exige formato próprio (Bedrock/Java) — converta dentro do BB (Convert Project).

## Cuidados

- Não regenere o `.bbmodel` com o Blockbench aberto segurando o arquivo antigo — salve/feche antes de rodar o build de novo.
- O web app re-renderiza as faces desabilitadas "ressuscitadas" se virem com UV válido — nosso serializador grava `uv: [0,0,0,0]` + `texture: null` (correto).
- `link.txt` não é estável entre gerações (textura base64 muda) — tudo bem, é descartável; o artefato canônico é o `.bbmodel`.
