// ESP32 clásico (DAC de 8 bits) - Seno por DAC1 en GPIO25
// Placa en Arduino IDE: "ESP32 Dev Module"
//
// 64 muestras por periodo, una muestra cada 15 us -> ~1.04 kHz.
// La frecuencia exacta no importa: el análisis en Python la detecta solo.

const uint8_t PIN_DAC = 25;
const int N = 64;
const uint32_t PERIODO_US = 15;

uint8_t tabla[N];

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < N; i++) {
    // Seno centrado en 127.5 con amplitud casi completa (0..255)
    tabla[i] = (uint8_t)roundf(127.5f + 127.0f * sinf(2.0f * PI * i / N));
  }
  Serial.println("Seno en GPIO25 (DAC1), ~1.04 kHz");
}

void loop() {
  uint32_t t_next = micros();
  while (true) {
    for (int i = 0; i < N; i++) {
      dacWrite(PIN_DAC, tabla[i]);
      t_next += PERIODO_US;
      while ((int32_t)(micros() - t_next) < 0) { }  // espera activa
    }
  }
}
