
import streamlit as st
import pandas as pd
import plotly.express as px
import serial
import serial.tools.list_ports
import json
import time
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="Caída Libre",
    page_icon="⚽",
    layout="wide"
)

st.title(" Laboratorio de Caída Libre")
st.subheader("Sistema de medición con Arduino UNO R3")

st.info(
    "Esta página recibe los datos enviados por Arduino mediante USB. "
    "Puedes probar la página sin conectar el Arduino."
)

# Distancia entre sensores
distancia = st.sidebar.number_input(
    "Distancia entre sensores (metros)",
    min_value=0.01,
    max_value=5.0,
    value=0.30,
    step=0.01
)

st.sidebar.write("### Conexión Arduino")

puertos = list(serial.tools.list_ports.comports())
opciones = [p.device for p in puertos]

puerto = st.sidebar.selectbox(
    "Selecciona el puerto USB",
    opciones if opciones else ["Sin Arduino conectado"]
)

conectar = st.sidebar.button("Conectar Arduino")

if "datos" not in st.session_state:
    st.session_state.datos = []

if "conexion" not in st.session_state:
    st.session_state.conexion = None

if conectar:
    if puerto != "Sin Arduino conectado":
        try:
            st.session_state.conexion = serial.Serial(
                puerto, 115200, timeout=1
            )
            time.sleep(2)
            st.sidebar.success("Arduino conectado")
        except Exception as e:
            st.sidebar.error(f"No se pudo conectar: {e}")
    else:
        st.sidebar.warning("No se detectó Arduino")

if st.sidebar.button("Desconectar Arduino"):
    if st.session_state.conexion:
        st.session_state.conexion.close()
        st.session_state.conexion = None
        st.sidebar.success("Arduino desconectado")

# Lectura de datos del Arduino
if st.session_state.conexion:
    try:
        linea = st.session_state.conexion.readline().decode(
            "utf-8", errors="ignore"
        ).strip()

        if linea:
            dato = json.loads(linea)

            registro = {
                "Fecha": datetime.now().strftime("%H:%M:%S"),
                "Tiempo (s)": float(dato["tiempo"]),
                "Velocidad (m/s)": float(dato["velocidad"]),
                "Gravedad (m/s²)": float(dato["gravedad"])
            }

            st.session_state.datos.append(registro)
            st.session_state.datos = st.session_state.datos[-1000:]

    except (ValueError, KeyError, json.JSONDecodeError):
        pass
    except Exception as e:
        st.warning(f"Error de lectura: {e}")

# Modo de prueba
st.divider()
st.subheader("Prueba de funcionamiento")

if st.button("Agregar medición de prueba"):
    tiempo = 0.247
    velocidad = distancia / tiempo
    gravedad = 2 * distancia / (tiempo ** 2)

    st.session_state.datos.append({
        "Fecha": datetime.now().strftime("%H:%M:%S"),
        "Tiempo (s)": tiempo,
        "Velocidad (m/s)": velocidad,
        "Gravedad (m/s²)": gravedad
    })

if st.button("Borrar mediciones"):
    st.session_state.datos = []

# Resultados
datos = pd.DataFrame(st.session_state.datos)

st.divider()
st.subheader(" Resultados experimentales")

if not datos.empty:
    ultimo = datos.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Tiempo", f"{ultimo['Tiempo (s)']:.4f} s")
    c2.metric("Velocidad", f"{ultimo['Velocidad (m/s)']:.3f} m/s")
    c3.metric("Gravedad estimada", f"{ultimo['Gravedad (m/s²)']:.3f} m/s²")
    c4.metric("Mediciones", len(datos))

    st.subheader("Gráfica de velocidad")

    fig = px.line(
        datos,
        x="Fecha",
        y="Velocidad (m/s)",
        markers=True,
        title="Velocidad registrada"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader(" Gráfica de gravedad")

    fig2 = px.line(
        datos,
        x="Fecha",
        y="Gravedad (m/s²)",
        markers=True,
        title="Gravedad estimada"
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Historial de mediciones")
    st.dataframe(datos, use_container_width=True)

    # Descargar CSV
    csv = datos.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar CSV",
        data=csv,
        file_name="mediciones_caida_libre.csv",
        mime="text/csv"
    )

    # Descargar Excel (corregido)
    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:
        datos.to_excel(
            writer,
            index=False,
            sheet_name="Mediciones"
        )

    st.download_button(
        label="Descargar Excel",
        data=excel_buffer.getvalue(),
        file_name="mediciones_caida_libre.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.warning(
        "Todavía no hay mediciones. Agrega una medición de prueba."
    )

st.caption(
    "Proyecto de Física | Arduino UNO R3 | Dos sensores infrarrojos"
)
