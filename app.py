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


def chart_palette():
    active_theme = st.context.theme or {}
    theme_base = active_theme.get("type") or st.get_option("theme.base")
    if theme_base == "dark":
        return [
            "#39FF14",
            "#00E5FF",
            "#FF2E88",
            "#FFF01F",
            "#B967FF",
            "#FF7A00",
            "#00FFB3",
            "#FF4D4D",
        ]
    return [
        "#123B5D",
        "#552583",
        "#006B5B",
        "#8A3A00",
        "#9B174C",
        "#3D4F00",
        "#174A8B",
        "#5E3A1C",
    ]


def job_color(chart_type):
    palette = chart_palette()
    if chart_type in ("Línea", "Área"):
        return alt.value(palette[0])
    return alt.Color(
        "JobNumber:N",
        scale=alt.Scale(range=palette),
        legend=alt.Legend(labelLimit=0, labelFontSize=12),
    )


def render_comparison_chart(
    data,
    metric,
    title,
    tooltip_format=None,
    axis_format=None,
    axis_label_expr=None,
    category_field="JobNumber",
):
    y_axis = alt.Axis(title=title)
    if axis_format:
        y_axis.format = axis_format
    if axis_label_expr:
        y_axis.labelExpr = axis_label_expr

    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_field}:N",
                sort="-y",
                axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
            ),
            xOffset=alt.XOffset("Comparacion:N"),
            y=alt.Y(f"{metric}:Q", axis=y_axis),
            color=alt.Color(
                "Comparacion:N",
                scale=alt.Scale(domain=["A", "B"], range=chart_palette()[:2]),
                legend=alt.Legend(title="Archivo"),
            ),
            tooltip=[
                alt.Tooltip(f"{category_field}:N", title=category_field),
                alt.Tooltip("Comparacion:N", title="Archivo"),
                alt.Tooltip(f"{metric}:Q", title=title, format=tooltip_format),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)


def render_cpu_chart(data, metric, title, chart_key, category_field, tooltip_title):
    chart_type = select_chart_type(chart_key)
    chart_color = job_color(chart_type) if category_field == "JobNumber" else alt.value(chart_palette()[0])
    chart = (
        apply_chart_mark(alt.Chart(data), chart_type)
        .encode(
            x=alt.X(
                f"{category_field}:N",
                sort="-y",
                axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
            ),
            y=alt.Y(
                f"{metric}:Q",
                title=title,
                axis=alt.Axis(format=".2f", labelExpr="format(datum.value, '.2f') + '%'"),
            ),
            color=chart_color,
            tooltip=[
                alt.Tooltip(f"{category_field}:N", title=category_field),
                alt.Tooltip(f"{metric}:Q", title=tooltip_title, format=".2f"),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)


def render_duration_chart(data, metric, title, chart_key, category_field, tooltip_title):
    chart_type = select_chart_type(chart_key)
    chart_color = job_color(chart_type) if category_field == "JobNumber" else alt.value(chart_palette()[0])
    tooltip = [alt.Tooltip(f"{category_field}:N", title=category_field)]
    if category_field == "Registro":
        tooltip.append(alt.Tooltip("JobNumber:N", title="JobNumber"))
    tooltip.append(alt.Tooltip(f"{metric}:Q", title=tooltip_title, format=",.2f"))
    chart = (
        apply_chart_mark(alt.Chart(data), chart_type)
        .encode(
            x=alt.X(
                f"{category_field}:N",
                sort="-y",
                axis=alt.Axis(labelLimit=0, labelAngle=-45, labelFontSize=12),
            ),
            y=alt.Y(f"{metric}:Q", title=title),
            color=chart_color,
            tooltip=tooltip,
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)


def render_peak_vs_threshold_time_chart(data, series_field=None, per_record=False):
    if per_record:
        data = data.rename(
            columns={
                "CpuPeakPercent": "PicoMaximoCPU",
                "CpuTimeAboveThresholdMs": "TiempoSobreUmbralMs",
                "CpuThresholdPercent": "UmbralCPUPercent",
            }
        )
    chart_data = data.dropna(subset=["PicoMaximoCPU", "TiempoSobreUmbralMs"])
    if chart_data.empty:
        st.info("Los archivos no contienen valores de pico máximo y tiempo sobre umbral.")
        return

    tooltip = [
        alt.Tooltip("JobNumber:N", title="JobNumber"),
        alt.Tooltip("PicoMaximoCPU:Q", title="Pico máximo CPU (%)", format=".2f"),
        alt.Tooltip("UmbralCPUPercent:Q", title="Umbral CPU (%)", format=".2f"),
        alt.Tooltip("TiempoSobreUmbralMs:Q", title="Tiempo sobre umbral (ms)", format=",.0f"),
    ]
    if per_record and "Registro" in chart_data.columns:
        tooltip.insert(1, alt.Tooltip("Registro:N", title="Registro"))
    encodings = {
        "x": alt.X(
            "PicoMaximoCPU:Q",
            title="Pico máximo de CPU (%)",
            axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'"),
        ),
        "y": alt.Y("TiempoSobreUmbralMs:Q", title="Tiempo sobre umbral (ms)"),
        "tooltip": tooltip,
    }
    if series_field:
        tooltip.insert(1, alt.Tooltip(f"{series_field}:N", title="Archivo"))
        encodings["color"] = alt.Color(
            f"{series_field}:N",
            scale=alt.Scale(domain=["A", "B"], range=chart_palette()[:2]),
            legend=alt.Legend(title="Archivo"),
        )
    else:
        encodings["color"] = alt.value(chart_palette()[0])

    chart = (
        alt.Chart(chart_data)
        .mark_circle(size=110, filled=True)
        .encode(**encodings)
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)


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
                cpu_time_above_threshold_ms = record.get("CpuTimeAboveThresholdMs")
                cpu_threshold_percent = record.get("CpuThresholdPercent")
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
                            "Registro": (
                                f"{file_name} · {record.get('File') or record.get('WorkItemId') or 'Registro'}"
                                f" · {len(rows) + 1}"
                            ),
                            "JobNumber": job_number,
                            "CpuAveragePercent": cpu,
                            "DurationMs": duration_ms,
                            "CpuPeakPercent": cpu_peak,
                            "CpuTimeAboveThresholdMs": cpu_time_above_threshold_ms,
                            "CpuThresholdPercent": cpu_threshold_percent,
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
            "CpuTimeAboveThresholdMs",
            "CpuThresholdPercent",
            "InputBytes",
            "Records",
        ]
        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.dropna(subset=["CpuAveragePercent", "Records"]).reset_index(drop=True)

    if df.empty:
        return df, errors, df

    has_details = df.groupby("JobNumber")["EsResumen"].transform(lambda values: (~values).any())
    df = df.loc[~df["EsResumen"] | ~has_details].reset_index(drop=True)

    df["Inicio_ts"] = pd.to_datetime(df["Inicio"], errors="coerce")
    df["Fin_ts"] = pd.to_datetime(df["Fin"], errors="coerce")
    df = df.dropna(subset=["Inicio_ts", "Fin_ts"]).reset_index(drop=True)

    if df.empty:
        return df, errors, df

    df["DuracionRegistroSegundos"] = (df["Fin_ts"] - df["Inicio_ts"]).dt.total_seconds()
    records_df = df.copy()
    df["DuracionCPUPonderadaMs"] = df["DurationMs"].where(
        df["DurationMs"].gt(0) & df["CpuAveragePercent"].notna(),
        0,
    )
    df["CPUPonderada"] = df["CpuAveragePercent"].fillna(0) * df["DuracionCPUPonderadaMs"]
    grouped = (
        df.groupby("JobNumber", as_index=False)
        .agg(
            Inicio=("Inicio_ts", "min"),
            Fin=("Fin_ts", "max"),
            MediaUsoCPU=("CpuAveragePercent", "mean"),
            CPUPonderada=("CPUPonderada", "sum"),
            DuracionCPUPonderadaMs=("DuracionCPUPonderadaMs", "sum"),
            DuracionPromedioMs=("DurationMs", "mean"),
            DuracionPromedioSegundos=("DuracionRegistroSegundos", "mean"),
            PicoUsoCPU=("CpuPeakPercent", "mean"),
            PicoMaximoCPU=("CpuPeakPercent", "max"),
            TiempoSobreUmbralMs=("CpuTimeAboveThresholdMs", lambda values: values.sum(min_count=1)),
            UmbralCPUPercent=("CpuThresholdPercent", "max"),
            TotalInputBytes=("InputBytes", "sum"),
            TotalRecords=("Records", "sum"),
            RegistrosAnalizados=("Records", "count"),
            Archivos=("Archivo", "nunique"),
            Sitios=("Site", "nunique"),
        )
        .sort_values("TotalRecords", ascending=False)
        .reset_index(drop=True)
    )

    cpu_con_duracion = grouped["DuracionCPUPonderadaMs"] > 0
    grouped.loc[cpu_con_duracion, "MediaUsoCPU"] = (
        grouped.loc[cpu_con_duracion, "CPUPonderada"]
        / grouped.loc[cpu_con_duracion, "DuracionCPUPonderadaMs"]
    )
    grouped = grouped.drop(columns=["CPUPonderada", "DuracionCPUPonderadaMs"])
    grouped["DuracionTranscurridaMs"] = (grouped["Fin"] - grouped["Inicio"]).dt.total_seconds() * 1000
    grouped["DuracionMinutos"] = ((grouped["Fin"] - grouped["Inicio"]).dt.total_seconds() / 60).round(2)
    grouped["TamanoTotal"] = grouped["TotalInputBytes"].map(format_file_size)
    return grouped, errors, records_df


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
    st.session_state.pop("comparison_file_a", None)
    st.session_state.pop("comparison_file_b", None)
    st.session_state.pop("app_mode", None)
    st.rerun()

app_mode = st.radio(
    "Modo",
    ["Analizar archivos", "Comparar 2 archivos"],
    horizontal=True,
    key="app_mode",
)

file_sources = []
comparison_ready = False
if app_mode == "Comparar 2 archivos":
    file_col_a, file_col_b = st.columns(2)
    with file_col_a:
        comparison_file_a = st.file_uploader(
            "Archivo A",
            type=["json"],
            key="comparison_file_a",
        )
    with file_col_b:
        comparison_file_b = st.file_uploader(
            "Archivo B",
            type=["json"],
            key="comparison_file_b",
        )

    comparison_ready = comparison_file_a is not None and comparison_file_b is not None
    if comparison_ready:
        metrics_a, errors_a, records_a = build_metrics_by_job([comparison_file_a])
        metrics_b, errors_b, records_b = build_metrics_by_job([comparison_file_b])
        for error in errors_a + errors_b:
            st.warning(f"No se pudo procesar un archivo: {error}")

        if metrics_a.empty or metrics_b.empty:
            st.error("No se encontraron métricas válidas en ambos archivos para compararlos.")
        else:
            st.caption(f"A: {comparison_file_a.name} | B: {comparison_file_b.name}")
            comparison_fields = [
                "Inicio",
                "Fin",
                "MediaUsoCPU",
                "DuracionTranscurridaMs",
                "DuracionPromedioMs",
                "PicoUsoCPU",
                "PicoMaximoCPU",
                "TiempoSobreUmbralMs",
                "UmbralCPUPercent",
                "TamanoTotal",
                "TotalInputBytes",
                "TotalRecords",
            ]
            comparison_a = metrics_a[["JobNumber", *comparison_fields]].rename(
                columns={field: f"{field} A" for field in comparison_fields}
            )
            comparison_b = metrics_b[["JobNumber", *comparison_fields]].rename(
                columns={field: f"{field} B" for field in comparison_fields}
            )
            comparison_df = comparison_a.merge(comparison_b, on="JobNumber", how="outer")

            delta_fields = [
                ("MediaUsoCPU", "Diferencia CPU (%)"),
                ("DuracionTranscurridaMs", "Diferencia duración transcurrida (ms)"),
                ("DuracionPromedioMs", "Diferencia duración promedio (ms)"),
                ("PicoUsoCPU", "Diferencia pico promedio CPU (%)"),
                ("PicoMaximoCPU", "Diferencia pico máximo CPU (%)"),
                ("TiempoSobreUmbralMs", "Diferencia tiempo sobre umbral (ms)"),
                ("TotalInputBytes", "Diferencia tamaño (bytes)"),
                ("TotalRecords", "Diferencia records"),
            ]
            for field, delta_name in delta_fields:
                comparison_df[delta_name] = comparison_df[f"{field} B"] - comparison_df[f"{field} A"]

            st.subheader("Comparación por JobNumber")
            display_fields = [
                "Inicio",
                "Fin",
                "MediaUsoCPU",
                "DuracionTranscurridaMs",
                "DuracionPromedioMs",
                "PicoUsoCPU",
                "PicoMaximoCPU",
                "TiempoSobreUmbralMs",
                "UmbralCPUPercent",
                "TamanoTotal",
                "TotalRecords",
            ]
            display_config = {
                "MediaUsoCPU A": st.column_config.NumberColumn("CPU media ponderada", format="%.2f%%"),
                "MediaUsoCPU B": st.column_config.NumberColumn("CPU media ponderada", format="%.2f%%"),
                "PicoUsoCPU A": st.column_config.NumberColumn("Pico promedio CPU", format="%.2f%%"),
                "PicoUsoCPU B": st.column_config.NumberColumn("Pico promedio CPU", format="%.2f%%"),
                "PicoMaximoCPU A": st.column_config.NumberColumn("Pico máximo CPU", format="%.2f%%"),
                "PicoMaximoCPU B": st.column_config.NumberColumn("Pico máximo CPU", format="%.2f%%"),
                "TiempoSobreUmbralMs A": st.column_config.NumberColumn("Tiempo sobre umbral (ms)", format="%.0f"),
                "TiempoSobreUmbralMs B": st.column_config.NumberColumn("Tiempo sobre umbral (ms)", format="%.0f"),
                "UmbralCPUPercent A": st.column_config.NumberColumn("Umbral CPU", format="%.2f%%"),
                "UmbralCPUPercent B": st.column_config.NumberColumn("Umbral CPU", format="%.2f%%"),
                "DuracionTranscurridaMs A": st.column_config.NumberColumn("Duración transcurrida (ms)", format="%.0f"),
                "DuracionTranscurridaMs B": st.column_config.NumberColumn("Duración transcurrida (ms)", format="%.0f"),
                "DuracionPromedioMs A": st.column_config.NumberColumn("Duración promedio (ms)", format="%.2f"),
                "DuracionPromedioMs B": st.column_config.NumberColumn("Duración promedio (ms)", format="%.2f"),
                "TotalRecords A": st.column_config.NumberColumn("Records", format="%.0f"),
                "TotalRecords B": st.column_config.NumberColumn("Records", format="%.0f"),
            }
            comparison_col_a, comparison_col_b = st.columns(2)
            with comparison_col_a:
                st.markdown("**Archivo A**")
                columns_a = ["JobNumber"] + [f"{field} A" for field in display_fields]
                st.dataframe(
                    comparison_df[columns_a],
                    column_config=display_config,
                    use_container_width=True,
                    hide_index=True,
                )
            with comparison_col_b:
                st.markdown("**Archivo B**")
                columns_b = ["JobNumber"] + [f"{field} B" for field in display_fields]
                st.dataframe(
                    comparison_df[columns_b],
                    column_config=display_config,
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("**Diferencias (B - A)**")
            difference_columns = ["JobNumber"] + [delta_name for _, delta_name in delta_fields]
            st.dataframe(
                comparison_df[difference_columns],
                column_config={
                    "Diferencia CPU (%)": st.column_config.NumberColumn("CPU (%)", format="%.2f"),
                    "Diferencia duración transcurrida (ms)": st.column_config.NumberColumn(
                        "Duración transcurrida (ms)", format="%.0f"
                    ),
                    "Diferencia duración promedio (ms)": st.column_config.NumberColumn(
                        "Duración promedio (ms)", format="%.2f"
                    ),
                    "Diferencia pico promedio CPU (%)": st.column_config.NumberColumn(
                        "Pico promedio CPU (%)", format="%.2f"
                    ),
                    "Diferencia pico máximo CPU (%)": st.column_config.NumberColumn(
                        "Pico máximo CPU (%)", format="%.2f"
                    ),
                    "Diferencia tiempo sobre umbral (ms)": st.column_config.NumberColumn(
                        "Tiempo sobre umbral (ms)", format="%.0f"
                    ),
                    "Diferencia tamaño (bytes)": st.column_config.NumberColumn("Tamaño (bytes)", format="%.0f"),
                    "Diferencia records": st.column_config.NumberColumn("Records", format="%.0f"),
                },
                use_container_width=True,
                hide_index=True,
            )

            comparison_chart_data = pd.concat(
                [
                    metrics_a.assign(Comparacion="A"),
                    metrics_b.assign(Comparacion="B"),
                ],
                ignore_index=True,
            )
            comparison_record_data = pd.concat(
                [
                    records_a.assign(Comparacion="A"),
                    records_b.assign(Comparacion="B"),
                ],
                ignore_index=True,
            )
            st.subheader("Gráficas comparativas")
            chart_view = st.radio(
                "Ver gráficas",
                ["Por registro", "Por promedio"],
                horizontal=True,
                index=1,
                key="comparison_chart_view",
            )
            if chart_view == "Por registro":
                render_comparison_chart(
                    comparison_record_data.dropna(subset=["DurationMs"]),
                    "DurationMs",
                    "Duración por registro individual (ms)",
                    tooltip_format=",.2f",
                    axis_format=",.2f",
                    category_field="Registro",
                )
                render_comparison_chart(
                    comparison_record_data.dropna(subset=["CpuAveragePercent"]),
                    "CpuAveragePercent",
                    "CPU promedio por registro (%)",
                    tooltip_format=".2f",
                    axis_format=".2f",
                    axis_label_expr="format(datum.value, '.2f') + '%' ",
                    category_field="Registro",
                )
                render_comparison_chart(
                    comparison_record_data.dropna(subset=["CpuPeakPercent"]),
                    "CpuPeakPercent",
                    "Pico de CPU por registro (%)",
                    tooltip_format=".2f",
                    axis_format=".2f",
                    axis_label_expr="format(datum.value, '.2f') + '%' ",
                    category_field="Registro",
                )
            else:
                render_comparison_chart(
                    comparison_chart_data,
                    "DuracionPromedioMs",
                    "Duración promedio por JobNumber (ms)",
                    tooltip_format=",.2f",
                    axis_format=",.2f",
                )
                render_comparison_chart(
                    comparison_chart_data,
                    "MediaUsoCPU",
                    "CPU promedio ponderado (%)",
                    tooltip_format=".2f",
                    axis_format=".2f",
                    axis_label_expr="format(datum.value, '.2f') + '%' ",
                )
                render_comparison_chart(
                    comparison_chart_data.dropna(subset=["PicoUsoCPU"]),
                    "PicoUsoCPU",
                    "Pico promedio de CPU (%)",
                    tooltip_format=".2f",
                    axis_format=".2f",
                    axis_label_expr="format(datum.value, '.2f') + '%' ",
                )
            render_comparison_chart(
                comparison_chart_data,
                "TotalInputBytes",
                "Tamaño de archivos",
                tooltip_format=",.0f",
                axis_label_expr=(
                    "datum.value < 1048576 ? format(datum.value / 1024, '.2f') + ' KB' : "
                    "datum.value < 1073741824 ? format(datum.value / 1048576, '.2f') + ' MB' : "
                    "format(datum.value / 1073741824, '.2f') + ' GB'"
                ),
            )
            render_comparison_chart(
                comparison_chart_data,
                "TotalRecords",
                "Records totales",
                tooltip_format=",.0f",
                axis_format=",.0f",
            )
            st.subheader("Pico máximo de CPU y tiempo sobre umbral")
            st.caption("El tiempo se mide sobre CpuThresholdPercent, no sobre el pico máximo de CPU.")
            render_peak_vs_threshold_time_chart(comparison_chart_data, series_field="Comparacion")
    else:
        st.info("Carga los archivos A y B para ver su comparación por JobNumber.")
else:
    uploaded_files = st.file_uploader(
        "Selecciona uno o varios archivos JSON",
        type=["json"],
        accept_multiple_files=True,
        key="uploaded_files",
    )
    file_sources = list(uploaded_files or [])

st.session_state["file_sources"] = file_sources

if app_mode == "Analizar archivos" and file_sources:
    metrics_df, errors, records_df = build_metrics_by_job(file_sources)

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
                "MediaUsoCPU": st.column_config.NumberColumn("CPU media ponderada", format="%.2f%%"),
                "PicoUsoCPU": st.column_config.NumberColumn("Pico promedio CPU", format="%.2f%%"),
                "DuracionTranscurridaMs": st.column_config.NumberColumn(
                    "Duración transcurrida (ms)", format="%.0f"
                ),
                "DuracionPromedioMs": st.column_config.NumberColumn("Duración promedio (ms)", format="%.2f"),
            },
            use_container_width=True,
        )

        chart_view = st.radio(
            "Ver gráficas",
            ["Por registro", "Por promedio"],
            horizontal=True,
            index=1,
            key="analysis_chart_view",
        )
        if chart_view == "Por registro":
            st.subheader("Duración por registro individual (ms)")
            render_duration_chart(
                records_df.dropna(subset=["DurationMs"]),
                "DurationMs",
                "Duración del registro (ms)",
                "chart_type_duration_record",
                "Registro",
                "Duración del registro",
            )
        else:
            st.subheader("Duración promedio por registro y JobNumber (segundos)")
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
                        "DuracionPromedioSegundos:Q",
                        title="Duración promedio (segundos)",
                        axis=alt.Axis(format=".2f"),
                    ),
                    color=job_color(duration_chart_type),
                    tooltip=[
                        "JobNumber:N",
                        alt.Tooltip("DuracionPromedioSegundos:Q", title="Duración promedio (s)", format=".2f"),
                        alt.Tooltip("Inicio:T", title="Inicio", format="%Y-%m-%d %H:%M:%S.%L"),
                        alt.Tooltip("Fin:T", title="Fin", format="%Y-%m-%d %H:%M:%S.%L"),
                    ],
                )
                .properties(height=350)
            )
            st.altair_chart(duration_chart, use_container_width=True)

            st.subheader("Duración promedio por JobNumber (ms)")
            render_duration_chart(
                metrics_df,
                "DuracionPromedioMs",
                "Duración promedio (ms)",
                "chart_type_duration_ms",
                "JobNumber",
                "Duración promedio por JobNumber",
            )

        st.subheader("Uso de CPU")
        if chart_view == "Por registro":
            render_cpu_chart(
                records_df.dropna(subset=["CpuAveragePercent"]),
                "CpuAveragePercent",
                "CPU promedio (%)",
                "chart_type_cpu_average_record",
                "Registro",
                "CPU promedio del registro",
            )
        else:
            render_cpu_chart(
                metrics_df,
                "MediaUsoCPU",
                "CPU promedio ponderado (%)",
                "chart_type_cpu_average_job",
                "JobNumber",
                "CPU promedio ponderado",
            )

        st.subheader("Picos de uso de CPU")
        record_cpu_peak_data = records_df.dropna(subset=["CpuPeakPercent"])
        job_cpu_peak_data = metrics_df.dropna(subset=["PicoUsoCPU"])
        cpu_peak_data = record_cpu_peak_data if chart_view == "Por registro" else job_cpu_peak_data
        if cpu_peak_data.empty:
            st.info("Los archivos seleccionados no contienen valores válidos de CpuPeakPercent.")
        else:
            if chart_view == "Por registro":
                render_cpu_chart(
                    record_cpu_peak_data,
                    "CpuPeakPercent",
                    "Pico de CPU (%)",
                    "chart_type_cpu_peak_record",
                    "Registro",
                    "Pico de CPU del registro",
                )
            else:
                render_cpu_chart(
                    job_cpu_peak_data,
                    "PicoUsoCPU",
                    "Pico promedio de CPU (%)",
                    "chart_type_cpu_peak_job",
                    "JobNumber",
                    "Pico promedio CPU",
                )

        st.subheader("Pico máximo de CPU y tiempo sobre umbral")
        st.caption("El tiempo se mide sobre CpuThresholdPercent, no sobre el pico máximo de CPU.")
        if chart_view == "Por registro":
            render_peak_vs_threshold_time_chart(records_df, per_record=True)
        else:
            render_peak_vs_threshold_time_chart(metrics_df)

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
                    "DuracionTranscurridaMs",
                    "DuracionPromedioMs",
                    "PicoUsoCPU",
                    "PicoMaximoCPU",
                    "TiempoSobreUmbralMs",
                    "UmbralCPUPercent",
                    "TamanoTotal",
                    "TotalRecords",
                    "DuracionMinutos",
                    "Archivos",
                ]
            ],
            column_config={
                "MediaUsoCPU": st.column_config.NumberColumn("CPU media ponderada", format="%.2f%%"),
                "PicoUsoCPU": st.column_config.NumberColumn("Pico promedio CPU", format="%.2f%%"),
                "PicoMaximoCPU": st.column_config.NumberColumn("Pico máximo CPU", format="%.2f%%"),
                "TiempoSobreUmbralMs": st.column_config.NumberColumn("Tiempo sobre umbral (ms)", format="%.0f"),
                "UmbralCPUPercent": st.column_config.NumberColumn("Umbral CPU", format="%.2f%%"),
                "DuracionTranscurridaMs": st.column_config.NumberColumn(
                    "Duración transcurrida (ms)", format="%.0f"
                ),
                "DuracionPromedioMs": st.column_config.NumberColumn("Duración promedio (ms)", format="%.2f"),
            },
            use_container_width=True,
        )
elif app_mode == "Analizar archivos":
    st.info("Selecciona uno o varios archivos JSON para comparar métricas por JobNumber.")
