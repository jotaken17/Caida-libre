
import streamlit as st
import pandas as pd
import plotly.express as px
import serial
import serial.tools.list_ports
import json
import time
import threading
from datetime import datetime
from io import BytesIO


# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

st.set_page_config(
    page_title="Caída Libre",
    page_icon="⚽",
    layout="wide"
)

st.title("🔬 Laboratorio de Caída Libre")
st.subheader("Sistema de medición con Arduino UNO R3")

st.info(
    "Sistema de medición mediante dos sensores infrarrojos. "
    "Los resultados se actualizan automáticamente."
)


# --------------------------------------------------
# ADMINISTRADOR COMPARTIDO DE MEDICIONES
# --------------------------------------------------

class AdministradorDatos:

    def __init__(self):
        self.datos = []
        self.serial = None
        self.hilo = None
        self.bloqueo = threading.Lock()
        self.detener = threading.Event()
        self.error = None

    def agregar(self, registro):
        with self.bloqueo:
            self.datos.append(registro)
            self.datos = self.datos[-1000:]

    def obtener(self):
        with self.bloqueo:
            return list(self.datos)

    def borrar(self):
        with self.bloqueo:
            self.datos.clear()

    def conectado(self):
        with self.bloqueo:
            return (
                self.serial is not None
                and self.serial.is_open
            )

    def conectar(self, puerto):

        if self.conectado():
            return False, "Ya existe una conexión activa."

        try:
            conexion = serial.Serial(
                puerto,
                115200,
                timeout=1
            )

            with self.bloqueo:
                self.serial = conexion
                self.error = None

            self.detener.clear()

            self.hilo = threading.Thread(
                target=self.leer_arduino,
                daemon=True
            )

            self.hilo.start()

            return True, "Arduino conectado correctamente."

        except Exception as e:
            return False, str(e)

    def desconectar(self):

        self.detener.set()

        with self.bloqueo:
            conexion = self.serial
            self.serial = None

        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

        return "Arduino desconectado."

    def leer_arduino(self):

        while not self.detener.is_set():

            with self.bloqueo:
                conexion = self.serial

            if conexion is None:
                break

            try:
                linea = conexion.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if not linea:
                    continue

                dato = json.loads(linea)

                tiempo = float(dato["tiempo"])
                velocidad = float(dato["velocidad"])
                gravedad = float(dato["gravedad"])

                if tiempo <= 0:
                    continue

                registro = {
                    "Fecha": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Tiempo (s)": tiempo,
                    "Velocidad (m/s)": velocidad,
                    "Gravedad (m/s²)": gravedad
                }

                self.agregar(registro)

            except json.JSONDecodeError:
                continue

            except (ValueError, KeyError):
                continue

            except Exception as e:
                with self.bloqueo:
                    self.error = str(e)
                break


@st.cache_resource
def obtener_administrador():
    return AdministradorDatos()


admin = obtener_administrador()


# --------------------------------------------------
# PANEL LATERAL
# --------------------------------------------------

st.sidebar.header("Configuración")

distancia = st.sidebar.number_input(
    "Distancia entre sensores (metros)",
    min_value=0.01,
    max_value=5.0,
    value=0.30,
    step=0.01
)

st.sidebar.divider()
st.sidebar.subheader("Conexión Arduino")

puertos = list(serial.tools.list_ports.comports())
opciones = [p.device for p in puertos]

if opciones:
    puerto = st.sidebar.selectbox(
        "Selecciona el puerto USB",
        opciones
    )
else:
    puerto = None
    st.sidebar.warning(
        "No se detectó ningún Arduino conectado."
    )

if st.sidebar.button(
    "Conectar Arduino",
    disabled=(puerto is None or admin.conectado())
):
    correcto, mensaje = admin.conectar(puerto)

    if correcto:
        st.sidebar.success(mensaje)
    else:
        st.sidebar.error(mensaje)

if st.sidebar.button(
    "Desconectar Arduino",
    disabled=not admin.conectado()
):
    st.sidebar.info(admin.desconectar())


# --------------------------------------------------
# ACTUALIZACIÓN AUTOMÁTICA
# --------------------------------------------------

@st.fragment(run_every="1s")
def mostrar_resultados():

    st.divider()
    st.subheader("Resultados experimentales")

    datos = pd.DataFrame(admin.obtener())

    if admin.conectado():
        st.success("Arduino conectado y escuchando datos.")
    else:
        st.warning("Arduino desconectado.")

    if admin.error:
        st.error(f"Error de comunicación: {admin.error}")

    # Prueba de funcionamiento

    st.subheader("Prueba de funcionamiento")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Agregar medición de prueba"):
            tiempo = 0.247
            velocidad = distancia / tiempo
            gravedad = 2 * distancia / (tiempo ** 2)

            admin.agregar({
                "Fecha": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Tiempo (s)": tiempo,
                "Velocidad (m/s)": velocidad,
                "Gravedad (m/s²)": gravedad
            })

    with col2:
        if st.button("Borrar mediciones"):
            admin.borrar()

    datos = pd.DataFrame(admin.obtener())

    st.divider()

    if not datos.empty:

        ultimo = datos.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Tiempo",
            f"{ultimo['Tiempo (s)']:.4f} s"
        )

        c2.metric(
            "Velocidad",
            f"{ultimo['Velocidad (m/s)']:.3f} m/s"
        )

        c3.metric(
            "Gravedad estimada",
            f"{ultimo['Gravedad (m/s²)']:.3f} m/s²"
        )

        c4.metric(
            "Mediciones",
            len(datos)
        )

        st.subheader("Gráfica de velocidad")

        fig = px.line(
            datos,
            x="Fecha",
            y="Velocidad (m/s)",
            markers=True,
            title="Velocidad registrada"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Gráfica de gravedad")

        fig2 = px.line(
            datos,
            x="Fecha",
            y="Gravedad (m/s²)",
            markers=True,
            title="Gravedad estimada"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

        st.subheader("Historial de mediciones")

        st.dataframe(
            datos,
            use_container_width=True
        )

        # DESCARGA CSV

        csv = datos.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Descargar CSV",
            data=csv,
            file_name="mediciones_caida_libre.csv",
            mime="text/csv"
        )

        # DESCARGA EXCEL

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
            "Descargar Excel",
            data=excel_buffer.getvalue(),
            file_name="mediciones_caida_libre.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:

        st.warning(
            "Todavía no hay mediciones registradas."
        )

    st.caption(
        "Proyecto de Física | Arduino UNO R3 | "
        "Dos sensores infrarrojos"
    )


mostrar_resultados()
