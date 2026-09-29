int ENA = 5;
int IN1 = 6;
int IN2 = 7;
int ENB = 9;
int IN3 = 10;
int IN4 = 11;

char data;

void setup() {
  Serial.begin(9600);
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  moveNormal(); 
}

void loop() {
  if (Serial.available() > 0) {
    data = Serial.read();
    if (data == 'N' || data == '0') {
      moveNormal();
    }
    else if (data == 'S' || data == '1') {
      slowDown();
    }
    else if (data == 'B') {
      gradualStop();
    }
    else if (data == 'X') {
      stopMotors();
    }
  }
}
void moveNormal() {
  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}
void slowDown() {
  analogWrite(ENA, 120);
  analogWrite(ENB, 120);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}
void gradualStop() {
  for (int speed = 200; speed >= 0; speed -= 10) {
    analogWrite(ENA, speed);
    analogWrite(ENB, speed);
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
    delay(100);
  }
  stopMotors();
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}