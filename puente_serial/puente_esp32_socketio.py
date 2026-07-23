"""Puente entre el ESP32 por Serial y el servidor Node/Socket.IO."""

import argparse
import re
import threading
import time
from datetime import datetime

import serial
import socketio

PATRON_ESTADO = re.compile(
    r"LUX:(?P<lux>[\d.]+),ADC:(?P<adc>\d+),ESTADO:(?P<estado>ON|OFF)(?:,MODO:(?P<modo>AUTO|MANUAL))?",
    re.IGNORECASE,
)


def crear_argumentos():
    parser = argparse.ArgumentParser(description="Puente ESP32 -> servidor de monitoreo")
    parser.add_argument("--puerto", default="COM5", help="Puerto serial, por ejemplo COM5")
    parser.add_argument("--baudios", type=int, default=9600)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--servidor", type=int, default=5001)
    return parser.parse_args()


def main():
    args = crear_argumentos()
    socket_io = socketio.Client(reconnection=True, reconnection_attempts=0, logger=False, engineio_logger=False)

    print(f"Abriendo ESP32 en {args.puerto} a {args.baudios} baudios...")
    esp32 = serial.Serial(args.puerto, args.baudios, timeout=0.5)
    time.sleep(2.0)  # El ESP32 puede reiniciarse al abrir el puerto.
    esp32.reset_input_buffer()
    print("ESP32 conectado.")

    bloqueo_serial = threading.Lock()
    activo = True

    def recibir_comando(valor):
        comando = str(valor).strip().upper()
        equivalencias = {"P": "BUZZER_ON", "A": "BUZZER_OFF", "ON": "BUZZER_ON", "OFF": "BUZZER_OFF"}
        comando = equivalencias.get(comando, comando)
        if comando not in {"BUZZER_ON", "BUZZER_OFF", "AUTO", "R"}:
            print(f"Comando ignorado: {comando}")
            return
        with bloqueo_serial:
            esp32.write((comando + "\n").encode("ascii"))
            esp32.flush()
        print(f"Servidor -> ESP32: {comando}")

    @socket_io.event
    def connect():
        socket_io.emit("soy_arduino", "ESP32_LDR")
        print("Servidor Socket.IO conectado y puente registrado.")

    @socket_io.event
    def disconnect():
        print("Servidor Socket.IO desconectado; se intentará reconectar.")

    socket_io.on("comando", recibir_comando)
    print(f"Conectando al servidor Socket.IO http://{args.host}:{args.servidor}...")
    socket_io.connect(f"http://{args.host}:{args.servidor}", transports=["polling", "websocket"])

    try:
        while activo:
            with bloqueo_serial:
                linea_bytes = esp32.readline()
            if not linea_bytes:
                continue

            linea = linea_bytes.decode("utf-8", errors="replace").strip()
            coincidencia = PATRON_ESTADO.fullmatch(linea)
            if coincidencia:
                estado = coincidencia.group("estado").upper()
                paquete = {
                    "tipo": "ESTADO",
                    "valor_ldr": float(coincidencia.group("lux")),
                    "adc": int(coincidencia.group("adc")),
                    "buzzer": estado,
                    "led": estado,
                    "modo": (coincidencia.group("modo") or "AUTO").upper(),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                socket_io.emit("desde_arduino", paquete)
                print(
                    f"Luz={paquete['valor_ldr']:.1f} lux | ADC={paquete['adc']} | "
                    f"Alarma={paquete['buzzer']} | Modo={paquete['modo']}"
                )
                continue

            # Compatibilidad con el sketch antiguo que devolvía solo un número.
            try:
                valor = float(linea)
                socket_io.emit(
                    "desde_arduino",
                    {
                        "tipo": "ESTADO",
                        "valor_ldr": valor,
                        "adc": round(valor),
                        "buzzer": "OFF",
                        "led": "OFF",
                        "modo": "AUTO",
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    },
                )
            except ValueError:
                print(f"Línea serial no reconocida: {linea}")
    except KeyboardInterrupt:
        print("\nCerrando puente...")
    finally:
        activo = False
        esp32.close()
        socket_io.disconnect()


if __name__ == "__main__":
    main()
