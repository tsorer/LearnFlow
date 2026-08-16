import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    // Unifies the fetch globals across jsdom and Node so request bodies are
    // readable in every test — see the file for what breaks without it.
    setupFiles: ["./test/setup.ts"],
  },
});
