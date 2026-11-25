import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Solo funciones puras (lib/): entorno Node, sin navegador simulado.
export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
