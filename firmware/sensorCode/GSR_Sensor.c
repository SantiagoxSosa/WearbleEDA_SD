// GSR v1.2 (SIG -> ESP32-S2 ADC pin)
// Reads raw ADC + smoothed value

const int GSR_PIN = 3;          // <-- change to your ADC pin (GPIO number)
const int SAMPLES = 50;         // smoothing window

int buffer[SAMPLES];
long sum = 0;
int idx = 0;

void setup() {
  Serial.begin(115200);
  delay(500);

  // ESP32 ADC setup
  analogReadResolution(12);          // 0..4095
  analogSetAttenuation(ADC_11db);    // good for ~0-3.3V range

  // init buffer
  for (int i = 0; i < SAMPLES; i++) {
    buffer[i] = analogRead(GSR_PIN);
    sum += buffer[i];
    delay(5);
  }
}

void loop() {
  int raw = analogRead(GSR_PIN);

  // moving average
  sum -= buffer[idx];
  buffer[idx] = raw;
  sum += raw;
  idx = (idx + 1) % SAMPLES;

  float smooth = (float)sum / SAMPLES;

  Serial.print("raw=");
  Serial.print(raw);
  Serial.print("\t smooth=");
  Serial.println(smooth);

  delay(20); // ~50 Hz sampling
}
