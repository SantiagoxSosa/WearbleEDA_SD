#include <Wire.h>

// ESP32-C3 Super Mini I2C pins (as you requested)
static const int I2C_SDA = 6;
static const int I2C_SCL = 7;

// Common WT901 I2C address. We'll scan to confirm.
uint8_t WT901_ADDR = 0x50;

// JY901/WT901 register map (common mode)
static const uint8_t REG_ACC  = 0x34; // 6 bytes: AxL AxH AyL AyH AzL AzH
static const uint8_t REG_GYRO = 0x37; // 6 bytes: GxL GxH GyL GyH GzL GzH
static const uint8_t REG_ANG  = 0x3D; // 6 bytes: RollL RollH PitchL PitchH YawL YawH

bool i2cReadBytes(uint8_t addr, uint8_t reg, uint8_t *buf, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {   // repeated start
    return false;
  }

  size_t n = Wire.requestFrom((int)addr, (int)len);
  if (n != len) return false;

  for (size_t i = 0; i < len; i++) {
    buf[i] = Wire.read();
  }
  return true;
}

int16_t toInt16(uint8_t lo, uint8_t hi) {
  return (int16_t)((hi << 8) | lo);
}

uint8_t scanForDevice() {
  Serial.println("Scanning I2C...");
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(a, HEX);
      return a;
    }
  }
  return 0;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000); // try 100000 if you get read errors

  uint8_t found = scanForDevice();
  if (found == 0) {
    Serial.println("No I2C devices found. Check wiring/power/address.");
  } else {
    WT901_ADDR = found;
    Serial.print("Using WT901 address 0x");
    Serial.println(WT901_ADDR, HEX);
  }
}

void loop() {
  uint8_t buf[6];

  // ----- Accel -----
  if (i2cReadBytes(WT901_ADDR, REG_ACC, buf, 6)) {
    int16_t axRaw = toInt16(buf[0], buf[1]);
    int16_t ayRaw = toInt16(buf[2], buf[3]);
    int16_t azRaw = toInt16(buf[4], buf[5]);

    // Common scaling: accel = raw / 32768 * 16g
    float ax = (axRaw / 32768.0f) * 16.0f;
    float ay = (ayRaw / 32768.0f) * 16.0f;
    float az = (azRaw / 32768.0f) * 16.0f;

    Serial.print("ACC(g): ");
    Serial.print(ax, 3); Serial.print(", ");
    Serial.print(ay, 3); Serial.print(", ");
    Serial.print(az, 3);
    Serial.print(" | ");
  } else {
    Serial.print("ACC read fail | ");
  }

  // ----- Gyro -----
  if (i2cReadBytes(WT901_ADDR, REG_GYRO, buf, 6)) {
    int16_t gxRaw = toInt16(buf[0], buf[1]);
    int16_t gyRaw = toInt16(buf[2], buf[3]);
    int16_t gzRaw = toInt16(buf[4], buf[5]);

    // Common scaling: gyro = raw / 32768 * 2000 dps
    float gx = (gxRaw / 32768.0f) * 2000.0f;
    float gy = (gyRaw / 32768.0f) * 2000.0f;
    float gz = (gzRaw / 32768.0f) * 2000.0f;

    Serial.print("GYRO(dps): ");
    Serial.print(gx, 2); Serial.print(", ");
    Serial.print(gy, 2); Serial.print(", ");
    Serial.print(gz, 2);
    Serial.print(" | ");
  } else {
    Serial.print("GYRO read fail | ");
  }

  // ----- Angle -----
  if (i2cReadBytes(WT901_ADDR, REG_ANG, buf, 6)) {
    int16_t rollRaw  = toInt16(buf[0], buf[1]);
    int16_t pitchRaw = toInt16(buf[2], buf[3]);
    int16_t yawRaw   = toInt16(buf[4], buf[5]);

    // Common scaling: angle = raw / 32768 * 180 deg
    float roll  = (rollRaw  / 32768.0f) * 180.0f;
    float pitch = (pitchRaw / 32768.0f) * 180.0f;
    float yaw   = (yawRaw   / 32768.0f) * 180.0f;

    Serial.print("ANG(deg): ");
    Serial.print(roll, 2); Serial.print(", ");
    Serial.print(pitch, 2); Serial.print(", ");
    Serial.print(yaw, 2);
  } else {
    Serial.print("ANG read fail");
  }

  Serial.println();
  delay(50); // ~20 Hz prints
}
