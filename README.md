# JsonMetrix

Aplicación local con Streamlit para comparar métricas de procesamiento a partir de uno o varios archivos JSON de LogExport.

## Funcionalidades

- Seleccionar archivos JSON disponibles dentro del proyecto o cargar varios archivos desde el equipo.
- Leer JSON estándar, JSON Lines y secuencias de objetos JSON concatenados.
- Ignorar eventos de inicio del logger (`"@mt": "Metrics logger started"`).
- Agrupar registros por `JobNumber` y calcular:
	- Inicio más temprano y final más tardío.
	- Duración total en segundos.
	- Uso medio de CPU, presentado como porcentaje con dos decimales.
	- Total de records y cantidad de registros analizados.
- Comparar duración, uso de CPU y records mediante gráficas de barras.
- Limpiar los archivos seleccionados y cargados con el botón **Limpiar todo**.

## Requisitos

- Windows
- Python 3.9 o posterior
- Dependencias: Streamlit, pandas y Altair

## Instalación

Desde PowerShell, en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install streamlit pandas altair
```

Si ya existe el entorno `.venv`, no es necesario crearlo nuevamente.

## Ejecución

Con `app.py` en la raíz del proyecto, inicia la aplicación con:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit mostrará la dirección local en la terminal; normalmente es [http://localhost:8501](http://localhost:8501).

## Datos esperados

Los registros de métricas deben incluir `JobNumber`, `CpuAveragePercent` y `Records`, además de fechas de inicio y fin en `ProcessingStartUtc` / `ProcessingEndUtc` o `ProcessingStartLocal` / `ProcessingEndLocal`. Los valores se agregan entre los registros válidos de cada trabajo. Los archivos JSON pueden seleccionarse desde el proyecto o cargarse desde el navegador.
"# JsonMetrix" 
