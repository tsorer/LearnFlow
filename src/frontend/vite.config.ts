import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  server: {
    // Ziel ist nginx (webapp), nicht die API direkt: docker-compose.yml
    // veroeffentlicht nur den webapp-Port, api:8000 ist von aussen nicht
    // erreichbar. Damit laeuft der Dev-Server ueber denselben /api-Rewrite wie
    // der Browser in Produktion — deshalb hier auch kein eigenes rewrite, das
    // Strippen des Prefix macht nginx (frontend/nginx.conf).
    // Bei abweichendem WEBAPP_PORT in .env die Portangabe hier ergaenzen.
    proxy: {
      "/api": {
        target: "http://localhost",
      },
    },
  },
});
