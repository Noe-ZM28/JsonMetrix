import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


def extract_json_records(raw_text: str):
    text = raw_text.strip()
    if not text:
        raise ValueError("El archivo JSON está vacío.")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                records.append(parsed)
        except json.JSONDecodeError:
            continue
    if records:
        return records

    objects = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        if text[i] != "{":
            i += 1
            continue

        start = i
        depth = 0
        in_string = False
        escape = False
        while i < n:
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                objects.append(obj)
                        except json.JSONDecodeError:
                            pass
                        i += 1
                        break
            i += 1

        if i >= n:
            break

    if objects:
        return objects

    raise ValueError("El contenido no se pudo interpretar como JSON válido.")


def format_file_size(size_bytes):
    if pd.isna(size_bytes):
        return "N/D"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    return f"{size_bytes / (1024 ** 3):.2f} GB"


def select_chart_type(key):
    return st.radio(
        "Tipo de gráfica",
        ["Barras", "Línea", "Puntos", "Área"],
        horizontal=True,
        key=key,
    )


def apply_chart_mark(chart, chart_type):
    if chart_type == "Línea":
        return chart.mark_line(point=True)
    if chart_type == "Puntos":
        return chart.mark_point(filled=True, size=90)
    if chart_type == "Área":
        return chart.mark_area()
    return chart.mark_bar()


def job_color(chart_type):
    if chart_type in ("Línea", "Área"):
        return alt.value("#367a8c")
    return alt.Color("JobNumber:N", legend=alt.Legend(labelLimit=0, labelFontSize=12))


def build_metrics_by_job(file_sources):
    rows = []
    errors = []

    for source in file_sources:
        try:
            if hasattr(source, "read"):
                raw_text = source.read().decode("utf-8")
                file_name = source.name
            else:
                raw_text = Path(source).read_text(encoding="utf-8")
                file_name = Path(source).name

            records = extract_json_records(raw_text)
            for record in records:
                if not isinstance(record, dict):
                    continue
                if record.get("@mt") == "Metrics logger started":
                    continue
                if "JobNumber" not in record:
                    continue

                job_number = str(record.get("JobNumber") or "UNKNOWN")
                cpu = record.get("CpuAveragePercent")
                duration_ms = record.get("DurationMs")
                cpu_peak = record.get("CpuPeakPercent")
                input_bytes = record.get("InputBytes")
                records_count = record.get("Records")
                start = record.get("ProcessingStartUtc") or record.get("ProcessingStartLocal")
                end = record.get("ProcessingEndUtc") or record.get("ProcessingEndLocal")
                is_summary = (
                    record.get("EventType") == "JobSummary"
                    or record.get("WorkItemId") == "SUMMARY"
                    or record.get("File") == "JOB_SUMMARY"
                )

                if cpu is not None and records_count is not None:
                    rows.append(
                        {
                            "Archivo": file_name,
                            "JobNumber": job_number,
                            "CpuAveragePercent": cpu,
                            "DurationMs": duration_ms,
                            "CpuPeakPercent": cpu_peak,
                            "InputBytes": input_bytes,
                            "Records": records_count,
                            "Site": record.get("Site", "N/A"),
                            "Status": record.get("Status", "N/A"),
                            "Inicio": start,
                            "Fin": end,
                            "EsResumen": is_summary,
                        }
                    )
        except Exception as exc:
            errors.append(f"{source if isinstance(source, str) else getattr(source, 'name', str(source))}: {exc}")

    df = pd.DataFrame(rows)
    if not df.empty:
        numeric_columns = [
            "CpuAveragePercent",
            "DurationMs",
            "CpuPeakPercent",
            "InputBytes",
            "Records",
        ]
        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.dropna(subset=["CpuAveragePercent", "Records"]).reset_index(drop=True)

    if df.empty:
        return df, errors

    has_details = df.groupby("JobNumber")["EsResumen"].transform(lambda values: (~values).any())
    df = df.loc[~df["EsResumen"] | ~has_details].reset_index(drop=True)

    df["Inicio_ts"] = pd.to_datetime(df["Inicio"], errors="coerce")
    df["Fin_ts"] = pd.to_datetime(df["Fin"], errors="coerce")
    df = df.dropna(subset=["Inicio_ts", "Fin_ts"]).reset_index(drop=True)

    if df.empty:
        return df, errors

    grouped = (
        df.groupby("JobNumber", as_index=False)
        .agg(
            Inicio=("Inicio_ts", "min"),
            Fin=("Fin_ts", "max"),
            MediaUsoCPU=("CpuAveragePercent", "mean"),
            DuracionTotalMs=("DurationMs", "sum"),
            PicoUsoCPU=("CpuPeakPercent", "max"),
            TotalInputBytes=("InputBytes", "sum"),
            TotalRecords=("Records", "sum"),
            RegistrosAnalizados=("Records", "count"),
            Archivos=("Archivo", "nunique"),
            Sitios=("Site", "nunique"),
        )
        .sort_values("TotalRecords", ascending=False)
        .reset_index(drop=True)
    )

    grouped["DuracionSegundos"] = (grouped["Fin"] - grouped["Inicio"]).dt.total_seconds()
    grouped["DuracionMinutos"] = (grouped["DuracionSegundos"] / 60).round(2)
    grouped["TamanoTotal"] = grouped["TotalInputBytes"].map(format_file_size)
    return grouped, errors


st.set_page_config(page_title="JsonMetrix", page_icon="📊", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
        box-sizing: border-box;
        width: 70%;
        max-width: 70%;
        margin-left: auto;
        margin-right: auto;
        padding-left: clamp(1rem, 2.5vw, 2.5rem);
        padding-right: clamp(1rem, 2.5vw, 2.5rem);
    }

    @media (max-width: 1024px) {
        [data-testid="stMainBlockContainer"] {
            width: 90%;
            max-width: 90%;
        }
    }

    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            width: 100%;
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("JsonMetrix")
st.write("Carga uno o varios archivos JSON y compara el uso de CPU y la cantidad de registros.")

if st.button("Limpiar todo", type="secondary"):
    st.session_state.pop("selected_paths", None)
    st.session_state.pop("uploaded_files", None)
    st.session_state.pop("file_sources", None)
    st.rerun()

uploaded_files = st.file_uploader(
    "Selecciona uno o varios archivos JSON",
    type=["json"],
    accept_multiple_files=True,
    key="uploaded_files",
)

file_sources = list(uploaded_files or [])
st.session_state["file_sources"] = file_sources

if file_sources:
    metrics_df, errors = build_metrics_by_job(file_sources)

    if errors:
        st.warning("Algunos archivos no pudieron procesarse:")
        for error in errors:
            st.write(f"- {error}")

    if metrics_df.empty:
        st.error("No se encontraron métricas válidas con JobNumber, CpuAveragePercent y Records en los JSON cargados.")
    else:
        st.success(f"Se agruparon {len(metrics_df)} JobNumbers con métricas válidas.")

        st.subheader("Tabla agregada por JobNumber")
        st.dataframe(
            metrics_df,
            column_config={
                "MediaUsoCPU": st.column_config.NumberColumn("MediaUsoCPU", format="%.2f%%"),
                "PicoUsoCPU": st.column_config.NumberColumn("PicoUsoCPU", format="%.2f%%"),
            },
            use_container_width=True,
        )

        st.subheader("Duración por JobNumber (segundos)")
        duration_chart_type = select_chart_type("chart_type_duration")
        duration_chart = (
            apply_chart_mark(alt.Chart(metrics_df), duration_chart_type)
            .encode(
                x=alt.X(
                    "JobNumber:N",
                    sort="-y",
                    axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                ),
                y=alt.Y(
                    "DuracionSegundos:Q",
                    title="Duración (segundos)",
                    axis=alt.Axis(format=".2f"),
                ),
                color=job_color(duration_chart_type),
                tooltip=[
                    "JobNumber:N",
                    alt.Tooltip("DuracionSegundos:Q", format=".2f"),
                    alt.Tooltip("Inicio:T", title="Inicio", format="%Y-%m-%d %H:%M:%S.%L"),
                    alt.Tooltip("Fin:T", title="Fin", format="%Y-%m-%d %H:%M:%S.%L"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(duration_chart, use_container_width=True)

        st.subheader("Duración acumulada por JobNumber (ms)")
        duration_ms_chart_type = select_chart_type("chart_type_duration_ms")
        duration_ms_chart = (
            apply_chart_mark(alt.Chart(metrics_df), duration_ms_chart_type)
            .encode(
                x=alt.X(
                    "JobNumber:N",
                    sort="-y",
                    axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                ),
                y=alt.Y("DuracionTotalMs:Q", title="Duración acumulada (ms)"),
                color=job_color(duration_ms_chart_type),
                tooltip=["JobNumber:N", alt.Tooltip("DuracionTotalMs:Q", format=",.0f")],
            )
            .properties(height=350)
        )
        st.altair_chart(duration_ms_chart, use_container_width=True)

        st.subheader("CPU promedio por JobNumber")
        cpu_chart_type = select_chart_type("chart_type_cpu_average")
        cpu_chart = (
            apply_chart_mark(alt.Chart(metrics_df), cpu_chart_type)
            .transform_calculate(MediaUsoCPUFormato="format(datum.MediaUsoCPU, '.2f') + '%' ")
            .encode(
                x=alt.X(
                    "JobNumber:N",
                    sort="-y",
                    axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                ),
                y=alt.Y(
                    "MediaUsoCPU:Q",
                    axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'"),
                ),
                color=job_color(cpu_chart_type),
                tooltip=[
                    "JobNumber:N",
                    alt.Tooltip("MediaUsoCPUFormato:N", title="CPU promedio"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(cpu_chart, use_container_width=True)

        st.subheader("Pico de uso de CPU (CpuPeakPercent) por JobNumber")
        cpu_peak_data = metrics_df.dropna(subset=["PicoUsoCPU"])
        if cpu_peak_data.empty:
            st.info("Los archivos seleccionados no contienen valores válidos de CpuPeakPercent.")
        else:
            cpu_peak_chart_type = select_chart_type("chart_type_cpu_peak")
            cpu_peak_chart = (
                apply_chart_mark(alt.Chart(cpu_peak_data), cpu_peak_chart_type)
                .encode(
                    x=alt.X(
                        "JobNumber:N",
                        sort="-y",
                        axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                    ),
                    y=alt.Y(
                        "PicoUsoCPU:Q",
                        title="Pico de uso de CPU (%)",
                        axis=alt.Axis(format=".2f", labelExpr="format(datum.value, '.2f') + '%'"),
                    ),
                    color=job_color(cpu_peak_chart_type),
                    tooltip=["JobNumber:N", alt.Tooltip("PicoUsoCPU:Q", title="CpuPeakPercent", format=".2f")],
                )
                .properties(height=350)
            )
            st.altair_chart(cpu_peak_chart, use_container_width=True)

        st.subheader("Tamaño total de archivos por JobNumber")
        input_size_chart_type = select_chart_type("chart_type_input_size")
        input_size_chart = (
            apply_chart_mark(alt.Chart(metrics_df), input_size_chart_type)
            .encode(
                x=alt.X(
                    "JobNumber:N",
                    sort="-y",
                    axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                ),
                y=alt.Y(
                    "TotalInputBytes:Q",
                    title="Tamaño total",
                    axis=alt.Axis(
                        labelExpr=(
                            "datum.value < 1048576 ? format(datum.value / 1024, '.2f') + ' KB' : "
                            "datum.value < 1073741824 ? format(datum.value / 1048576, '.2f') + ' MB' : "
                            "format(datum.value / 1073741824, '.2f') + ' GB'"
                        )
                    ),
                ),
                color=job_color(input_size_chart_type),
                tooltip=["JobNumber:N", alt.Tooltip("TamanoTotal:N", title="Tamaño total")],
            )
            .properties(height=350)
        )
        st.altair_chart(input_size_chart, use_container_width=True)

        st.subheader("Records totales por JobNumber")
        records_chart_type = select_chart_type("chart_type_records")
        records_chart = (
            apply_chart_mark(alt.Chart(metrics_df), records_chart_type)
            .encode(
                x=alt.X(
                    "JobNumber:N",
                    sort="-y",
                    axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
                ),
                y="TotalRecords:Q",
                color=job_color(records_chart_type),
                tooltip=["JobNumber:N", "TotalRecords:Q"],
            )
            .properties(height=350)
        )
        st.altair_chart(records_chart, use_container_width=True)

        st.subheader("Resumen final por JobNumber")
        st.dataframe(
            metrics_df[
                [
                    "JobNumber",
                    "Inicio",
                    "Fin",
                    "RegistrosAnalizados",
                    "MediaUsoCPU",
                    "DuracionTotalMs",
                    "PicoUsoCPU",
                    "TamanoTotal",
                    "TotalRecords",
                    "DuracionMinutos",
                    "Archivos",
                ]
            ],
            column_config={
                "MediaUsoCPU": st.column_config.NumberColumn("MediaUsoCPU", format="%.2f%%"),
                "PicoUsoCPU": st.column_config.NumberColumn("PicoUsoCPU", format="%.2f%%"),
            },
            use_container_width=True,
        )
else:
    st.info("Selecciona uno o varios archivos JSON para comparar métricas por JobNumber.")
