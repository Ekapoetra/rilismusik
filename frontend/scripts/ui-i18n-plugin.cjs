/** Localizes only authored presentation text. Values, routes, IDs and arbitrary API data are untouched. */
module.exports = function uiI18nPlugin({ types: t }) {
  const ATTRIBUTES = new Set(["title", "label", "placeholder", "aria-label", "alt", "description", "emptyText", "submitLabel"]);
  const protectedAncestor = (path) => Boolean(path.findParent((parent) => parent.isJSXElement() && parent.node.openingElement.attributes.some((attr) => t.isJSXAttribute(attr) && ((attr.name.name === "translate" && attr.value?.value === "no") || attr.name.name === "data-no-translate"))));
  const useful = (value) => typeof value === "string" && /[A-Za-zÀ-ÿ]{2}/.test(value) && !/^(https?:|\/api\/|[\w-]+@)/i.test(value) && !/^RILIS\s*MUSIK$/i.test(value.trim()) && !/^[\w-]+\.[\w.-]+$/.test(value.trim());
  const clean = (node) => (t.react.buildChildren({ children: [node] })[0]?.value || "");
  const staticData = (node, scope, seen = new Set()) => {
    if (!node) return false;
    if (t.isArrayExpression(node)) return true;
    if (t.isObjectExpression(node)) return true;
    if (t.isIdentifier(node)) {
      if (/(?:LABELS|TITLES|REASONS|HEADERS|CATEGORIES|TABS|STEPS|COPY)$/.test(node.name)) return true;
      if (seen.has(node.name)) return false; seen.add(node.name);
      const binding = scope.getBinding(node.name);
      return binding?.path.isVariableDeclarator() ? staticData(binding.path.node.init, binding.scope, seen) : false;
    }
    if (t.isCallExpression(node) && t.isMemberExpression(node.callee)) {
      if (t.isIdentifier(node.callee.object, { name: "Object" }) && ["entries", "values", "keys"].includes(node.callee.property.name)) return staticData(node.arguments[0], scope, seen);
      if (["filter", "map", "slice"].includes(node.callee.property.name)) return staticData(node.callee.object, scope, seen);
    }
    return false;
  };
  const staticMapValue = (node, path) => {
    let root = node;
    while (t.isMemberExpression(root)) root = root.object;
    if (!t.isIdentifier(root)) return false;
    if (/(?:LABELS|TITLES|REASONS|HEADERS|CATEGORIES|COPY)$/.test(root.name)) return true;
    const binding = path.scope.getBinding(root.name);
    const fn = binding?.path.findParent((parent) => parent.isFunction());
    const call = fn?.parentPath;
    if (!call?.isCallExpression() || !t.isMemberExpression(call.node.callee) || call.node.callee.property.name !== "map") return false;
    return staticData(call.node.callee.object, call.scope);
  };
  const template = (node) => ({ source: node.quasis.map((part, index) => part.value.cooked + (index < node.expressions.length ? `{${index}}` : "")).join(""), values: node.expressions });
  const record = (state, value) => { if (useful(value)) state.uiStrings.add(value.replace(/\s+/g, " ").trim()); };
  const textComponent = (state, source, values) => {
    state.uiUsed = true;
    const attrs = [t.jsxAttribute(t.jsxIdentifier("source"), t.jsxExpressionContainer(source))];
    if (values?.length) attrs.push(t.jsxAttribute(t.jsxIdentifier("values"), t.jsxExpressionContainer(t.arrayExpression(values))));
    const element = t.jsxElement(t.jsxOpeningElement(t.jsxIdentifier("__RmSystemText"), attrs, true), null, [], true);
    element.__rmUiGenerated = true;
    return element;
  };
  const renderExpression = (node, path, state) => {
    if (t.isStringLiteral(node) && useful(node.value)) { record(state, node.value); return textComponent(state, node); }
    if (t.isTemplateLiteral(node)) { const data = template(node); if (useful(data.source)) { record(state, data.source); return textComponent(state, t.stringLiteral(data.source), data.values); } }
    if (t.isConditionalExpression(node)) return t.conditionalExpression(node.test, renderExpression(node.consequent, path, state), renderExpression(node.alternate, path, state));
    if (t.isLogicalExpression(node)) return t.logicalExpression(node.operator, node.left, renderExpression(node.right, path, state));
    if (staticMapValue(node, path) && !/(?:label_name|artist_name|release_title|track_title|lyrics|email|body)$/.test(node.property?.name || "")) return textComponent(state, node);
    if (!state.filename.includes("/chat/") && t.isIdentifier(node) && /^(err|error|errorMessage|msg|successMessage)$/.test(node.name)) return textComponent(state, node);
    return node;
  };
  const propValue = (node, state) => {
    if (t.isStringLiteral(node) && useful(node.value)) { record(state, node.value); return node; }
    if (t.isTemplateLiteral(node)) { const data = template(node); if (useful(data.source)) { record(state, data.source); return t.objectExpression([t.objectProperty(t.identifier("source"), t.stringLiteral(data.source)), t.objectProperty(t.identifier("values"), t.arrayExpression(data.values))]); } }
    if (t.isConditionalExpression(node) && [node.consequent, node.alternate].every((part) => t.isStringLiteral(part))) { record(state, node.consequent.value); record(state, node.alternate.value); return node; }
    return null;
  };
  return {
    pre(file) { this.filename = file.opts.filename || ""; this.uiStrings = new Set(); this.uiUsed = false; this.uiGlobalUsed = false; this.uiDisabled = !this.filename.includes("/src/") || /\/i18n\/|\/components\/landing\/|\/pages\/public\/|\/constants\/|\/api\//.test(this.filename); },
    visitor: {
      Program: { exit(path, state) {
        if (state.uiUsed) path.unshiftContainer("body", t.importDeclaration([t.importSpecifier(t.identifier("__RmSystemText"), t.identifier("SystemText")), t.importSpecifier(t.identifier("__RmSystemElement"), t.identifier("SystemElement"))], t.stringLiteral("@/i18n/SystemText")));
        if (state.uiGlobalUsed) path.unshiftContainer("body", t.importDeclaration([t.importSpecifier(t.identifier("__RmTranslateUi"), t.identifier("translateUi")), t.importSpecifier(t.identifier("__RmTranslateTemplate"), t.identifier("translateTemplate"))], t.stringLiteral("@/i18n/languageStore")));
        state.file.metadata.rilisUiStrings = [...state.uiStrings];
      } },
      JSXText(path, state) {
        if (state.uiDisabled || protectedAncestor(path) || path.parentPath.node.__rmUiGenerated || ["option", "textarea", "script", "style"].includes(path.parentPath.node.openingElement?.name?.name)) return;
        const value = clean(path.node);
        if (!useful(value)) return;
        record(state, value); path.replaceWith(t.jsxExpressionContainer(textComponent(state, t.stringLiteral(value)))); path.skip();
      },
      JSXExpressionContainer(path, state) {
        if (state.uiDisabled || path.parentPath.isJSXAttribute() || protectedAncestor(path) || path.parentPath.node.__rmUiGenerated || path.parentPath.node.openingElement?.name?.name === "option") return;
        const result = renderExpression(path.node.expression, path, state);
        if (result !== path.node.expression) { path.node.expression = result; path.skip(); }
      },
      JSXElement: { exit(path, state) {
        if (state.uiDisabled || path.node.__rmUiGenerated || protectedAncestor(path) || path.node.openingElement.attributes.some((attr) => attr.name?.name === "translate" && attr.value?.value === "no")) return;
        const node = path.node;
        const attrs = [], ui = [];
        node.openingElement.attributes.forEach((attribute) => {
          if (t.isJSXAttribute(attribute) && ATTRIBUTES.has(attribute.name.name)) {
            const raw = t.isJSXExpressionContainer(attribute.value) ? attribute.value.expression : attribute.value;
            const translated = propValue(raw, state);
            if (translated) { ui.push(t.objectProperty(t.stringLiteral(attribute.name.name), translated)); return; }
          }
          attrs.push(attribute);
        });
        let uiText = null;
        if (node.openingElement.name.name === "option") {
          const sources = [], values = [];
          node.children.forEach((child) => { if (t.isJSXText(child)) sources.push(clean(child)); else if (t.isJSXExpressionContainer(child)) { sources.push(`{${values.length}}`); values.push(child.expression); } });
          const source = sources.join("");
          if (useful(source)) { record(state, source); uiText = values.length ? t.objectExpression([t.objectProperty(t.identifier("source"), t.stringLiteral(source)), t.objectProperty(t.identifier("values"), t.arrayExpression(values))]) : t.stringLiteral(source); }
          else if (values.length === 1 && staticMapValue(values[0], path)) uiText = values[0];
        }
        if (!ui.length && !uiText) return;
        const name = node.openingElement.name;
        const asExpression = t.isJSXIdentifier(name) ? (/^[a-z]/.test(name.name) ? t.stringLiteral(name.name) : t.identifier(name.name)) : t.memberExpression(t.identifier(name.object.name), t.identifier(name.property.name));
        attrs.push(t.jsxAttribute(t.jsxIdentifier("as"), t.jsxExpressionContainer(asExpression)));
        if (ui.length) attrs.push(t.jsxAttribute(t.jsxIdentifier("ui"), t.jsxExpressionContainer(t.objectExpression(ui))));
        if (uiText) attrs.push(t.jsxAttribute(t.jsxIdentifier("uiText"), t.jsxExpressionContainer(uiText)));
        node.openingElement.name = t.jsxIdentifier("__RmSystemElement"); node.openingElement.attributes = attrs;
        if (node.closingElement) node.closingElement.name = t.jsxIdentifier("__RmSystemElement");
        if (uiText) node.children = [];
        node.__rmUiGenerated = true; state.uiUsed = true;
      } },
      CallExpression(path, state) {
        if (state.uiDisabled) return;
        const callee = path.node.callee;
        const name = t.isIdentifier(callee) ? callee.name : callee.property?.name;
        if (["t", "setErr", "setError", "setMsg", "setMessage", "alert", "confirm", "success", "error", "info", "warning", "message"].includes(name)) {
          const value = path.node.arguments[0];
          if (t.isStringLiteral(value)) record(state, value.value);
          if (t.isTemplateLiteral(value)) record(state, template(value).source);
          if (["alert", "confirm"].includes(name) && (t.isIdentifier(callee) || callee.object?.name === "window")) {
            if (t.isStringLiteral(value) && useful(value.value)) { path.node.arguments[0] = t.callExpression(t.identifier("__RmTranslateUi"), [value]); state.uiGlobalUsed = true; }
            if (t.isTemplateLiteral(value)) { const data = template(value); path.node.arguments[0] = t.callExpression(t.identifier("__RmTranslateTemplate"), [t.stringLiteral(data.source), t.arrayExpression(data.values)]); state.uiGlobalUsed = true; }
          }
          if (callee.object?.name === "toast" && (t.isStringLiteral(value) || t.isTemplateLiteral(value))) path.node.arguments[0] = renderExpression(value, path, state);
        }
      },
    },
  };
};
module.exports = require("@babel/helper-plugin-utils").declare(module.exports);