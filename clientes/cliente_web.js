var express = require('express');
var app = express();
var server = require('http').Server(app);
const io = require('socket.io')(server);
var net = require('net');

// Servir archivos estáticos desde la carpeta public/
app.use(express.static('public'));

// Configuración
const WEB_PORT = 5001;
const PYTHON_HOST = '127.0.0.1';
const PYTHON_PORT = 5000;

let pythonClient = null;
let bufferPython = '';

// ---------- Conexión al servidor Python (puerto 5000) ----------
function conectarPython() {
    pythonClient = net.createConnection({ port: PYTHON_PORT, host: PYTHON_HOST }, () => {
        console.log('✅ Conectado al servidor Python (puerto 5000)');
    });

    pythonClient.on('data', (data) => {
        bufferPython += data.toString();

        // El servidor Python separa cada mensaje con '\n'
        let partes = bufferPython.split('\n');
        bufferPython = partes.pop(); // el último trozo puede estar incompleto

        partes.forEach((linea) => {
            linea = linea.trim();
            if (!linea) return;

            try {
                const estado = JSON.parse(linea);
                if (estado.tipo === 'ESTADO') {
                    // Estado estructurado (LDR, buzzer, LED) -> alimenta el medidor
                    io.sockets.emit('estado', estado);
                    return;
                }
            } catch (e) {
                // No era JSON: es una respuesta de texto plano (OK / ERROR / ...)
            }

            console.log('📩 Respuesta desde Python:', linea);
            io.sockets.emit('respuesta_python', linea);
        });
    });

    pythonClient.on('end', () => {
        console.log('🔌 Desconectado del servidor Python. Reintentando en 3s...');
        setTimeout(conectarPython, 3000);
    });

    pythonClient.on('error', (err) => {
        console.log('⚠️ Error al conectar con Python:', err.message);
        // Intentar reconectar después de 3 segundos
        setTimeout(conectarPython, 3000);
    });
}

// Iniciar la conexión al servidor Python
conectarPython();

// ---------- Servidor Socket.IO (Web) ----------
io.on('connection', function(socket) {
    console.log('🔗 Cliente Web conectado: ' + socket.id);

    // Enviar estado inicial (puedes ampliarlo luego)
    socket.emit('estado_inicial', { mensaje: 'Conectado al servidor web' });

    // Recibir comandos desde la interfaz web
    socket.on('comando', function(data) {
        console.log('📤 Comando desde Web:', data);

        // Enviar al servidor Python por TCP
        if (pythonClient && pythonClient.readyState === 'open') {
            pythonClient.write(data + '\n');
            socket.emit('comando_enviado', 'Comando enviado: ' + data);
        } else {
            console.log('⚠️ Servidor Python no disponible');
            socket.emit('error', 'Servidor Python no conectado');
        }
    });
});

// Iniciar el servidor web
server.listen(WEB_PORT, function() {
    console.log(`🌐 Servidor Web corriendo en puerto ${WEB_PORT}`);
    console.log(`   Abre http://localhost:${WEB_PORT} en tu navegador`);
});