const socket = io();
const MAX_LUX = 50;

const elementos = {
  conexion: document.getElementById('conexion'),
  ldr: document.getElementById('ldr'),
  adc: document.getElementById('adc'),
  buzzer: document.getElementById('buzzer'),
  led: document.getElementById('led'),
  modo: document.getElementById('modo'),
  hora: document.getElementById('hora'),
  barraLuz: document.getElementById('barraLuz'),
  valorLux: document.getElementById('valorLux'),
  log: document.getElementById('log'),
  txtComando: document.getElementById('txtComando')
};

function agregarLog(texto) {
  const hora = new Date().toLocaleTimeString();
  elementos.log.textContent += `[${hora}] ${texto}\n`;
  elementos.log.scrollTop = elementos.log.scrollHeight;
}

function actualizarEstado(datos) {
  const lux = Number(datos.valor_ldr || 0);
  const porcentaje = Math.max(0, Math.min(100, (lux / MAX_LUX) * 100));

  elementos.ldr.textContent = `${lux.toFixed(1)} lux`;
  elementos.adc.textContent = datos.adc ?? 0;
  elementos.buzzer.textContent = datos.buzzer === 'ON' ? 'ENCENDIDO' : 'APAGADO';
  elementos.led.textContent = datos.led === 'ON' ? 'ENCENDIDO' : 'APAGADO';
  elementos.modo.textContent = datos.modo || 'AUTO';
  elementos.hora.textContent = datos.timestamp
    ? new Date(datos.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();
  elementos.valorLux.textContent = `${lux.toFixed(1)} lux`;
  elementos.barraLuz.style.height = `${porcentaje}%`;

  elementos.buzzer.className = datos.buzzer === 'ON' ? 'activo' : 'inactivo';
  elementos.led.className = datos.led === 'ON' ? 'activo' : 'inactivo';
  agregarLog(`Luz ${lux.toFixed(1)} lux | ADC ${datos.adc ?? 0} | Alarma ${datos.buzzer}`);
}

socket.on('connect', () => {
  elementos.conexion.textContent = 'Conectado';
  elementos.conexion.className = 'estado conectado';
  agregarLog('Interfaz web conectada al servidor');
});

socket.on('disconnect', () => {
  elementos.conexion.textContent = 'Desconectado';
  elementos.conexion.className = 'estado desconectado';
  agregarLog('Servidor desconectado');
});

socket.on('estado', actualizarEstado);

function enviarComando(comando) {
  socket.emit('comando', comando);
  agregarLog(`Comando enviado: ${comando}`);
}

function enviarComandoLibre() {
  const comando = elementos.txtComando.value.trim();
  if (!comando) return;
  enviarComando(comando);
  elementos.txtComando.value = '';
}

elementos.txtComando.addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter') enviarComandoLibre();
});
