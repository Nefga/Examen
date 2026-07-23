[README.md](https://github.com/user-attachments/files/30290140/README.md)
# Monitoreo y control del ecosistema

Sistema integrado para un **ESP32 con LDR, buzzer y LED**. Conserva la interfaz web y el cliente TCP de LabVIEW del proyecto original, y agrega las dos interfaces gráficas solicitadas: **Python** y **Java**.

## Arquitectura

```text
LDR + buzzer + LED
        │
      ESP32
        │ Serial 9600
        ▼
puente_esp32_socketio.py
        │ Socket.IO :5001
        ▼
Servidor Node.js
 ├─ Web / Socket.IO :5001
 ├─ Python y Java TCP JSON :5000
 └─ LabVIEW TCP legado :5002
```

Todos los clientes pueden estar abiertos al mismo tiempo. Los comandos de cualquiera de ellos llegan al ESP32 y el estado actualizado se distribuye a todas las interfaces.

## Conexiones

- **LDR:** `3.3 V -> LDR -> nodo -> GPIO34`; del nodo se coloca una resistencia de `10 kΩ` a GND.
- **LED:** `GPIO26 -> resistencia de 220 a 330 Ω -> ánodo del LED`; cátodo a GND.
- **Buzzer activo:** señal a `GPIO25`, GND común y alimentación según el módulo.
- Si el buzzer consume más corriente que la permitida por el GPIO, usar transistor/MOSFET; no alimentarlo directamente desde el pin.

## Puertos e interfaces

| Puerto | Interfaz | Formato |
|---|---|---|
| 5000 | Clientes Java y Python | Una línea JSON por lectura y comandos de texto |
| 5001 | Página web y puente serial | HTTP + Socket.IO |
| 5002 | LabVIEW original | Lectura numérica fija de 4 bytes; comandos `P` y `A` |

## Orden correcto de ejecución

### 1. Cargar el programa al ESP32

Abrir `ESP32/monitoreo_ldr_buzzer_led.ino`, seleccionar la placa ESP32 y cargarlo. El monitor serial debe mostrar líneas como:

```text
LUX:12.4,ADC:1910,ESTADO:ON,MODO:AUTO
```

### 2. Instalar y ejecutar el servidor

```bat
cd Server_2
npm install
npm start
```

Abrir la interfaz web en `http://localhost:5001`.

### 3. Instalar y ejecutar el puente serial

```bat
cd puente_serial
py -m pip install -r requirements.txt
py puente_esp32_socketio.py --puerto COM5
```

Cambiar `COM5` por el puerto que aparezca en Arduino IDE si es diferente.

### 4. Abrir el cliente Python

No necesita paquetes externos; Tkinter viene con la instalación normal de Python para Windows.

```bat
cd clientes\python
py cliente_ecosistema.py
```

### 5. Compilar y abrir el cliente Java

No necesita Gson ni librerías externas.

```bat
cd clientes\java
javac ClienteEcosistemaJava.java
java ClienteEcosistemaJava
```

### 6. Abrir LabVIEW

Abrir `LabVIEW/tcp_client_Rx_y_Tx_1_5.vi` y ejecutar el VI con servidor `localhost` y puerto `5002`. El protocolo original `P/A` se mantiene:

- `P`: activar alarma.
- `A`: desactivar alarma.

## Comandos aceptados

- `BUZZER_ON`, `P` o `ON`: activa buzzer y LED en modo manual.
- `BUZZER_OFF`, `A` u `OFF`: apaga buzzer y LED en modo manual.
- `AUTO`: devuelve el control al LDR.

En modo automático, buzzer y LED se encienden cuando la iluminación baja de **15 lux**.

## Calibración

El sketch usa una aproximación de `1 a 50 lux` entre ADC `200 y 2880`. Si la aplicación del celular y el ESP32 no coinciden, ajustar `ADC_OSCURO` y `ADC_BRILLANTE` en el sketch. Las interfaces no requieren cambios mientras el máximo siga siendo 50 lux.

## Prueba funcional recomendada

1. Encender servidor y puente: las interfaces deben mostrar “Conectado”.
2. Tapar el LDR: el valor debe bajar de 15 lux y encender buzzer/LED en AUTO.
3. Iluminar el LDR: el valor debe subir y apagar buzzer/LED.
4. En Python pulsar “Activar alarma”: todas las interfaces deben mostrar ON/MANUAL.
5. En Java pulsar “Desactivar alarma”: todas deben mostrar OFF/MANUAL.
6. En LabVIEW mandar `P` y `A`: el hardware y los demás clientes deben reflejar el cambio.
7. Pulsar “Modo automático” en web, Python o Java: el LDR recupera el control.
