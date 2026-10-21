import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Option B: bind to 127.0.0.1 so OAuth cookies work with API on 127.0.0.1:8000
  server: { port: 5173, host: "127.0.0.1", strictPort: true },
});
