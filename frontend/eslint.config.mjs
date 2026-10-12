import js from "@eslint/js";
import tseslint from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
const config = [
  { ignores: [".next/**", "node_modules/**", "playwright-report/**", "test-results/**", "next-env.d.ts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { languageOptions: { globals: { process: "readonly", window: "readonly", document: "readonly", fetch: "readonly", URL: "readonly", URLSearchParams: "readonly", setTimeout: "readonly", FormData: "readonly", File: "readonly", console: "readonly" } } },
  { files: ["**/*.tsx"], plugins: { "react-hooks": hooks }, rules: {
    "react-hooks/rules-of-hooks": "error", "react-hooks/exhaustive-deps": "error",
  } },
];
export default config;
