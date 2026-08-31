import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Empaqueta solo lo necesario para ejecutar: la imagen Docker no lleva node_modules.
  output: "standalone",
};

export default nextConfig;
