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
                records_count = record.get("Records")
                start = record.get("ProcessingStartUtc") or record.get("ProcessingStartLocal")
                end = record.get("ProcessingEndUtc") or record.get("ProcessingEndLocal")

                if cpu is not None and records_count is not None:
                    rows.append(
                        {
                            "Archivo": file_name,
                            "JobNumber": job_number,
                            "CpuAveragePercent": cpu,
                            "Records": records_count,
                            "Site": record.get("Site", "N/A"),
                            "Status": record.get("Status", "N/A"),
                            "Inicio": start,
                            "Fin": end,
                        }
                    )
        except Exception as exc:
            errors.append(f"{source if isinstance(source, str) else getattr(source, 'name', str(source))}: {exc}")

    df = pd.DataFrame(rows)
    if not df.empty:
        df["CpuAveragePercent"] = pd.to_numeric(df["CpuAveragePercent"], errors="coerce")
        df["Records"] = pd.to_numeric(df["Records"], errors="coerce")
        df = df.dropna(subset=["CpuAveragePercent", "Records"]).reset_index(drop=True)

    if df.empty:
        return df, errors

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
    return grouped, errors


st.set_page_config(page_title="JsonMetrix", page_icon="📊")
st.title("JsonMetrix")
st.write("Carga uno o varios archivos JSON y compara el uso de CPU y la cantidad de registros.")

if st.button("Limpiar todo", type="secondary"):
    st.session_state.pop("selected_paths", None)
    st.session_state.pop("uploaded_files", None)
    st.session_state.pop("file_sources", None)
    st.rerun()

project_root = Path(__file__).resolve().parent
json_candidates = sorted(project_root.rglob("*.json"), key=lambda p: str(p).lower())
options = [str(path) for path in json_candidates]

selected_paths = st.multiselect(
    "Selecciona archivos JSON del proyecto",
    options=options,
    default=[],
    key="selected_paths",
)

uploaded_files = st.file_uploader(
    "O súbelo desde tu equipo (puedes seleccionar varios)",
    type=["json"],
    accept_multiple_files=True,
    key="uploaded_files",
)

file_sources = []
for path in selected_paths:
    file_sources.append(path)
for uploaded in uploaded_files or []:
    file_sources.append(uploaded)
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
                "MediaUsoCPU": st.column_config.NumberColumn("MediaUsoCPU", format="%.2f%%")
            },
            use_container_width=True,
        )

        st.subheader("Duración por JobNumber (segundos)")
        duration_chart = (
            alt.Chart(metrics_df)
            .mark_bar()
            .encode(
                x=alt.X("JobNumber:N", sort="-y"),
                y=alt.Y(
                    "DuracionSegundos:Q",
                    title="Duración (segundos)",
                    axis=alt.Axis(format=".2f"),
                ),
                color="JobNumber:N",
                tooltip=[
                    "JobNumber:N",
                    alt.Tooltip("DuracionSegundos:Q", format=".2f"),
                    "Inicio:T",
                    "Fin:T",
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(duration_chart, use_container_width=True)

        st.subheader("CPU promedio por JobNumber")
        cpu_chart = (
            alt.Chart(metrics_df)
            .transform_calculate(MediaUsoCPUFormato="format(datum.MediaUsoCPU, '.2f') + '%' ")
            .mark_bar()
            .encode(
                x=alt.X("JobNumber:N", sort="-y"),
                y=alt.Y(
                    "MediaUsoCPU:Q",
                    axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'"),
                ),
                color="JobNumber:N",
                tooltip=[
                    "JobNumber:N",
                    alt.Tooltip("MediaUsoCPUFormato:N", title="CPU promedio"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(cpu_chart, use_container_width=True)

        st.subheader("Records totales por JobNumber")
        records_chart = (
            alt.Chart(metrics_df)
            .mark_bar()
            .encode(
                x=alt.X("JobNumber:N", sort="-y"),
                y="TotalRecords:Q",
                color="JobNumber:N",
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
                    "TotalRecords",
                    "DuracionMinutos",
                    "Archivos",
                ]
            ],
            column_config={
                "MediaUsoCPU": st.column_config.NumberColumn("MediaUsoCPU", format="%.2f%%")
            },
            use_container_width=True,
        )
else:
    st.info("Selecciona uno o varios archivos JSON o súbelos desde tu equipo para comparar métricas por JobNumber.")
