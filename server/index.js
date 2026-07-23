'use strict';

const express = require('express');
const http = require('http');
const net = require('net');
const path = require('path');
const { Server: SocketIOServer } = require('socket.io');

const WEB_PORT = 5001;
const JSON_TCP_PORT = 5000;   // Clientes Java y Python
const LABVIEW_TCP_PORT = 5002; // Se conserva para el VI original

const app = express();
const httpServer = http.createServer(app);
const io = new SocketIOServer(httpServer, {
  cors: { origin: '*' }
});

app.use(express.static(path.join(__dirname, '..', 'public')));

let arduinoSocketId = null;
let estadoActual = {
  tipo: 'ESTADO',
  valor_ldr: 0.0,
  adc: 0,
  buzzer: 'OFF',
  led: 'OFF',
  modo: 'AUTO',
  timestamp: new Date().toISOString()
};

const clientesJson = new Set();
const clientesLabView = new Set();

function normalizarComando(valor) {
  const comando = String(valor ?? '').trim().toUpperCase();
  const equivalencias = {
    P: 'BUZZER_ON',
    A: 'BUZZER_OFF',
    ON: 'BUZZER_ON',
    OFF: 'BUZZER_OFF',
    AUTOMATICO: 'AUTO',
    'AUTOMÁTICO': 'AUTO'
  };
  return equivalencias[comando] || comando;
}

function comandoValido(comando) {
  return ['BUZZER_ON', 'BUZZER_OFF', 'AUTO', 'R'].includes(comando);
}

function enviarComandoAlDispositivo(valor, origen = 'desconocido') {
  const comando = normalizarComando(valor);
  if (!comandoValido(comando)) {
    console.log(`[COMANDO INVÁLIDO] ${origen}: ${valor}`);
    return false;
  }

  console.log(`[COMANDO] ${origen} -> ESP32: ${comando}`);
  if (arduinoSocketId) {
    io.to(arduinoSocketId).emit('comando', comando);
    return true;
  }

  console.log('[AVISO] El puente serial todavía no está conectado.');
  return false;
}

function extraerNumero(valor, respaldo = 0) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : respaldo;
}

function normalizarEstado(data) {
  if (typeof data === 'number' || (typeof data === 'string' && data.trim() !== '' && Number.isFinite(Number(data)))) {
    return {
      ...estadoActual,
      valor_ldr: extraerNumero(data, estadoActual.valor_ldr),
      timestamp: new Date().toISOString()
    };
  }

  if (typeof data === 'string') {
    // Compatibilidad con una línea serial directa: LUX:12.3,ADC:1234,ESTADO:ON,MODO:AUTO
    const lux = data.match(/LUX:([\d.]+)/i);
    const adc = data.match(/ADC:(\d+)/i);
    const estado = data.match(/ESTADO:(ON|OFF)/i);
    const modo = data.match(/MODO:(AUTO|MANUAL)/i);
    if (lux) {
      return {
        tipo: 'ESTADO',
        valor_ldr: extraerNumero(lux[1], estadoActual.valor_ldr),
        adc: adc ? parseInt(adc[1], 10) : estadoActual.adc,
        buzzer: estado ? estado[1].toUpperCase() : estadoActual.buzzer,
        led: estado ? estado[1].toUpperCase() : estadoActual.led,
        modo: modo ? modo[1].toUpperCase() : estadoActual.modo,
        timestamp: new Date().toISOString()
      };
    }
  }

  if (data && typeof data === 'object') {
    const buzzer = String(data.buzzer ?? data.estado ?? estadoActual.buzzer).toUpperCase() === 'ON' ? 'ON' : 'OFF';
    const led = String(data.led ?? data.estado ?? estadoActual.led).toUpperCase() === 'ON' ? 'ON' : 'OFF';
    const modo = String(data.modo ?? estadoActual.modo).toUpperCase() === 'MANUAL' ? 'MANUAL' : 'AUTO';

    return {
      tipo: 'ESTADO',
      valor_ldr: extraerNumero(data.valor_ldr ?? data.lux, estadoActual.valor_ldr),
      adc: Math.round(extraerNumero(data.adc, estadoActual.adc)),
      buzzer,
      led,
      modo,
      timestamp: data.timestamp || new Date().toISOString()
    };
  }

  return { ...estadoActual, timestamp: new Date().toISOString() };
}

function enviarJson(socket, objeto) {
  if (!socket.destroyed && socket.writable) {
    socket.write(`${JSON.stringify(objeto)}\n`);
  }
}

function difundirEstado() {
  // Interfaz web y clientes antiguos de Socket.IO
  io.emit('estado', estadoActual);
  io.emit('arduino', estadoActual.valor_ldr);

  // Clientes gráficos Java/Python: JSON delimitado por salto de línea
  for (const socket of clientesJson) {
    enviarJson(socket, estadoActual);
  }

  // LabVIEW original: exactamente 4 bytes numéricos, como en el proyecto base.
  const valorLabView = Math.max(0, Math.min(99.9, estadoActual.valor_ldr))
    .toFixed(1)
    .padStart(4, '0');

  for (const socket of clientesLabView) {
    if (!socket.destroyed && socket.writable) {
      socket.write(valorLabView);
    }
  }
}

// ---------------- Socket.IO: web + puente serial ----------------
io.on('connection', (socket) => {
  console.log(`[SOCKET.IO] Conectado: ${socket.id}`);
  socket.emit('estado', estadoActual);

  socket.on('soy_arduino', () => {
    arduinoSocketId = socket.id;
    console.log(`[PUENTE SERIAL] Registrado: ${socket.id}`);
  });

  socket.on('comando', (data) => {
    enviarComandoAlDispositivo(data, `Socket.IO ${socket.id}`);
  });

  socket.on('desde_arduino', (data) => {
    estadoActual = normalizarEstado(data);
    difundirEstado();
  });

  socket.on('disconnect', () => {
    if (socket.id === arduinoSocketId) {
      arduinoSocketId = null;
      console.log('[PUENTE SERIAL] Desconectado.');
    }
  });
});

// ---------------- TCP JSON: Java y Python (puerto 5000) ----------------
const jsonTcpServer = net.createServer((socket) => {
  socket.setEncoding('utf8');
  socket.setKeepAlive(true);
  socket.nombre = `${socket.remoteAddress}:${socket.remotePort}`;
  socket.bufferEntrada = '';
  clientesJson.add(socket);
  console.log(`[TCP JSON] Cliente conectado: ${socket.nombre}`);
  enviarJson(socket, estadoActual);

  socket.on('data', (chunk) => {
    socket.bufferEntrada += chunk;
    let indice;
    while ((indice = socket.bufferEntrada.indexOf('\n')) >= 0) {
      const linea = socket.bufferEntrada.slice(0, indice).trim();
      socket.bufferEntrada = socket.bufferEntrada.slice(indice + 1);
      if (!linea) continue;

      let comando = linea;
      try {
        const json = JSON.parse(linea);
        comando = json.comando ?? json.command ?? linea;
      } catch (_) {
        // También se aceptan comandos de texto plano.
      }
      enviarComandoAlDispositivo(comando, `TCP JSON ${socket.nombre}`);
    }
  });

  const retirar = () => {
    clientesJson.delete(socket);
    console.log(`[TCP JSON] Cliente desconectado: ${socket.nombre}`);
  };
  socket.on('end', retirar);
  socket.on('close', retirar);
  socket.on('error', (error) => {
    console.log(`[TCP JSON] Error ${socket.nombre}: ${error.message}`);
    retirar();
  });
});

// ---------------- TCP legado: LabVIEW (puerto 5002) ----------------
const labViewTcpServer = net.createServer((socket) => {
  socket.setEncoding('utf8');
  socket.nombre = `${socket.remoteAddress}:${socket.remotePort}`;
  clientesLabView.add(socket);
  console.log(`[LABVIEW] Cliente conectado: ${socket.nombre}`);

  socket.on('data', (data) => {
    const texto = String(data).trim();
    // El VI original manda P/A. También aceptamos los nombres completos.
    const comandos = texto.includes('\n') ? texto.split(/\r?\n/) : [texto];
    for (const comando of comandos) {
      if (comando.trim()) enviarComandoAlDispositivo(comando, `LabVIEW ${socket.nombre}`);
    }
  });

  const retirar = () => {
    clientesLabView.delete(socket);
    console.log(`[LABVIEW] Cliente desconectado: ${socket.nombre}`);
  };
  socket.on('end', retirar);
  socket.on('close', retirar);
  socket.on('error', (error) => {
    console.log(`[LABVIEW] Error ${socket.nombre}: ${error.message}`);
    retirar();
  });
});

jsonTcpServer.listen(JSON_TCP_PORT, () => {
  console.log(`Servidor TCP JSON (Java/Python) en puerto ${JSON_TCP_PORT}.`);
});

labViewTcpServer.listen(LABVIEW_TCP_PORT, () => {
  console.log(`Servidor TCP LabVIEW en puerto ${LABVIEW_TCP_PORT}.`);
});

httpServer.listen(WEB_PORT, () => {
  console.log(`Servidor web/Socket.IO en http://localhost:${WEB_PORT}`);
});
