import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_name="ecosistema.db"):
       
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.crear_tablas()

    def crear_tablas(self):
       
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tipo TEXT NOT NULL,
                comando TEXT,
                valor_ldr INTEGER,
                estado_buzzer TEXT,
                estado_led TEXT,
                origen TEXT
            )
        ''')

       
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                valor_ldr INTEGER
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')

        self.conn.commit()

    def registrar_evento(self, tipo, comando=None, valor_ldr=None, 
                          estado_buzzer=None, estado_led=None, origen=None):
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO eventos 
            (timestamp, tipo, comando, valor_ldr, estado_buzzer, estado_led, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, tipo, comando, valor_ldr, estado_buzzer, estado_led, origen))
        self.conn.commit()
        return self.cursor.lastrowid

    def registrar_lectura(self, valor_ldr):
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO lecturas (timestamp, valor_ldr)
            VALUES (?, ?)
        ''', (timestamp, valor_ldr))
        self.conn.commit()

    def obtener_ultimos_eventos(self, limite=50):
        self.cursor.execute('''
            SELECT * FROM eventos ORDER BY timestamp DESC LIMIT ?
        ''', (limite,))
        return self.cursor.fetchall()

    def obtener_lecturas_historicas(self, limite=100):
        self.cursor.execute('''
            SELECT * FROM lecturas ORDER BY timestamp DESC LIMIT ?
        ''', (limite,))
        return self.cursor.fetchall()

    def obtener_estadisticas(self):
        self.cursor.execute('SELECT COUNT(*) FROM eventos')
        total_eventos = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT AVG(valor_ldr) FROM lecturas')
        promedio_ldr = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM eventos WHERE comando = "BUZZER_ON"')
        activaciones = self.cursor.fetchone()[0]
        
        return {
            'total_eventos': total_eventos,
            'promedio_ldr': promedio_ldr or 0,
            'activaciones_buzzer': activaciones
        }

    def cerrar(self):
        self.conn.close()
