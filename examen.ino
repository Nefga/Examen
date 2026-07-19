const int pinLDR = 34;      // ESP32: pin34 es ADC1_CH6, solo entrada
const int pinBuzzer = 25;   // GPIO de salida libre
const int pinLED = 26;      // GPIO de salida libre

// ---------------------------------------------------------------
// Calibracion ADC -> lux (interpolacion logaritmica, 2 puntos)
// ---------------------------------------------------------------
// IMPORTANTE: como el servidor de Python usa este mismo puerto serial,
// no puedes tener el Monitor Serial del IDE abierto al mismo tiempo que
// corres servidor_prueba.py. Por eso, el sketch ahora manda el ADC
// crudo junto con el lux (ver el final del loop), y el servidor lo
// imprime en su propia consola -- así calibras viendo esa consola.
//
// Para calibrar de verdad:
//   1. Sube este sketch y corre servidor_prueba.py.
//   2. Tapa completamente el sensor y anota el "ADC crudo" que
//      imprime la consola del servidor -> ese es ADC_OSCURO.
//   3. Ilumina el sensor con lo mismo que vayas a usar de referencia
//      (ej. el flash de tu celular) y anota ese otro "ADC crudo"
//      -> ese es ADC_BRILLANTE.
//   4. LUX_OSCURO y LUX_BRILLANTE son los lux reales de esos dos
//      momentos (si no tienes luxómetro, usa 1.0 para "oscuro total"
//      y el valor conocido de tu fuente de luz, como los 50 lux de
//      tu celular, para "brillante").
const int ADC_OSCURO      = 200;   // <-- reemplaza con tu ADC medido a oscuras
const int ADC_BRILLANTE   = 1500;  // <-- reemplaza con tu ADC medido con el celular encima
const float LUX_OSCURO    = 1.0;
const float LUX_BRILLANTE = 50.0;  // tu celular = 50 lux

const float UMBRAL_LUX = 15.0;   // por debajo de esto, se considera "oscuro"

float adcALux(int adc) {
  adc = constrain(adc, ADC_OSCURO, ADC_BRILLANTE);
  float t = (float)(adc - ADC_OSCURO) / (float)(ADC_BRILLANTE - ADC_OSCURO);
  return LUX_OSCURO * pow(LUX_BRILLANTE / LUX_OSCURO, t);  // interpolacion log
}

// ---------------------------------------------------------------
// Estado de la alarma
// ---------------------------------------------------------------
bool modoManual = false;   // true mientras un comando manual tenga el control
bool estadoAlarma = false; // estado real actual del buzzer/LED

void setup() {
  Serial.begin(9600);
  pinMode(pinBuzzer, OUTPUT);
  pinMode(pinLED, OUTPUT);
}

void loop() {
  int valorADC = analogRead(pinLDR);   // 0 - 4095 en ESP32
  float lux = adcALux(valorADC);

  // Solo el modo automatico reacciona a la luz; si hay un comando manual
  // activo, el estado se queda como lo dejo ese comando hasta que llegue
  // otro (BUZZER_ON / BUZZER_OFF / AUTO).
  if (!modoManual) {
    estadoAlarma = (lux < UMBRAL_LUX);
  }

  digitalWrite(pinBuzzer, estadoAlarma ? HIGH : LOW);
  digitalWrite(pinLED, estadoAlarma ? HIGH : LOW);

  // Escuchar comandos desde la PC (Python/Java/Web)
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "BUZZER_ON") {
      modoManual = true;
      estadoAlarma = true;
    }
    else if (comando == "BUZZER_OFF") {
      modoManual = true;
      estadoAlarma = false;
    }
    else if (comando == "AUTO") {
      modoManual = false;   // regresa el control a la luz ambiente
    }
  }

  // Reportar lux + ADC crudo (para calibrar) + el estado real
  Serial.print("LUX:");
  Serial.print(lux, 1);
  Serial.print(",ADC:");
  Serial.print(valorADC);
  Serial.print(",ESTADO:");
  Serial.println(estadoAlarma ? "ON" : "OFF");

  delay(100);
}
