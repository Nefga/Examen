# Ecosistema — Monitoreo y Control con ESP32

Sistema de instrumentación virtual que lee un sensor de luz (LDR) conectado a un
ESP32, calcula lux reales, y expone el estado (luz, buzzer, LED) a tres clientes
distintos (Java, Python y Web) a través de un servidor central en Python.

Repositorio: https://github.com/Nefga/Examen/tree/main

## Arquitectura

```
   ESP32 (examen.ino)
        │  USB / Serial
        ▼
 servidor_prueba.py  ──TCP:5000──┬──► cliente_python.py
  (+ database.py)                ├──► cliente_extra_python.py (dashboard con gráfica)
                                  ├──► ClienteEcosistemaJava.java
                                  └──► cliente_web.js ──Socket.IO:5001──► index.html (navegador)
```

El ESP32 es la única fuente de verdad del estado real (automático o manual);
el servidor solo retransmite lo que el ESP32 reporta.

## Estructura del repositorio

| Archivo | Descripción |
|---|---|
| `examen.ino` | Firmware del ESP32 (lectura del LDR, cálculo de lux, control de buzzer/LED) |
| `servidor_prueba.py` | Servidor central: habla por serial con el ESP32 y por TCP con los clientes |
| `database.py` | Registro de eventos y lecturas en SQLite (`ecosistema.db`) |
| `cliente_python.py` | Cliente de escritorio (Tkinter) con medidor de luz y controles |
| `cliente_extra_python.py` | Dashboard con gráfica en tiempo real (Matplotlib) |
| `ClienteEcosistemaJava.java` | Cliente de escritorio en Java (Swing) |
| `gson-2.10.1.jar` | Dependencia de Java para parsear JSON |
| `cliente_web.js`, `package.json` | Servidor puente Node.js (TCP ↔ Socket.IO) |
| `index.html`, `index.js`, `style.css` | Interfaz web |

## Requisitos

- **Arduino IDE** con soporte para placas ESP32 instalado.
- **Python 3.10+** con los paquetes:
  ```bash
  pip install pyserial matplotlib numpy
  ```
- **Node.js + npm** (para el cliente web).
- **Java JDK 11+** (para el cliente de escritorio Java).

## 1. Subir el firmware al ESP32

1. Abre `examen.ino` en el Arduino IDE.
2. Selecciona tu placa ESP32 y el puerto correspondiente.
3. Antes de subirlo, calibra las constantes `ADC_OSCURO` / `ADC_BRILLANTE` /
   `LUX_OSCURO` / `LUX_BRILLANTE` según tu sensor (ver comentarios dentro del
   archivo).
4. Sube el sketch.

## 2. Levantar el servidor

```bash
pip install pyserial
python servidor_prueba.py COM3
```

Cambia `COM3` por el puerto real donde aparece tu ESP32 (revisa el
Administrador de Dispositivos en Windows, o `/dev/ttyUSB0` / `/dev/ttyACM0`
en Linux/Mac).

El servidor debe quedar escuchando en `127.0.0.1:5000`.

## 3. Cliente Web (Node.js)

```bash
npm install
node cliente_web.js
```

Esto instala `express`, `socket.io` y `nodemon` (definidos en
`package.json`), y levanta el puente en el puerto `5001`. Abre
`http://localhost:5001` en tu navegador para ver `index.html`.

Alternativa con recarga automática:
```bash
npm start
```

## 4. Cliente Python (escritorio)

```bash
python cliente_python.py
```

## 5. Dashboard extra (gráfica en tiempo real)

```bash
python cliente_extra_python.py
```

## 6. Cliente Java

Con `gson-2.10.1.jar` en la misma carpeta:

```bash
javac -cp gson-2.10.1.jar ClienteEcosistemaJava.java
java -cp .;gson-2.10.1.jar ClienteEcosistemaJava      # Windows
java -cp .:gson-2.10.1.jar ClienteEcosistemaJava       # Linux/Mac
```

## Notas

- Todos los clientes se conectan por defecto a `127.0.0.1`. Si vas a
  conectarte desde otra máquina en la misma red, cambia `host` en
  `servidor_prueba.py` a `0.0.0.0`, y la IP en cada cliente por la IP real
  del equipo donde corre el servidor (`ipconfig` / `ifconfig`).
- El botón **"Modo Automático"** en cualquier cliente le devuelve el control
  al ESP32 después de haber forzado el buzzer manualmente.
- Solo un programa puede tener el puerto serial abierto a la vez — cierra el
  Monitor Serial del Arduino IDE antes de correr `servidor_prueba.py`.
