const int pinLDR = 34;      
const int pinBuzzer = 25;   
const int pinLED = 26;      


const int ADC_OSCURO      = 200;   
const int ADC_BRILLANTE   = 1500;  
const float LUX_OSCURO    = 1.0;
const float LUX_BRILLANTE = 50.0; 

const float UMBRAL_LUX = 15.0;  

float adcALux(int adc) {
  adc = constrain(adc, ADC_OSCURO, ADC_BRILLANTE);
  float t = (float)(adc - ADC_OSCURO) / (float)(ADC_BRILLANTE - ADC_OSCURO);
  return LUX_OSCURO * pow(LUX_BRILLANTE / LUX_OSCURO, t); 
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
      modoManual = false;   
    }
  }


  Serial.print("LUX:");
  Serial.print(lux, 1);
  Serial.print(",ADC:");
  Serial.print(valorADC);
  Serial.print(",ESTADO:");
  Serial.println(estadoAlarma ? "ON" : "OFF");

  delay(100);
}
