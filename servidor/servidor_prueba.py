import socket
import threading
import serial
import time
import json
from database import Database
from datetime import datetime

class ServidorEcosistema:
    def __init__(self, host='127.0.0.1', puerto_tcp=5000, puerto_serial='COM4'):
        self.host = host
        self.puerto_tcp = puerto_tcp
        self.puerto_serial = puerto_serial
        self.db = Database()
        self.clientes = []
        self.arduino_conectado = False
        self.ultimo_valor_ldr = 0
        self.estado_buzzer = False
        self.estado_led = False
        self.lock = threading.Lock()
        self.db_lock = threading.Lock()

        # Intentar conectar con Arduino
        self.conectar_arduino()

    def conectar_arduino(self):
        try:
            self.ser = serial.Serial(self.puerto_serial, 9600, timeout=1)
            time.sleep(2)  

         
            n = 0
            while n < 11:
                try:
                    self.ser.readline()
                except Exception:
                    pass
                n += 1

            self.arduino_conectado = True
            print(f"✅ Arduino conectado en {self.puerto_serial}")
            
            # Iniciar hilo para leer datos del Arduino
            threading.Thread(target=self.leer_arduino, daemon=True).start()
        except Exception as e:
            print(f"⚠️ No se pudo conectar al Arduino: {e}")
            print("   El servidor funcionará en modo simulación")

    def leer_arduino(self):
        """Lee datos del Arduino continuamente"""
        while self.arduino_conectado:
            try:
                if self.ser.in_waiting > 0:
                    linea = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if linea.startswith("LUX:"):
                        # Formato: "LUX:23.4,ADC:1800,ESTADO:ON"
                        partes = linea.split(",")
                        lux = float(partes[0].split(":")[1])
                        adc_crudo = None
                        estado_reportado = None
                        for parte in partes[1:]:
                            if parte.startswith("ADC:"):
                                adc_crudo = parte.split(":")[1]
                            elif parte.startswith("ESTADO:"):
                                estado_reportado = parte.split(":")[1] == "ON"

                        with self.lock:
                            self.ultimo_valor_ldr = lux
                        with self.db_lock:
                            self.db.registrar_lectura(lux)

                        if adc_crudo is not None:
                            print(f"📊 Lux: {lux:.1f}  (ADC crudo: {adc_crudo})")
                        else:
                            print(f"📊 Lux: {lux:.1f}")

                     
                        if estado_reportado is not None and estado_reportado != self.estado_buzzer:
                            self.estado_buzzer = estado_reportado
                            self.estado_led = estado_reportado
                            with self.db_lock:
                                self.db.registrar_evento(
                                    tipo="AUTOMATICO",
                                    valor_ldr=lux,
                                    estado_buzzer="ON" if self.estado_buzzer else "OFF",
                                    estado_led="ON" if self.estado_led else "OFF",
                                    origen="ESP32"
                                )

                   
                        self.broadcast_estado()
                time.sleep(0.1)
            except Exception as e:
                print(f"Error leyendo Arduino: {e}")
                time.sleep(1)

    def enviar_a_arduino(self, comando):
        """Envía un comando al Arduino"""
        if self.arduino_conectado:
            try:
                self.ser.write((comando + '\n').encode())
                print(f"📤 Enviado a Arduino: {comando}")
                return True
            except Exception as e:
                print(f"Error enviando a Arduino: {e}")
        return False

    def broadcast_estado(self):
        """Envía el estado actual a todos los clientes TCP"""
        estado = {
            'tipo': 'ESTADO',
            'valor_ldr': self.ultimo_valor_ldr,
            'buzzer': 'ON' if self.estado_buzzer else 'OFF',
            'led': 'ON' if self.estado_led else 'OFF',
            'timestamp': datetime.now().isoformat()
        }
        mensaje = json.dumps(estado) + '\n'
        for cliente in self.clientes[:]:
            try:
                cliente.send(mensaje.encode())
            except:
                self.clientes.remove(cliente)

    def manejar_cliente(self, conn, addr):
        """Maneja la conexión con un cliente TCP"""
        print(f"🔗 Cliente conectado: {addr}")
        self.clientes.append(conn)
        
        # Enviar estado inicial
        self.broadcast_estado()

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                comando = data.decode('utf-8').strip()
                print(f"📩 Comando recibido de {addr}: {comando}")
                
                # Procesar comando
                if comando in ['BUZZER_ON', 'BUZZER_OFF']:
                    es_on = comando == 'BUZZER_ON'
                    self.estado_buzzer = es_on
                    self.estado_led = es_on
                    
                    if self.enviar_a_arduino(comando):
                        with self.db_lock:
                            self.db.registrar_evento(
                                tipo="MANUAL",
                                comando=comando,
                                valor_ldr=self.ultimo_valor_ldr,
                                estado_buzzer="ON" if es_on else "OFF",
                                estado_led="ON" if es_on else "OFF",
                                origen=f"Cliente {addr[0]}"
                            )
                        self.broadcast_estado()
                        conn.send(b"OK\n")
                    else:
                        conn.send(b"ERROR\n")
                elif comando == 'AUTO':
                    # Le devuelve el control al ESP32 (deja de forzar ON/OFF)
                    if self.enviar_a_arduino(comando):
                        with self.db_lock:
                            self.db.registrar_evento(
                                tipo="MANUAL",
                                comando=comando,
                                valor_ldr=self.ultimo_valor_ldr,
                                origen=f"Cliente {addr[0]}"
                            )
                        conn.send(b"OK\n")
                    else:
                        conn.send(b"ERROR\n")
                else:
                    conn.send(b"COMANDO_DESCONOCIDO\n")

        except Exception as e:
            print(f"Error con cliente {addr}: {e}")
        finally:
            if conn in self.clientes:
                self.clientes.remove(conn)
            conn.close()
            print(f"🔌 Cliente desconectado: {addr}")

    def iniciar(self):
        """Inicia el servidor TCP"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.puerto_tcp))
            s.listen()
            print(f"🌐 Servidor escuchando en {self.host}:{self.puerto_tcp}")
            print("   (Presiona Ctrl+C para detener)")
            
            try:
                while True:
                    conn, addr = s.accept()
                    threading.Thread(target=self.manejar_cliente, 
                                   args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                print("\n🛑 Apagando servidor...")
                self.db.cerrar()
                if self.arduino_conectado:
                    self.ser.close()

if __name__ == "__main__":
    import sys
    puerto_serial = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
    servidor = ServidorEcosistema(puerto_serial=puerto_serial)
    servidor.iniciar()
