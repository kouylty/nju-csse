import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", ".cache/**", "test-results/**", "UI/**"] },
  js.configs.recommended,
  { files: ["web/js/**/*.js"], languageOptions: { globals: globals.browser } },
  {
    files: ["*.js", "tests/browser/**/*.js", "scripts/**/*.mjs"],
    languageOptions: { globals: globals.node },
  },
  {
    files: ["tests/browser/**/*.js"],
    languageOptions: { globals: globals.browser },
  },
];
