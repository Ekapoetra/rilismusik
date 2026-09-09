const fs = require("fs"), path = require("path"), babel = require("@babel/core");
const root = path.resolve(__dirname, "../src"), texts = new Set(), colors = new Set();
function walk(folder) { return fs.readdirSync(folder, { withFileTypes: true }).flatMap((entry) => entry.isDirectory() ? walk(path.join(folder, entry.name)) : /\.(jsx|js)$/.test(entry.name) ? [path.join(folder, entry.name)] : []); }
for (const filename of walk(root)) {
  const code = fs.readFileSync(filename, "utf8");
  try {
    const result = babel.transformSync(code, { filename, configFile: false, babelrc: false, parserOpts: { plugins: ["jsx"] }, plugins: [require("./ui-i18n-plugin.cjs")] });
    for (const text of result.metadata.rilisUiStrings || []) texts.add(text);
    if (!/\/i18n\//.test(filename)) babel.transformSync(code, { filename, configFile: false, babelrc: false, parserOpts: { plugins: ["jsx"] }, plugins: [() => ({ visitor: { StringLiteral(nodePath) {
      const value = nodePath.node.value.replace(/\s+/g, " ").trim();
      if (nodePath.parentPath.isImportDeclaration() || nodePath.parentPath.isExportNamedDeclaration() || (nodePath.parentPath.isObjectProperty() && nodePath.key === "key")) return;
      if (nodePath.parentPath.isJSXAttribute() && ["className", "id", "name", "value", "src", "href", "data-testid", "type"].includes(nodePath.parentPath.node.name.name)) return;
      if (value.length < 2 || value.length > 1800 || !/[A-Za-z]{2}/.test(value) || /^(https?:|\/|\.|@)|RILIS\s*MUSIK/.test(value) || /(?:^|\s)(?:bg-|text-|p[xytrbl]?-|m[xytrbl]?-|w-|h-|rounded-|border-|grid-|flex-|hover:|sm:|md:|lg:)/.test(value) || /^[a-z0-9_.:/-]+$/.test(value) || /[{}<>]=|application\/|image\/|audio\//.test(value)) return;
      texts.add(value);
    } } })] });
  } catch (error) { console.error(filename, error.message); process.exitCode = 1; }
  for (const match of code.matchAll(/bg-\[(#[0-9a-fA-F]{3,8})\](?:\/\d+)?/g)) {
    let hex = match[1].slice(1); if (hex.length === 3) hex = hex.split("").map((ch) => ch + ch).join("");
    const rgb = [0, 2, 4].map((position) => parseInt(hex.slice(position, position + 2), 16));
    if (Math.max(...rgb) <= 55) colors.add(match[0]);
  }
}
const source = path.resolve(root, "i18n/catalog.source.json");
fs.writeFileSync(source, JSON.stringify([...texts].sort(), null, 2));
const css = [...colors].map((cls) => `html[data-app-theme="light"] [class~="${cls}"] { background-color: var(--ui-surface); }`).join("\n");
fs.writeFileSync(path.resolve(root, "styles/theme-compat.css"), css + "\n");
console.log(`UI catalog: ${texts.size} authored strings; ${colors.size} dark-surface variants.`, source);