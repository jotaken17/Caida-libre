import json
import os
import sys
import time

import serial
import serial.tools.list_ports
from supabase import create_client


BAUDIOS = 115200
TABLA = "mediciones"


def elegir_puerto():
    puertos = list(serial.tools.list_ports.comports())
    if not puertos:
        print("No se detectaron puertos seriales.")
        print("Conecta el Arduino por USB y vuelve a ejecutar el programa.")
        sys.exit(1)

    print("\nPuertos detectados:")
    for i, puerto in enumerate(puertos, start=1):
        print(f"{i}. {puerto.device} - {puerto.description}")

    while True:
        opcion = input("Escribe el número del puerto del Arduino: ").strip()
        if opcion.isdigit() and 1 <= int(opcion) <= len(puertos):
            return puertos[int(opcion) - 1].device
        print("Opción no válida. Inténtalo otra vez.")


def main():
    url = os.getenv("SUPABASE_URL")
    clave = os.getenv("SUPABASE_SECRET_KEY")

    if not url or not clave:
        print("Faltan las variables SUPABASE_URL o SUPABASE_SECRET_KEY.")
        print("Configúralas en la Terminal antes de ejecutar este programa.")
        sys.exit(1)

    cliente = create_client(url, clave)
    puerto = elegir_puerto()

    print(f"\nConectando a {puerto} a {BAUDIOS} baudios...")
    print("IMPORTANTE: cierra el Monitor Serial del IDE de Arduino si está abierto.")
    try:
        with serial.Serial(puerto, BAUDIOS, timeout=1) as arduino:
            time.sleep(2)
            print("Conexión establecida. Esperando mediciones...")
            while True:
                linea = arduino.readline().decode("utf-8", errors="ignore").strip()
                if not linea:
                    continue

                try:
                    dato = json.loads(linea)
                    tiempo = float(dato["tiempo"])
                    velocidad = float(dato["velocidad"])
                    gravedad = float(dato["gravedad"])

                    if tiempo <= 0:
                        print("Medición ignorada: tiempo no válido.")
                        continue

                    registro = {
                        "tiempo": tiempo,
                        "velocidad": velocidad,
                        "gravedad": gravedad
                    }
                    resultado = cliente.table(TABLA).insert(registro).execute()
                    print(
                        "Medición guardada: "
                        f"tiempo={tiempo:.4f} s | "
                        f"velocidad={velocidad:.3f} m/s | "
                        f"gravedad={gravedad:.3f} m/s²"
                    )
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    # Ignora líneas que no sean un JSON de medición válido.
                    continue
                except Exception as error:
                    print(f"Error al guardar en Supabase: {error}")
                    print("El programa seguirá intentando con la siguiente medición.")

    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    except serial.SerialException as error:
        print(f"No se pudo leer el puerto serial: {error}")
        print("Comprueba el cable USB, el puerto y que no esté ocupado por otro programa.")


if __name__ == "__main__":
    main()
