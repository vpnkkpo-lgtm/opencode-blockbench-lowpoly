import { Plugin } from "@opencode/plugin"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const __dirname = dirname(fileURLToPath(import.meta.url))
const skillMdPath = join(__dirname, "..", "skills", "blockbench-lowpoly", "SKILL.md")

export default Plugin.define({
  id: "blockbench-lowpoly",
  async setup(ctx) {
    const content = readFileSync(skillMdPath, "utf-8")
    await ctx.skill.transform((editor) => {
      editor.add({
        id: "blockbench-lowpoly",
        name: "Blockbench LowPoly",
        description:
          "Toolkit Python puro para autorar assets 3D low poly cute cartoon por código — gera .bbmodel, pinta textura via Canvas, valida (bbcheck), renderiza previews PNG (bbrender), exporta GLB (bbglb) e monta link do web app Blockbench (bburl). Zero dependências, zero MCP, zero editor.",
        path: skillMdPath,
        content,
      })
    })
  },
})
