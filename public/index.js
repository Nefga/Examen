var socket = io.connect('http://localhost:5001', { forceNew: true });

const LDR_MAX = 50;   // debe coincidir con LUX_BRILLANTE del sketch (el ESP32 nunca reporta más que esto)
const UMBRAL_ALARMA = 15;   // debe coincidir con UMBRAL_LUX del sketch

const fill = document.getElementById('medidor_fill');
const marcador = document.getElementById('medidor_marcador');
const umbral = document.getElementById('medidor_umbral');
const valorTxt = document.getElementById('div_ldr_valor');
const pillConexion = document.getElementById('pill_conexion');
const divBuzzer = document.getElementById('div_buzzer');
const divLed = document.getElementById('div_led');
const divLog = document.getElementById('div_log');

// Coloca la línea de umbral una sola vez (200 / 1023 del alto de la barra)
umbral.style.bottom = (UMBRAL_ALARMA / LDR_MAX * 100) + '%';

function agregarLog(mensaje) {
    const linea = document.createElement('div');
    const hora = new Date().toLocaleTimeString();
    linea.textContent = `[${hora}] ${mensaje}`;
    divLog.prepend(linea);
    while (divLog.childNodes.length > 60) {
        divLog.removeChild(divLog.lastChild);
    }
}

function actualizarMedidor(valorLdr) {
    const pct = Math.max(0, Math.min(100, (valorLdr / LDR_MAX) * 100));
    fill.style.height = pct + '%';
    marcador.style.bottom = pct + '%';
    valorTxt.textContent = valorLdr.toFixed(1) + ' lux';
}

function actualizarEstado(datos) {
    if (typeof datos.valor_ldr === 'number') {
        actualizarMedidor(datos.valor_ldr);
    }
    if (datos.buzzer) {
        divBuzzer.textContent = datos.buzzer === 'ON' ? 'ENCENDIDO' : 'APAGADO';
        divBuzzer.className = 'dato ' + (datos.buzzer === 'ON' ? 'on' : 'off');
    }
    if (datos.led) {
        divLed.textContent = datos.led === 'ON' ? 'ENCENDIDO' : 'APAGADO';
        divLed.className = 'dato ' + (datos.led === 'ON' ? 'on' : 'off');
    }
    agregarLog(`Luz: ${datos.valor_ldr.toFixed(1)} lux · Buzzer: ${datos.buzzer}`);
}

// Función para encender (activar alarma)
function encender() {
    socket.emit('comando', 'BUZZER_ON');
    agregarLog('Comando enviado: BUZZER_ON');
}

// Función para apagar (desactivar alarma)
function apagar() {
    socket.emit('comando', 'BUZZER_OFF');
    agregarLog('Comando enviado: BUZZER_OFF');
}

// Función para devolverle el control al ESP32 (deja de forzar ON/OFF)
function reiniciarAuto() {
    socket.emit('comando', 'AUTO');
    agregarLog('Comando enviado: AUTO (modo automático)');
}

// Función para enviar comando personalizado
function enviar_comando() {
    var comando = document.getElementById('txt_comando').value;
    if (comando.trim() !== '') {
        socket.emit('comando', comando);
        agregarLog('Comando enviado: ' + comando);
        document.getElementById('txt_comando').value = '';
    } else {
        alert('Escribe un comando válido');
    }
}

// Estado en tiempo real (LDR, buzzer, LED) reenviado por el servidor Node
socket.on('estado', function (datos) {
    actualizarEstado(datos);
});

// Confirmaciones de texto plano (OK / ERROR / COMANDO_DESCONOCIDO)
socket.on('respuesta_python', function (data) {
    agregarLog('Servidor: ' + data);
});

socket.on('comando_enviado', function (msg) {
    agregarLog(msg);
});

socket.on('error', function (msg) {
    agregarLog('⚠️ ' + msg);
});

socket.on('connect', function () {
    pillConexion.textContent = '● Conectado';
    pillConexion.className = 'pill conectado';
});

socket.on('disconnect', function () {
    pillConexion.textContent = '● Desconectado';
    pillConexion.className = 'pill desconectado';
});

socket.on('estado_inicial', function (data) {
    agregarLog(data.mensaje);
});