import json
import socket
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
MAX_PUNTOS = 50


class DashboardEcosistema:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Dashboard extra del ecosistema")
        self.root.geometry("900x620")
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.datos_ldr: list[float] = []
        self.tiempos: list[str] = []
        self.conectado = False
        self.socket: socket.socket | None = None
        self.cerrando = False

        self.crear_interfaz()
        self.conectar_servidor()

    def crear_interfaz(self) -> None:
        titulo = ttk.Label(
            self.root,
            text="Dashboard histórico del LDR",
            font=("Helvetica", 18, "bold"),
        )
        titulo.pack(pady=(12, 4))

        frame_metricas = ttk.LabelFrame(self.root, text="Métricas", padding=10)
        frame_metricas.pack(fill="x", padx=12, pady=8)

        self.lbl_estado = ttk.Label(frame_metricas, text="Desconectado", font=("Helvetica", 11, "bold"))
        self.lbl_estado.grid(row=0, column=0, padx=12, pady=4, sticky="w")

        self.lbl_ultimo = ttk.Label(frame_metricas, text="Última lectura: -- lux")
        self.lbl_ultimo.grid(row=0, column=1, padx=12, pady=4, sticky="w")

        self.lbl_promedio = ttk.Label(frame_metricas, text="Promedio: -- lux")
        self.lbl_promedio.grid(row=0, column=2, padx=12, pady=4, sticky="w")

        self.lbl_min = ttk.Label(frame_metricas, text="Mínimo: -- lux")
        self.lbl_min.grid(row=1, column=1, padx=12, pady=4, sticky="w")

        self.lbl_max = ttk.Label(frame_metricas, text="Máximo: -- lux")
        self.lbl_max.grid(row=1, column=2, padx=12, pady=4, sticky="w")

        self.lbl_modo = ttk.Label(frame_metricas, text="Modo: --")
        self.lbl_modo.grid(row=1, column=0, padx=12, pady=4, sticky="w")

        for columna in range(3):
            frame_metricas.columnconfigure(columna, weight=1)

        self.fig, self.ax = plt.subplots(figsize=(9, 4.6))
        self.fig.tight_layout(pad=3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.ax.set_title("Evolución de la iluminación")
        self.ax.set_xlabel("Hora")
        self.ax.set_ylabel("Iluminación (lux)")
        self.ax.grid(True, alpha=0.3)
        (self.linea,) = self.ax.plot([], [], linewidth=2)

    def conectar_servidor(self) -> None:
        if self.cerrando or self.conectado:
            return

        threading.Thread(target=self._conectar_en_hilo, daemon=True).start()

    def _conectar_en_hilo(self) -> None:
        try:
            nuevo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            nuevo_socket.settimeout(5)
            nuevo_socket.connect((SERVER_IP, SERVER_PORT))
            nuevo_socket.settimeout(None)

            if self.cerrando:
                nuevo_socket.close()
                return

            self.socket = nuevo_socket
            self.conectado = True
            self.root.after(0, self._mostrar_conectado)
            self.recibir_datos()
        except OSError as error:
            self.conectado = False
            self.root.after(0, lambda: self._mostrar_error(str(error)))
            if not self.cerrando:
                self.root.after(3000, self.conectar_servidor)

    def _mostrar_conectado(self) -> None:
        self.lbl_estado.config(text="Conectado", foreground="green")

    def _mostrar_error(self, mensaje: str) -> None:
        if self.cerrando:
            return
        self.lbl_estado.config(text=f"Desconectado: {mensaje}", foreground="red")

    def recibir_datos(self) -> None:
        buffer = ""
        try:
            while self.conectado and not self.cerrando and self.socket is not None:
                data = self.socket.recv(2048)
                if not data:
                    break

                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    linea = linea.strip()
                    if linea:
                        self.procesar_dato(linea)
        except OSError:
            pass
        finally:
            self.conectado = False
            self._cerrar_socket()
            if not self.cerrando:
                self.root.after(0, lambda: self.lbl_estado.config(text="Desconectado", foreground="red"))
                self.root.after(3000, self.conectar_servidor)

    def procesar_dato(self, mensaje: str) -> None:
        try:
            datos = json.loads(mensaje)
        except json.JSONDecodeError:
            return

        if datos.get("tipo") != "ESTADO":
            return

        try:
            valor = float(datos.get("valor_ldr", 0))
        except (TypeError, ValueError):
            valor = 0.0

        timestamp = str(datos.get("timestamp", datetime.now().isoformat()))
        modo = str(datos.get("modo", "--"))
        buzzer = str(datos.get("buzzer", "OFF"))
        led = str(datos.get("led", "OFF"))

        self.root.after(0, lambda: self.actualizar_interfaz(valor, timestamp, modo, buzzer, led))

    def actualizar_interfaz(
        self,
        valor: float,
        timestamp: str,
        modo: str,
        buzzer: str,
        led: str,
    ) -> None:
        self.datos_ldr.append(valor)
        self.tiempos.append(timestamp[11:19] if len(timestamp) >= 19 else timestamp)

        if len(self.datos_ldr) > MAX_PUNTOS:
            self.datos_ldr = self.datos_ldr[-MAX_PUNTOS:]
            self.tiempos = self.tiempos[-MAX_PUNTOS:]

        self.lbl_ultimo.config(text=f"Última lectura: {valor:.1f} lux")
        self.lbl_promedio.config(text=f"Promedio: {np.mean(self.datos_ldr):.1f} lux")
        self.lbl_min.config(text=f"Mínimo: {min(self.datos_ldr):.1f} lux")
        self.lbl_max.config(text=f"Máximo: {max(self.datos_ldr):.1f} lux")
        self.lbl_modo.config(text=f"Modo: {modo} | Buzzer: {buzzer} | LED: {led}")
        self.actualizar_grafica()

    def actualizar_grafica(self) -> None:
        posiciones = list(range(len(self.datos_ldr)))
        self.linea.set_data(posiciones, self.datos_ldr)
        self.ax.relim()
        self.ax.autoscale_view()

        if posiciones:
            paso = max(1, len(posiciones) // 8)
            ticks = posiciones[::paso]
            etiquetas = self.tiempos[::paso]
            self.ax.set_xticks(ticks)
            self.ax.set_xticklabels(etiquetas, rotation=30, ha="right")

        self.canvas.draw_idle()

    def _cerrar_socket(self) -> None:
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None

    def cerrar(self) -> None:
        self.cerrando = True
        self.conectado = False
        self._cerrar_socket()
        plt.close(self.fig)
        self.root.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    DashboardEcosistema(ventana)
    ventana.mainloop()
