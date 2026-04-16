/**********************************************************************
  USB serial motor bridge for the Freenove 4WD Car for Raspberry Pi Pico.

  Commands are newline-terminated:
    F 50 250       forward at speed 50 for 250 ms
    B 50 250       backward at speed 50 for 250 ms
    L 50 250       ordinary-wheel left turn
    R 50 250       ordinary-wheel right turn
    ML 50 250      mecanum strafe left
    MR 50 250      mecanum strafe right
    S              stop
    DRIVE 50 -50   differential left/right speeds
    WHEEL 50 50 50 50  raw M1/M2/M3/M4 speeds
    PING           health check
**********************************************************************/

const int PIN_MOTOR_PWM_RIGHT1 = 7;
const int PIN_MOTOR_PWM_RIGHT2 = 6;
const int PIN_MOTOR_PWM_RIGHT3 = 9;
const int PIN_MOTOR_PWM_RIGHT4 = 8;
const int PIN_MOTOR_PWM_LEFT1 = 18;
const int PIN_MOTOR_PWM_LEFT2 = 19;
const int PIN_MOTOR_PWM_LEFT3 = 21;
const int PIN_MOTOR_PWM_LEFT4 = 20;

const int MOTOR_SPEED_MIN = -100;
const int MOTOR_SPEED_MAX = 100;
const int DEFAULT_SPEED = 50;
const int MOTOR_DIRECTION = -1;
const unsigned long FAILSAFE_MS = 750;

String inputLine = "";
unsigned long lastCommandAt = 0;
unsigned long runUntil = 0;
bool motorsRunning = false;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(20);

  setupMotorPin(PIN_MOTOR_PWM_RIGHT1);
  setupMotorPin(PIN_MOTOR_PWM_RIGHT2);
  setupMotorPin(PIN_MOTOR_PWM_RIGHT3);
  setupMotorPin(PIN_MOTOR_PWM_RIGHT4);
  setupMotorPin(PIN_MOTOR_PWM_LEFT1);
  setupMotorPin(PIN_MOTOR_PWM_LEFT2);
  setupMotorPin(PIN_MOTOR_PWM_LEFT3);
  setupMotorPin(PIN_MOTOR_PWM_LEFT4);

  stopMotors();
  lastCommandAt = millis();
  Serial.println("READY pico_serial_bridge");
}

void loop() {
  readSerialCommands();
  enforceFailsafe();
}

void setupMotorPin(int pin) {
  pinMode(pin, OUTPUT);
  analogWrite(pin, 0);
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        handleCommand(inputLine);
        inputLine = "";
      }
    } else if (inputLine.length() < 96) {
      inputLine += c;
    }
  }
}

void enforceFailsafe() {
  unsigned long now = millis();
  if (motorsRunning && runUntil > 0 && now >= runUntil) {
    stopMotors();
    Serial.println("OK AUTO_STOP");
  }
  if (motorsRunning && now - lastCommandAt > FAILSAFE_MS) {
    stopMotors();
    Serial.println("OK FAILSAFE_STOP");
  }
}

void handleCommand(String line) {
  line.trim();
  line.toUpperCase();
  if (line.length() == 0) {
    return;
  }

  char buffer[100];
  line.toCharArray(buffer, sizeof(buffer));
  char *command = strtok(buffer, " ,#\t");
  if (command == NULL) {
    return;
  }

  if (matches(command, "PING")) {
    Serial.println("PONG");
    return;
  }

  if (matches(command, "S") || matches(command, "STOP")) {
    stopMotors();
    lastCommandAt = millis();
    runUntil = 0;
    Serial.println("OK STOP");
    return;
  }

  if (matches(command, "DRIVE")) {
    int leftSpeed = readSignedToken(DEFAULT_SPEED);
    int rightSpeed = readSignedToken(DEFAULT_SPEED);
    int durationMs = readDurationToken(0);
    setDifferential(leftSpeed, rightSpeed);
    armStop(durationMs);
    Serial.println("OK DRIVE");
    return;
  }

  if (matches(command, "WHEEL") || matches(command, "WHEELS")) {
    int m1 = readSignedToken(0);
    int m2 = readSignedToken(0);
    int m3 = readSignedToken(0);
    int m4 = readSignedToken(0);
    int durationMs = readDurationToken(0);
    setWheels(m1, m2, m3, m4);
    armStop(durationMs);
    Serial.println("OK WHEEL");
    return;
  }

  int speed = readSpeedToken(DEFAULT_SPEED);
  int durationMs = readDurationToken(0);

  if (matches(command, "F") || matches(command, "FORWARD") || matches(command, "W")) {
    setDifferential(speed, speed);
  } else if (matches(command, "B") || matches(command, "BACK") || matches(command, "BACKWARD")) {
    setDifferential(-speed, -speed);
  } else if (matches(command, "L") || matches(command, "LEFT")) {
    setDifferential(-speed, speed);
  } else if (matches(command, "R") || matches(command, "RIGHT")) {
    setDifferential(speed, -speed);
  } else if (matches(command, "ML") || matches(command, "MOVE_LEFT") || matches(command, "STRAFE_LEFT")) {
    setWheels(-speed, speed, -speed, speed);
  } else if (matches(command, "MR") || matches(command, "MOVE_RIGHT") || matches(command, "STRAFE_RIGHT")) {
    setWheels(speed, -speed, speed, -speed);
  } else {
    Serial.print("ERR UNKNOWN ");
    Serial.println(command);
    return;
  }

  armStop(durationMs);
  Serial.println("OK MOVE");
}

bool matches(const char *left, const char *right) {
  return strcmp(left, right) == 0;
}

int readSpeedToken(int fallback) {
  char *token = strtok(NULL, " ,#\t");
  if (token == NULL) {
    return fallback;
  }
  return constrain(abs(atoi(token)), 0, MOTOR_SPEED_MAX);
}

int readSignedToken(int fallback) {
  char *token = strtok(NULL, " ,#\t");
  if (token == NULL) {
    return fallback;
  }
  return constrain(atoi(token), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX);
}

int readDurationToken(int fallback) {
  char *token = strtok(NULL, " ,#\t");
  if (token == NULL) {
    return fallback;
  }
  return constrain(atoi(token), 0, 5000);
}

void armStop(int durationMs) {
  lastCommandAt = millis();
  motorsRunning = true;
  if (durationMs > 0) {
    runUntil = lastCommandAt + (unsigned long)durationMs;
  } else {
    runUntil = 0;
  }
}

void setDifferential(int leftSpeed, int rightSpeed) {
  setWheels(leftSpeed, leftSpeed, rightSpeed, rightSpeed);
}

void setWheels(int m1Speed, int m2Speed, int m3Speed, int m4Speed) {
  writeMotor(PIN_MOTOR_PWM_LEFT1, PIN_MOTOR_PWM_LEFT2, m1Speed);
  writeMotor(PIN_MOTOR_PWM_LEFT3, PIN_MOTOR_PWM_LEFT4, m2Speed);
  writeMotor(PIN_MOTOR_PWM_RIGHT1, PIN_MOTOR_PWM_RIGHT2, m3Speed);
  writeMotor(PIN_MOTOR_PWM_RIGHT3, PIN_MOTOR_PWM_RIGHT4, m4Speed);
}

void writeMotor(int forwardPin, int reversePin, int speed) {
  speed = constrain(speed * MOTOR_DIRECTION, MOTOR_SPEED_MIN, MOTOR_SPEED_MAX);
  int pwm = map(abs(speed), 0, MOTOR_SPEED_MAX, 0, 255);

  if (speed >= 0) {
    analogWrite(forwardPin, pwm);
    analogWrite(reversePin, 0);
  } else {
    analogWrite(forwardPin, 0);
    analogWrite(reversePin, pwm);
  }
}

void stopMotors() {
  setWheels(0, 0, 0, 0);
  motorsRunning = false;
}
