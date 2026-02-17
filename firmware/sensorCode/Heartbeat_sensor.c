#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <math.h>

#define SDA_PIN 1
#define SCL_PIN 2

MAX30105 particleSensor;

// ---- Global state ----
uint32_t lastBeat = 0;
float bpm = 0;
float avgBpm = 0;

// HRV storage
#define RR_BUF 10
float rr[RR_BUF];
int rrIndex = 0;
int rrCount = 0;
// ----------------------

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("BOOT");

  Wire.begin(SDA_PIN, SCL_PIN);
  delay(500); // IMPORTANT: let MAX30102 power up

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 not found");
    while (1) delay(10);
  }

  Serial.println("MAX30102 OK");

  particleSensor.setup(
  60,     // ledBrightness
  4,     // sampleAverage  (more smoothing)
  2,      // Red + IR
  200,    // sampleRate
  215,    // pulseWidth (stronger pulse waveform)
  16384   // adcRange (prevents clipping)
);

particleSensor.setPulseAmplitudeIR(0xA0);  // IR ON
particleSensor.setPulseAmplitudeRed(0x00);
particleSensor.setPulseAmplitudeGreen(0);


  Serial.println("Place finger gently on sensor");
}

void loop() {
  long irValue = particleSensor.getIR();

  // Print IR occasionally so we know sensor is alive
  static uint32_t lastIRprint = 0;
  if (millis() - lastIRprint > 250) {
    lastIRprint = millis();
    Serial.print("IR=");
    Serial.println(irValue);
  }

  // Finger detect (LOWER threshold for debugging)
 const long FINGER_THRESH = 10000;

if (irValue < FINGER_THRESH) {
  avgBpm = 0;
  lastBeat = 0;
  rrIndex = 0;
  rrCount = 0;
  return;
}


  if (checkForBeat(irValue)) {
    uint32_t now = millis();
    Serial.print("BEAT ");

    if (lastBeat != 0) {
      uint32_t dt = now - lastBeat;
      Serial.print("dt=");
      Serial.print(dt);

      // Refractory period (prevents double triggers)
      if (dt < 300) {
        Serial.println(" (ignored: too fast)");
        return;
      }

      float rrInterval = (float)dt;
      bpm = 60000.0f / rrInterval;

      Serial.print(" bpm=");
      Serial.println(bpm, 1);

      // Store RR for HRV
      if (rrInterval > 300 && rrInterval < 2000) {
        rr[rrIndex] = rrInterval;
        rrIndex = (rrIndex + 1) % RR_BUF;
        if (rrCount < RR_BUF) rrCount++;
      }

      // HRV (RMSSD)
      if (rrCount >= 2) {
        float sumSq = 0;
        for (int i = 1; i < rrCount; i++) {
          float d = rr[i] - rr[i - 1];
          sumSq += d * d;
        }
        float hrv = sqrt(sumSq / (rrCount - 1));

        Serial.print("HRV: ");
        Serial.print(hrv, 1);
        Serial.print(" , BPM: ");
        Serial.println(bpm, 1);
      }
    } else {
      Serial.println("first");
    }

    lastBeat = now;
  }
}
