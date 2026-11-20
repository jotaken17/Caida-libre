import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from io import BytesIO

st.set_page_config(
    page_title="Caída Libre",
    page_icon="⚽",
    layout="wide"
)

st.title("🔬 Laboratorio de Caída Libre")
st.subheader("Sistema de medición con Arduino UNO R3")
st.info(
    "Sistema de medición mediante dos sensores infrarrojos. "
    "Los resultados se consultan desde la base de datos compartida."
)

st.sidebar.header("Configuración")
distancia = st.sidebar.number_input(
    "Distancia entre sensores (metros)",
    min_value=0.01,
    max_value=5.0,
    value=0.30,
    step=0.01
)
st.sidebar.caption("La distancia se utiliza como referencia visual. "
                   "Los valores registrados son los enviados por el Arduino.")

@st.cache_resource
def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
    return create_client(url, key)

def obtener_mediciones():
    cliente = conectar_supabase()
    respuesta = (
        cliente.table("mediciones")
        .select("id, created_at, tiempo, velocidad, gravedad")
        .order("created_at", desc=True)
        .limit(1000)
        .execute()
    )
    registros = respuesta.data or []
    if not registros:
        return pd.DataFrame()

    datos = pd.DataFrame(registros)
    datos["Fecha"] = pd.to_datetime(datos["created_at"], errors="coerce")
    datos["Tiempo (s)"] = pd.to_numeric(datos["tiempo"], errors="coerce")
    datos["Velocidad (m/s)"] = pd.to_numeric(datos["velocidad"], errors="coerce")
    datos["Gravedad (m/s²)"] = pd.to_numeric(datos["gravedad"], errors="coerce")
    datos = datos.dropna(subset=["Fecha", "Tiempo (s)", "Velocidad (m/s)", "Gravedad (m/s²)"])
    datos = datos.sort_values("Fecha")
    return datos

@st.fragment(run_every="3s")
def mostrar_resultados():
    st.divider()
    st.subheader("Resultados experimentales")

    try:
        datos = obtener_mediciones()
        st.success("Conectado a Supabase. Actualización automática cada 3 segundos.")

        if not datos.empty:
            ultimo = datos.iloc[-1]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tiempo", f"{ultimo['Tiempo (s)']:.4f} s")
            c2.metric("Velocidad", f"{ultimo['Velocidad (m/s)']:.3f} m/s")
            c3.metric("Gravedad estimada", f"{ultimo['Gravedad (m/s²)']:.3f} m/s²")
            c4.metric("Mediciones", f"{len(datos)}")

            st.subheader("Gráfica de velocidad")
            fig = px.line(
                datos, x="Fecha", y="Velocidad (m/s)",
                markers=True, title="Velocidad registrada"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Gráfica de gravedad")
            fig2 = px.line(
                datos, x="Fecha", y="Gravedad (m/s²)",
                markers=True, title="Gravedad estimada"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Historial de mediciones")
            tabla = datos[[
                "Fecha", "Tiempo (s)", "Velocidad (m/s)", "Gravedad (m/s²)"
            ]].copy()
            tabla["Fecha"] = tabla["Fecha"].dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(tabla.sort_values("Fecha", ascending=False),
                         use_container_width=True, hide_index=True)

            csv = tabla.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Descargar CSV", data=csv,
                file_name="mediciones_caida_libre.csv",
                mime="text/csv"
            )

            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                tabla.to_excel(writer, index=False, sheet_name="Mediciones")
            st.download_button(
                "Descargar Excel", data=excel_buffer.getvalue(),
                file_name="mediciones_caida_libre.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Todavía no hay mediciones registradas en Supabase.")
            st.caption("Cuando el Arduino envíe la primera medición, aparecerá aquí.")
    except KeyError as e:
        st.error(
            f"Falta configurar {e}. En Streamlit Cloud entra a "
            "Settings → Secrets y revisa SUPABASE_URL y "
            "SUPABASE_PUBLISHABLE_KEY."
        )
    except Exception as e:
        st.error("No se pudo consultar Supabase. Verifica la configuración y la conexión.")
        st.caption(f"Detalle técnico: {e}")

    st.caption("Proyecto de Física | Arduino UNO R3 | Dos sensores infrarrojos")

mostrar_resultados()
