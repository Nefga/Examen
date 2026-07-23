import json
import os
import queue
import socket
import threading
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk

SERVER_IP = os.getenv("ECOSISTEMA_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("ECOSISTEMA_PORT", "5000"))
MAX_LDR = 50
UMBRAL_ALARMA = 15
COLOR_NOCHE = (74, 111, 165)
COLOR_DIA = (244, 184, 96)


def interpolar_color(pct):
    r = int(COLOR_NOCHE[0] + (COLOR_DIA[0] - COLOR_NOCHE[0]) * pct)
    g = int(COLOR_NOCHE[1] + (COLOR_DIA[1] - COLOR_NOCHE[1]) * pct)
    b = int(COLOR_NOCHE[2] + (COLOR_DIA[2] - COLOR_NOCHE[2]) * pct)
    return f"#{r:02x}{g:02x}{b:02x}"


class BarraNivel(tk.Canvas):
    def __init__(self, master, ancho=70, alto=330, **kwargs):
        super().__init__(master, width=ancho, height=alto, bg="#0d1420", highlightthickness=0, **kwargs)
        self.ancho = ancho
        self.alto = alto
        self.margen = 7
        self.set_valor(0)

    def set_valor(self, valor):
        valor = max(0, min(MAX_LDR, float(valor)))
        self.delete("all")
        x0, x1 = self.margen, self.ancho - self.margen
        y0, y1 = self.margen, self.alto - self.margen
        alto_track = y1 - y0
        pct = valor / MAX_LDR
        alto_relleno = round(alto_track * pct)

        self.create_rectangle(x0, y0, x1, y1, fill="#131b2e", outline="")
        if alto_relleno:
            self.create_rectangle(x0, y1 - alto_relleno, x1, y1, fill=interpolar_color(pct), outline="")

        y_umbral = y1 - round(alto_track * (UMBRAL_ALARMA / MAX_LDR))
        self.create_line(x0 - 2, y_umbral, x1 + 2, y_umbral, fill="#e8735c", width=3)
        y_marcador = y1 - alto_relleno
        centro = self.ancho / 2
        self.create_oval(centro - 8, y_marcador - 8, centro + 8, y_marcador + 8, fill="white", outline="")
        self.create_text(centro, self.alto - 12, text=f"{valor:.1f}", fill="white", font=("Consolas", 10, "bold"))


class ClienteEcosistema:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Ecosistema - Python")
        self.root.geometry("700x650")
        self.root.resizable(False, False)

        self.sock = None
        self.conectado = False
        self.intentando_conectar = False
        self.cerrando = False
        self.cola = queue.Queue()
        self.bloqueo_socket = threading.Lock()

        self.crear_interfaz()
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.root.after(100, self.procesar_cola)
        self.conectar_servidor()

    def crear_interfaz(self):
        ttk.Label(self.root, text="🌿 Control de Ecosistema", font=("Segoe UI", 18, "bold")).pack(pady=12)

        principal = ttk.Frame(self.root)
        principal.pack(fill="both", expand=True, padx=20)

        frame_medidor = ttk.LabelFrame(principal, text="Nivel de luz", padding=10)
        frame_medidor.pack(side="left", fill="y")
        self.barra = BarraNivel(frame_medidor)
        self.barra.pack()
        ttk.Label(frame_medidor, text="Línea roja = 15 lux").pack(pady=(8, 0))

        derecha = ttk.Frame(principal)
        derecha.pack(side="left", fill="both", expand=True, padx=(16, 0))

        estado = ttk.LabelFrame(derecha, text="Estado actual", padding=12)
        estado.pack(fill="x", pady=(0, 10))
        self.lbl_conexion = ttk.Label(estado, text="Estado: Desconectado", foreground="orange")
        self.lbl_ldr = ttk.Label(estado, text="Luz: -- lux")
        self.lbl_adc = ttk.Label(estado, text="ADC: --")
        self.lbl_buzzer = ttk.Label(estado, text="Buzzer: APAGADO", foreground="red")
        self.lbl_led = ttk.Label(estado, text="LED: APAGADO", foreground="red")
        self.lbl_modo = ttk.Label(estado, text="Modo: AUTO")
        for etiqueta in (self.lbl_conexion, self.lbl_ldr, self.lbl_adc, self.lbl_buzzer, self.lbl_led, self.lbl_modo):
            etiqueta.pack(anchor="w", pady=2)

        control = ttk.LabelFrame(derecha, text="Control manual", padding=12)
        control.pack(fill="x")
        ttk.Button(control, text="🔊 Activar alarma", command=lambda: self.enviar_comando("BUZZER_ON")).pack(fill="x", pady=4)
        ttk.Button(control, text="🔇 Desactivar alarma", command=lambda: self.enviar_comando("BUZZER_OFF")).pack(fill="x", pady=4)
        ttk.Button(control, text="↺ Modo automático", command=lambda: self.enviar_comando("AUTO")).pack(fill="x", pady=4)

        frame_log = ttk.LabelFrame(self.root, text="Historial de eventos", padding=10)
        frame_log.pack(fill="both", expand=True, padx=20, pady=12)
        self.txt_log = scrolledtext.ScrolledText(frame_log, height=11, state="disabled", font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)

    def conectar_servidor(self):
        if self.cerrando or self.conectado or self.intentando_conectar:
            return
        self.intentando_conectar = True
        threading.Thread(target=self._conectar_en_hilo, daemon=True).start()

    def _conectar_en_hilo(self):
        try:
            nuevo_socket = socket.create_connection((SERVER_IP, SERVER_PORT), timeout=4)
            nuevo_socket.settimeout(None)
            nuevo_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            with self.bloqueo_socket:
                self.sock = nuevo_socket
            self.conectado = True
            self.cola.put(("conexion", True, f"Conectado a {SERVER_IP}:{SERVER_PORT}"))
            threading.Thread(target=self.recibir_datos, daemon=True).start()
        except OSError as error:
            self.cola.put(("conexion", False, f"Error de conexión: {error}"))
        finally:
            self.intentando_conectar = False

    def recibir_datos(self):
        buffer = ""
        try:
            while self.conectado and not self.cerrando:
                with self.bloqueo_socket:
                    sock = self.sock
                if sock is None:
                    break
                data = sock.recv(2048)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if not linea.strip():
                        continue
                    try:
                        self.cola.put(("estado", json.loads(linea)))
                    except json.JSONDecodeError:
                        self.cola.put(("log", f"Mensaje inválido: {linea}"))
        except OSError as error:
            if not self.cerrando:
                self.cola.put(("log", f"Conexión interrumpida: {error}"))
        finally:
            self.desconectar()
            if not self.cerrando:
                self.cola.put(("conexion", False, "Servidor desconectado; reintentando..."))

    def procesar_cola(self):
        while True:
            try:
                evento = self.cola.get_nowait()
            except queue.Empty:
                break

            tipo = evento[0]
            if tipo == "estado":
                self.actualizar_estado(evento[1])
            elif tipo == "conexion":
                conectado, mensaje = evento[1], evento[2]
                self.lbl_conexion.config(
                    text="Estado: Conectado ✅" if conectado else "Estado: Desconectado ❌",
                    foreground="green" if conectado else "red",
                )
                self.agregar_log(mensaje)
                if not conectado and not self.cerrando:
                    self.root.after(3000, self.conectar_servidor)
            elif tipo == "log":
                self.agregar_log(evento[1])

        if not self.cerrando:
            self.root.after(100, self.procesar_cola)

    def actualizar_estado(self, datos):
        if datos.get("tipo") != "ESTADO":
            return
        lux = float(datos.get("valor_ldr", 0))
        adc = int(datos.get("adc", 0))
        buzzer = datos.get("buzzer", "OFF")
        led = datos.get("led", "OFF")
        modo = datos.get("modo", "AUTO")

        self.lbl_ldr.config(text=f"Luz: {lux:.1f} lux")
        self.lbl_adc.config(text=f"ADC: {adc}")
        self.lbl_buzzer.config(text=f"Buzzer: {'ENCENDIDO 🔔' if buzzer == 'ON' else 'APAGADO 🔕'}", foreground="green" if buzzer == "ON" else "red")
        self.lbl_led.config(text=f"LED: {'ENCENDIDO 💡' if led == 'ON' else 'APAGADO ⚫'}", foreground="green" if led == "ON" else "red")
        self.lbl_modo.config(text=f"Modo: {modo}")
        self.barra.set_valor(lux)

        timestamp = datos.get("timestamp", datetime.now().isoformat())
        self.agregar_log(f"[{timestamp[:19]}] Luz {lux:.1f} lux | ADC {adc} | Alarma {buzzer} | {modo}")

    def enviar_comando(self, comando):
        if not self.conectado:
            self.agregar_log("⚠️ No hay conexión con el servidor")
            return
        try:
            with self.bloqueo_socket:
                if self.sock is None:
                    raise ConnectionError("socket no disponible")
                self.sock.sendall((comando + "\n").encode("utf-8"))
            self.agregar_log(f"📤 Comando enviado: {comando}")
        except OSError as error:
            self.agregar_log(f"❌ Error enviando comando: {error}")
            self.desconectar()

    def agregar_log(self, mensaje):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", mensaje + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def desconectar(self):
        self.conectado = False
        with self.bloqueo_socket:
            if self.sock is not None:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None

    def cerrar(self):
        self.cerrando = True
        self.desconectar()
        self.root.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    ClienteEcosistema(ventana)
    ventana.mainloop()
