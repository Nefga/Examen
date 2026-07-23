/*
  Monitoreo y control de un ecosistema
  ESP32 + LDR + buzzer activo + LED

  Conexiones:
  3.3 V --- LDR ---+--- GPIO34
                   |
                  10 kΩ
                   |
                  GND

  GPIO25 -> entrada del buzzer activo
  GPIO26 -> resistencia 220-330 Ω -> LED -> GND

  Comandos por Serial (9600 baudios):
  BUZZER_ON  / P  = modo manual y alarma encendida
  BUZZER_OFF / A  = modo manual y alarma apagada
  AUTO            = control automático por nivel de luz
  R               = solicita una lectura inmediata
*/

#include <Arduino.h>

const int PIN_LDR = 34;
const int PIN_BUZZER = 25;
const int PIN_LED = 26;

// Calibración aproximada basada en las mediciones del montaje.
// Ajusta estos dos ADC si cambias el divisor, el LDR o la distancia.
const int ADC_OSCURO = 200;
const int ADC_BRILLANTE = 2880;
const float LUX_OSCURO = 1.0f;
const float LUX_BRILLANTE = 50.0f;
const float UMBRAL_LUX = 15.0f;

const unsigned long INTERVALO_REPORTE_MS = 150;

bool modoManual = false;
bool estadoAlarma = false;
unsigned long ultimoReporte = 0;

float adcALux(int adc) {
  adc = constrain(adc, ADC_OSCURO, ADC_BRILLANTE);
  const float t = (float)(adc - ADC_OSCURO) /
                  (float)(ADC_BRILLANTE - ADC_OSCURO);
  return LUX_OSCURO * powf(LUX_BRILLANTE / LUX_OSCURO, t);
}

int leerADCPromediado() {
  long acumulado = 0;
  const int muestras = 10;
  for (int i = 0; i < muestras; i++) {
    acumulado += analogRead(PIN_LDR);
    delayMicroseconds(500);
  }
  return (int)(acumulado / muestras);
}

void aplicarSalidas() {
  digitalWrite(PIN_BUZZER, estadoAlarma ? HIGH : LOW);
  digitalWrite(PIN_LED, estadoAlarma ? HIGH : LOW);
}

void procesarComando(String comando) {
  comando.trim();
  comando.toUpperCase();

  if (comando == "BUZZER_ON" || comando == "P" || comando == "ON") {
    modoManual = true;
    estadoAlarma = true;
  } else if (comando == "BUZZER_OFF" || comando == "A" || comando == "OFF") {
    modoManual = true;
    estadoAlarma = false;
  } else if (comando == "AUTO" || comando == "AUTOMATICO") {
    modoManual = false;
  }

  aplicarSalidas();
}

void reportarEstado(int adc, float lux) {
  Serial.print("LUX:");
  Serial.print(lux, 1);
  Serial.print(",ADC:");
  Serial.print(adc);
  Serial.print(",ESTADO:");
  Serial.print(estadoAlarma ? "ON" : "OFF");
  Serial.print(",MODO:");
  Serial.println(modoManual ? "MANUAL" : "AUTO");
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(30);

  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED, LOW);
}

void loop() {
  while (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    procesarComando(comando);
  }

  const int adc = leerADCPromediado();
  const float lux = adcALux(adc);

  if (!modoManual) {
    estadoAlarma = lux < UMBRAL_LUX;
    aplicarSalidas();
  }

  const unsigned long ahora = millis();
  if (ahora - ultimoReporte >= INTERVALO_REPORTE_MS) {
    ultimoReporte = ahora;
    reportarEstado(adc, lux);
  }

  delay(5);
}
