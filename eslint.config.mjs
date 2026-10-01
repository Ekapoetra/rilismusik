export default [
  {
    files: ["scripts/build-maintenance.cjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "commonjs",
      globals: { console: "readonly", __dirname: "readonly" },
    },
    rules: {
      "no-undef": "error",
      "no-unused-vars": "error",
      "no-unreachable": "error",
      "valid-typeof": "error",
    },
  },
];
