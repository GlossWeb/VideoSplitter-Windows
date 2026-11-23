# Video Splitter para Windows

Este paquete conserva la interfaz y las funciones del programa original.
El flujo de compilación se ejecuta en GitHub Actions sobre Windows, aunque
el proyecto se prepare desde Ubuntu.

## Crear el ejecutable

1. Crea un repositorio en GitHub.
2. Sube todos los archivos de esta carpeta, incluida la carpeta `.github`.
3. En GitHub abre **Actions**.
4. Selecciona **Build Video Splitter for Windows**.
5. Pulsa **Run workflow**.
6. Cuando termine, abre la ejecución y descarga el artefacto
   **VideoSplitter-Windows**.

El ZIP generado contiene `VideoSplitter.exe` y `LEEME.txt`.
FFmpeg y FFprobe se empaquetan dentro del ejecutable.

## Requisitos

No necesitas instalar Python ni FFmpeg en el PC Windows de destino.
