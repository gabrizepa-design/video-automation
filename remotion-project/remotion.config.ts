import { Config } from "@remotion/cli/config";

// CRÍTICO para VPS sin GPU — usa software OpenGL renderer
Config.setChromiumOpenGlRenderer("swangle");

// Formato de frames internos (jpeg es más rápido que png)
Config.setVideoImageFormat("jpeg");

// Sobreescribir output si ya existe
Config.setOverwriteOutput(true);

// Concurrencia (ajustar según CPU del VPS)
// 4 es seguro para un VPS de 4 vCPU con 8GB RAM
Config.setConcurrency(4);

// Deshabilitar descarga de Chromium (usamos el del sistema)
Config.setBrowserExecutable("/usr/bin/chromium");
