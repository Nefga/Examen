import tkinter as tk
from tkinter import ttk
import socket
import threading
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class DashboardEcosistema:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Dashboard del Ecosistema")
        self.root.geometry("800x600")
        
        self.datos_ldr = []
        self.tiempos = []
        self.max_puntos = 50
        
        self.conectado = False
        self.socket = None
        
        self.crear_interfaz()
        self.conectar_servidor()
        
    def crear_interfaz(self):
        # Frame superior - métricas
        frame_metrics = ttk.Frame(self.root)
        frame_metrics.pack(fill="x", padx=10, pady=5)
        
        self.lbl_estado = ttk.Label(frame_metrics, text="🔌 Desconectado", font=("Helvetica", 12))
        self.lbl_estado.pack(side="left", padx=10)
        
        self.lbl_ultimo = ttk.Label(frame_metrics, text="Última lectura: -- lux", font=("Helvetica", 12))
        self.lbl_ultimo.pack(side="left", padx=10)
        
        self.lbl_promedio = ttk.Label(frame_metrics, text="Promedio: --", font=("Helvetica", 12))
        self.lbl_promedio.pack(side="left", padx=10)
        
        self.lbl_min = ttk.Label(frame_metrics, text="Mínimo: --", font=("Helvetica", 12))
        self.lbl_min.pack(side="left", padx=10)
        
        self.lbl_max = ttk.Label(frame_metrics, text="Máximo: --", font=("Helvetica", 12))
        self.lbl_max.pack(side="left", padx=10)
        
        # Gráfica
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
        
        self.ax.set_title("Evolución de la luz (lux)")
        self.ax.set_xlabel("Tiempo")
        self.ax.set_ylabel("Lux")
        self.ax.grid(True, alpha=0.3)
        
        self.linea, = self.ax.plot([], [], 'b-', linewidth=2)
        
    def conectar_servidor(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('127.0.0.1', 5000))
            self.conectado = True
            self.lbl_estado.config(text="✅ Conectado", foreground="green")
            
            threading.Thread(target=self.recibir_datos, daemon=True).start()
        except Exception as e:
            self.lbl_estado.config(text=f"❌ Error: {e}", foreground="red")
            self.root.after(3000, self.conectar_servidor)
    
    def recibir_datos(self):
        buffer = ""
        while self.conectado:
            try:
                data = self.socket.recv(1024).decode()
                buffer += data
                while '\n' in buffer:
                    linea, buffer = buffer.split('\n', 1)
                    if linea.strip():
                        self.procesar_dato(linea)
            except:
                break
        
        self.conectado = False
        self.lbl_estado.config(text="🔌 Desconectado", foreground="red")
        self.root.after(3000, self.conectar_servidor)
    
    def procesar_dato(self, mensaje):
        try:
            datos = json.loads(mensaje)
            if datos.get('tipo') == 'ESTADO':
                valor = datos.get('valor_ldr', 0)
                timestamp = datos.get('timestamp', datetime.now().isoformat())
                
                # Actualizar lista de datos
                self.datos_ldr.append(valor)
                self.tiempos.append(timestamp[11:19])  # HH:MM:SS
                
                if len(self.datos_ldr) > self.max_puntos:
                    self.datos_ldr = self.datos_ldr[-self.max_puntos:]
                    self.tiempos = self.tiempos[-self.max_puntos:]
                
                # Actualizar métricas
                self.lbl_ultimo.config(text=f"Última lectura: {valor:.1f} lux")
                if len(self.datos_ldr) > 1:
                    promedio = np.mean(self.datos_ldr)
                    minimo = min(self.datos_ldr)
                    maximo = max(self.datos_ldr)
                    self.lbl_promedio.config(text=f"Promedio: {promedio:.1f} lux")
                    self.lbl_min.config(text=f"Mínimo: {minimo:.1f} lux")
                    self.lbl_max.config(text=f"Máximo: {maximo:.1f} lux")
                
                # Actualizar gráfica
                self.actualizar_grafica()
                
        except json.JSONDecodeError:
            pass
    
    def actualizar_grafica(self):
        if len(self.datos_ldr) < 2:
            return
        
        self.linea.set_data(range(len(self.datos_ldr)), self.datos_ldr)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xticks(range(0, len(self.datos_ldr), max(1, len(self.datos_ldr)//10)))
        self.ax.set_xticklabels(self.tiempos[::max(1, len(self.tiempos)//10)])
        
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardEcosistema(root)
    root.mainloop()