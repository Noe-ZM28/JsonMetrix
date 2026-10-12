# JsonMetrix

Dashboard local con Streamlit para analizar métricas de procesamiento LogExport y comparar dos archivos JSON.

## Funcionalidades

- Analizar uno o varios archivos JSON cargados desde el equipo.
- Comparar dos archivos por `JobNumber`, con tablas paralelas para A y B y diferencias `B - A`.
- Leer JSON estándar, JSON Lines y secuencias de objetos JSON concatenados.
- Excluir eventos de inicio del logger y evitar contar de nuevo resúmenes cuando también hay registros detallados.
- Agrupar métricas por trabajo: inicio y fin, duración transcurrida, duración acumulada en milisegundos, CPU media y pico, tamaño total y records.
- Mostrar gráficas de duración, CPU, tamaño y records. En modo análisis, cada métrica permite cambiar por separado entre barras, línea, puntos y área.
- Mostrar los tamaños automáticamente en KB, MB o GB.
- Limpiar archivos y estado de la sesión con **Limpiar todo**.

## Requisitos

- Windows
- Python 3.9 o posterior

## Instalación

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si ya tienes el entorno `.venv`, puedes omitir su creación.

Para activarlo en PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
```

## Ejecución

```powershell
streamlit run app.py
```

Abre la URL local que indique Streamlit, normalmente [http://localhost:8501](http://localhost:8501).

## Formato de los datos

Para las métricas por trabajo, los registros deben incluir `JobNumber`, `CpuAveragePercent` y `Records`. También se reconocen `DurationMs`, `CpuPeakPercent`, `InputBytes` y las fechas `ProcessingStartUtc` / `ProcessingEndUtc` o `ProcessingStartLocal` / `ProcessingEndLocal`.

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
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si ya existe el entorno `.venv`, no es necesario crearlo nuevamente.

Para activarlo en PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
```

## Ejecución

Con `app.py` en la raíz del proyecto, inicia la aplicación con:

```powershell
streamlit run app.py
```

Streamlit mostrará la dirección local en la terminal; normalmente es [http://localhost:8501](http://localhost:8501).

## Datos esperados

Los registros de métricas deben incluir `JobNumber`, `CpuAveragePercent` y `Records`, además de fechas de inicio y fin en `ProcessingStartUtc` / `ProcessingEndUtc` o `ProcessingStartLocal` / `ProcessingEndLocal`. Los valores se agregan entre los registros válidos de cada trabajo. Los archivos JSON pueden seleccionarse desde el proyecto o cargarse desde el navegador.
"# JsonMetrix" 
