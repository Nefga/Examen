import tkinter as tk
from tkinter import ttk, scrolledtext
import socket
import threading
import json
from datetime import datetime

MAX_LDR = 50   
UMBRAL_ALARMA = 15   


COLOR_NOCHE = (74, 111, 165)   
COLOR_DIA = (244, 184, 96)     


def interpolar_color(pct):
    """Mezcla COLOR_NOCHE -> COLOR_DIA según el porcentaje (0.0 - 1.0)."""
    r = int(COLOR_NOCHE[0] + (COLOR_DIA[0] - COLOR_NOCHE[0]) * pct)
    g = int(COLOR_NOCHE[1] + (COLOR_DIA[1] - COLOR_NOCHE[1]) * pct)
    b = int(COLOR_NOCHE[2] + (COLOR_DIA[2] - COLOR_NOCHE[2]) * pct)
    return f'#{r:02x}{g:02x}{b:02x}'


class BarraNivel(tk.Canvas):
    """Medidor vertical del nivel de luz en lux, con línea de umbral de alarma."""

    def __init__(self, master, ancho=60, alto=320, **kwargs):
        super().__init__(master, width=ancho, height=alto,
                          bg="#0d1420", highlightthickness=0, **kwargs)
        self.ancho = ancho
        self.alto = alto
        self.margen = 6
        self.set_valor(0)

    def set_valor(self, valor):
        valor = max(0, min(MAX_LDR, valor))
        self.delete("all")

        track_x0 = self.margen
        track_x1 = self.ancho - self.margen
        track_y0 = self.margen
        track_y1 = self.alto - self.margen
        track_h = track_y1 - track_y0

        # Track de fondo
        self.create_rectangle(track_x0, track_y0, track_x1, track_y1,
                               fill="#131b2e", outline="")

        pct = valor / MAX_LDR
        fill_h = round(track_h * pct)
        if fill_h > 0:
            color = interpolar_color(pct)
            self.create_rectangle(track_x0, track_y1 - fill_h, track_x1, track_y1,
                                   fill=color, outline="")

        # Línea de umbral de alarma
        y_umbral = track_y1 - round(track_h * (UMBRAL_ALARMA / MAX_LDR))
        self.create_line(track_x0 - 2, y_umbral, track_x1 + 2, y_umbral,
                          fill="#e8735c", width=2)

        # Marcador circular en el nivel actual
        y_marcador = track_y1 - fill_h
        cx = self.ancho / 2
        self.create_oval(cx - 8, y_marcador - 8, cx + 8, y_marcador + 8,
                          fill="white", outline="")

        # Valor numérico
        self.create_text(cx, self.alto - 10, text=f"{valor:.0f}",
                          fill="white", font=("Consolas", 10, "bold"))


class ClienteEcosistemaPy:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Ecosistema - Python")
        self.root.geometry("640x600")
        self.root.resizable(False, False)

        self.socket = None
        self.conectado = False

        self.estado_buzzer = "APAGADO"
        self.estado_led = "APAGADO"
        self.valor_ldr = 0

        self.crear_interfaz()
        self.conectar_servidor()

    def crear_interfaz(self):
        # Título
        ttk.Label(self.root, text="🌿 Control de Ecosistema",
                  font=("Helvetica", 16, "bold")).pack(pady=10)

        # Contenedor principal: medidor a la izquierda, estado/controles a la derecha
        frame_principal = ttk.Frame(self.root)
        frame_principal.pack(fill="both", expand=True, padx=20)

        frame_medidor = ttk.LabelFrame(frame_principal, text="Nivel de luz", padding=10)
        frame_medidor.pack(side="left", fill="y")

        self.barra_nivel = BarraNivel(frame_medidor)
        self.barra_nivel.pack()

        frame_derecha = ttk.Frame(frame_principal)
        frame_derecha.pack(side="left", fill="both", expand=True, padx=(15, 0))

        # Frame de estado
        frame_estado = ttk.LabelFrame(frame_derecha, text="Estado Actual", padding=10)
        frame_estado.pack(fill="x", pady=10)

        self.lbl_ldr = ttk.Label(frame_estado, text="Luz: -- lux")
        self.lbl_ldr.pack(anchor="w")

        self.lbl_buzzer = ttk.Label(frame_estado, text="Buzzer: APAGADO", foreground="red")
        self.lbl_buzzer.pack(anchor="w")

        self.lbl_led = ttk.Label(frame_estado, text="LED: APAGADO", foreground="red")
        self.lbl_led.pack(anchor="w")

        self.lbl_conexion = ttk.Label(frame_estado, text="Estado: Desconectado", foreground="orange")
        self.lbl_conexion.pack(anchor="w")

        # Frame de control
        frame_control = ttk.LabelFrame(frame_derecha, text="Control Manual", padding=10)
        frame_control.pack(fill="x", pady=10)

        btn_frame = ttk.Frame(frame_control)
        btn_frame.pack()

        self.btn_on = ttk.Button(btn_frame, text="🔊 Activar Alarma",
                                  command=lambda: self.enviar_comando("BUZZER_ON"))
        self.btn_on.grid(row=0, column=0, padx=5, pady=5)

        self.btn_off = ttk.Button(btn_frame, text="🔇 Desactivar Alarma",
                                   command=lambda: self.enviar_comando("BUZZER_OFF"))
        self.btn_off.grid(row=0, column=1, padx=5, pady=5)

        self.btn_auto = ttk.Button(btn_frame, text="↺ Modo Automático",
                                    command=lambda: self.enviar_comando("AUTO"))
        self.btn_auto.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # Historial de eventos
        frame_log = ttk.LabelFrame(self.root, text="Historial de Eventos", padding=10)
        frame_log.pack(fill="both", expand=True, padx=20, pady=10)

        self.txt_log = scrolledtext.ScrolledText(frame_log, height=10, state='disabled')
        self.txt_log.pack(fill="both", expand=True)

    def conectar_servidor(self):
        """Conecta al servidor en un hilo separado"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('127.0.0.1', 5000))
            self.conectado = True
            self.lbl_conexion.config(text="Estado: Conectado ✅", foreground="green")
            self.agregar_log("✅ Conectado al servidor")

            # Iniciar hilo para recibir datos
            threading.Thread(target=self.recibir_datos, daemon=True).start()
        except Exception as e:
            self.lbl_conexion.config(text=f"Error: {e}", foreground="red")
            self.agregar_log(f"❌ Error de conexión: {e}")
            # Reintentar después de 3 segundos
            self.root.after(3000, self.conectar_servidor)

    def recibir_datos(self):
        """Recibe datos del servidor continuamente"""
        buffer = ""
        while self.conectado:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    linea, buffer = buffer.split('\n', 1)
                    if linea.strip():
                        self.procesar_mensaje(linea)
            except:
                break

        self.conectado = False
        self.lbl_conexion.config(text="Estado: Desconectado ❌", foreground="red")
        self.agregar_log("❌ Desconectado del servidor")
        self.root.after(3000, self.conectar_servidor)

    def procesar_mensaje(self, mensaje):
        """Procesa mensajes JSON del servidor"""
        try:
            datos = json.loads(mensaje)
            if datos.get('tipo') == 'ESTADO':
                self.valor_ldr = datos.get('valor_ldr', 0)
                self.estado_buzzer = datos.get('buzzer', 'OFF')
                self.estado_led = datos.get('led', 'OFF')

                self.lbl_ldr.config(text=f"Luz: {self.valor_ldr:.1f} lux")
                self.barra_nivel.set_valor(self.valor_ldr)

                # Actualizar colores
                if self.estado_buzzer == 'ON':
                    self.lbl_buzzer.config(text="Buzzer: ENCENDIDO 🔔", foreground="green")
                    self.lbl_led.config(text="LED: ENCENDIDO 💡", foreground="green")
                else:
                    self.lbl_buzzer.config(text="Buzzer: APAGADO 🔕", foreground="red")
                    self.lbl_led.config(text="LED: APAGADO ⚫", foreground="red")

                timestamp = datos.get('timestamp', datetime.now().isoformat())
                self.agregar_log(f"[{timestamp[:19]}] Luz: {self.valor_ldr:.1f} lux | Buzzer: {self.estado_buzzer}")
        except json.JSONDecodeError:
            pass

    def enviar_comando(self, comando):
        if not self.conectado:
            self.agregar_log("⚠️ No conectado al servidor")
            return

        try:
            self.socket.send((comando + '\n').encode())
            self.agregar_log(f"📤 Comando enviado: {comando}")
        except Exception as e:
            self.agregar_log(f"❌ Error enviando comando: {e}")

    def agregar_log(self, mensaje):
        self.txt_log.config(state='normal')
        self.txt_log.insert('end', f"{mensaje}\n")
        self.txt_log.see('end')
        self.txt_log.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteEcosistemaPy(root)
    root.mainloop()
