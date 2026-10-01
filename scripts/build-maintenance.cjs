const fs = require("node:fs");
const path = require("node:path");

// Build only the maintenance page. No application or database code is loaded.
const projectRoot = path.resolve(__dirname, "..");
const output = path.join(projectRoot, "maintenance-dist");
const logo = fs.readFileSync(path.join(projectRoot, "frontend/public/brand/logo-ui-light.png"));
const logoData = "data:image/png;base64," + logo.toString("base64");
const template = fs.readFileSync(path.join(projectRoot, "maintenance/index.html"), "utf8");
const page = template.replaceAll("{{RILIS_MUSIK_LOGO}}", logoData);
if (page.includes("{{RILIS_MUSIK_LOGO}}")) throw new Error("Maintenance logo placeholder was not replaced");
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(path.join(output, "index.html"), page);
console.log("Built static Rilis Musik maintenance page.");
