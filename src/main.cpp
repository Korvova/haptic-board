#include <Arduino.h>

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

constexpr uint8_t LEFT_MOTOR_PIN = 21;
constexpr uint8_t CENTER_MOTOR_PIN = 22;
constexpr uint8_t RIGHT_MOTOR_PIN = 23;
constexpr uint8_t TOP_MOTOR_PIN = 19;
constexpr uint8_t BOTTOM_MOTOR_PIN = 18;
constexpr uint8_t TOP_LEFT_MOTOR_PIN = 5;
constexpr uint8_t TOP_RIGHT_MOTOR_PIN = 17;
constexpr uint8_t FINGER_CLICK_MOTOR_PIN = 25;
constexpr uint8_t RIGHT_CLICK_MOTOR_PIN = 33;

constexpr uint8_t LEFT_PWM_CHANNEL = 0;
constexpr uint8_t CENTER_PWM_CHANNEL = 1;
constexpr uint8_t RIGHT_PWM_CHANNEL = 2;
constexpr uint8_t TOP_PWM_CHANNEL = 3;
constexpr uint8_t BOTTOM_PWM_CHANNEL = 4;
constexpr uint8_t TOP_LEFT_PWM_CHANNEL = 5;
constexpr uint8_t TOP_RIGHT_PWM_CHANNEL = 6;
constexpr uint8_t FINGER_CLICK_PWM_CHANNEL = 7;
constexpr uint8_t RIGHT_CLICK_PWM_CHANNEL = 8;

constexpr uint16_t PWM_FREQ_HZ = 20000;
constexpr uint8_t PWM_RESOLUTION_BITS = 8;
constexpr unsigned long COMMAND_TIMEOUT_MS = 300;

unsigned long lastCommandAt = 0;

void writeMotors(uint8_t left, uint8_t center, uint8_t right, uint8_t top,
                 uint8_t bottom, uint8_t topLeft, uint8_t topRight,
                 uint8_t fingerClick, uint8_t rightClick) {
  ledcWrite(LEFT_PWM_CHANNEL, left);
  ledcWrite(CENTER_PWM_CHANNEL, center);
  ledcWrite(RIGHT_PWM_CHANNEL, right);
  ledcWrite(TOP_PWM_CHANNEL, top);
  ledcWrite(BOTTOM_PWM_CHANNEL, bottom);
  ledcWrite(TOP_LEFT_PWM_CHANNEL, topLeft);
  ledcWrite(TOP_RIGHT_PWM_CHANNEL, topRight);
  ledcWrite(FINGER_CLICK_PWM_CHANNEL, fingerClick);
  ledcWrite(RIGHT_CLICK_PWM_CHANNEL, rightClick);
  digitalWrite(LED_BUILTIN,
               (left || center || right || top || bottom || topLeft || topRight ||
                fingerClick || rightClick)
                   ? HIGH
                   : LOW);
}

void stopMotors() {
  writeMotors(0, 0, 0, 0, 0, 0, 0, 0, 0);
}

uint8_t clampByte(int value) {
  if (value < 0) {
    return 0;
  }
  if (value > 255) {
    return 255;
  }
  return static_cast<uint8_t>(value);
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) {
    return;
  }

  if (line == "S" || line == "STOP") {
    stopMotors();
    Serial.println("OK STOP");
    return;
  }

  if (line[0] != 'V') {
    Serial.println(
        "ERR expected: V left center right top bottom topLeft topRight leftClick rightClick");
    return;
  }

  int left = 0;
  int center = 0;
  int right = 0;
  int top = 0;
  int bottom = 0;
  int topLeft = 0;
  int topRight = 0;
  int fingerClick = 0;
  int rightClick = 0;
  const int parsed =
      sscanf(line.c_str(), "V %d %d %d %d %d %d %d %d %d", &left, &center, &right,
             &top, &bottom, &topLeft, &topRight, &fingerClick, &rightClick);

  if (parsed != 3 && parsed != 5 && parsed != 7 && parsed != 8 && parsed != 9) {
    Serial.println(
        "ERR expected: V left center right top bottom topLeft topRight leftClick rightClick");
    return;
  }

  writeMotors(clampByte(left), clampByte(center), clampByte(right), clampByte(top),
              clampByte(bottom), clampByte(topLeft), clampByte(topRight),
              clampByte(fingerClick), clampByte(rightClick));
  lastCommandAt = millis();
  Serial.println("OK");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);

  ledcSetup(LEFT_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(CENTER_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(RIGHT_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(TOP_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(BOTTOM_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(TOP_LEFT_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(TOP_RIGHT_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(FINGER_CLICK_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(RIGHT_CLICK_PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);

  ledcAttachPin(LEFT_MOTOR_PIN, LEFT_PWM_CHANNEL);
  ledcAttachPin(CENTER_MOTOR_PIN, CENTER_PWM_CHANNEL);
  ledcAttachPin(RIGHT_MOTOR_PIN, RIGHT_PWM_CHANNEL);
  ledcAttachPin(TOP_MOTOR_PIN, TOP_PWM_CHANNEL);
  ledcAttachPin(BOTTOM_MOTOR_PIN, BOTTOM_PWM_CHANNEL);
  ledcAttachPin(TOP_LEFT_MOTOR_PIN, TOP_LEFT_PWM_CHANNEL);
  ledcAttachPin(TOP_RIGHT_MOTOR_PIN, TOP_RIGHT_PWM_CHANNEL);
  ledcAttachPin(FINGER_CLICK_MOTOR_PIN, FINGER_CLICK_PWM_CHANNEL);
  ledcAttachPin(RIGHT_CLICK_MOTOR_PIN, RIGHT_CLICK_PWM_CHANNEL);

  stopMotors();
  lastCommandAt = millis();

  Serial.println("Haptic mouse firmware ready");
  Serial.println(
      "Protocol: V left center right top bottom topLeft topRight leftClick rightClick, values 0-255. S stops.");
}

void loop() {
  if (Serial.available()) {
    const String line = Serial.readStringUntil('\n');
    handleCommand(line);
  }

  if (millis() - lastCommandAt > COMMAND_TIMEOUT_MS) {
    stopMotors();
    lastCommandAt = millis();
  }
}
