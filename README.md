# JsonMetrix

Dashboard local con Streamlit para analizar métricas LogExport desde archivos JSON y comparar dos archivos.

## Funcionalidades

- Analizar uno o varios JSON cargados desde el equipo, agrupando resultados por `JobNumber`.
- Comparar dos archivos con tablas A/B paralelas, diferencias `B - A` y gráficas de barras agrupadas.
- Leer JSON estándar, JSON Lines y secuencias de objetos concatenados.
- Ignorar eventos de inicio del logger y evitar duplicar los registros resumen cuando existen registros detallados.
- Alternar entre métricas por registro individual y promedios por `JobNumber`.
- Cambiar de forma independiente el tipo de gráfica entre barras, línea, puntos y área.
- Visualizar el pico máximo de CPU frente al tiempo por encima del umbral configurado, tanto por registro como por trabajo.
- Ajustar los colores al tema activo: paleta neón en modo oscuro y colores oscuros en modo claro.
- Mostrar tamaños de archivo automáticamente en KB, MB o GB.
- Limpiar los archivos cargados y el estado de sesión con **Limpiar todo**.

Las fechas agregadas usan el inicio más temprano y el fin más tardío. El uso medio de CPU se pondera por la duración de los registros. El tiempo de la gráfica de CPU corresponde a `CpuTimeAboveThresholdMs` sobre `CpuThresholdPercent`; no es tiempo por encima del pico máximo.

## Requisitos

- Windows
- Python 3.9 o posterior

## Instalación

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

El archivo `.gitignore` excluye el entorno virtual y los archivos de caché de Python.

## Ejecución

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abre la dirección que indique Streamlit, normalmente [http://localhost:8501](http://localhost:8501).

## Datos esperados

Los registros deben incluir `JobNumber`, `CpuAveragePercent` y `Records`. También se reconocen `DurationMs`, `CpuPeakPercent`, `CpuTimeAboveThresholdMs`, `CpuThresholdPercent`, `InputBytes` y las fechas `ProcessingStartUtc` / `ProcessingEndUtc` o `ProcessingStartLocal` / `ProcessingEndLocal`.
