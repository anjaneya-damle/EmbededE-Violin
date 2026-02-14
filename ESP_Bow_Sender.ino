#include "mpu6500.h"
#include <Wire.h>
#include <math.h>
#include <WiFi.h>
#include <WiFiUdp.h>

bfs::Mpu6500 imu;
WiFiUDP udp;

// --- WiFi & UDP settings ---
const char* ssid = "";
const char* password = "";
const char* udpHost = ""; // Destination IP
const uint16_t udpPort = 5005;          // Destination port

// --- Motion detection variables from the first code block ---
// Gravity filter constant
float alpha = 0.90;
float gravity_x = 0;

// Low-pass filter for ax
float filterAlpha = 0.2;
float axFiltered = 0;

// Dead-zone threshold to ignore tiny noise
float noiseThreshold = 0.05;

// Hysteresis thresholds
float threshold_on = 0.3;
float threshold_off = 0.1;

int motion = 0;     // -1 = backward, 0 = none, +1 = forward
int prevMotion = 0; // To detect changes in motion state

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);

  // Init WiFi
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected!");

  // Init IMU
  imu.Config(&Wire, bfs::Mpu6500::I2C_ADDR_PRIM);
  if (!imu.Begin()) {
    Serial.println("Error initializing communication with IMU");
    while (1) {}
  }
  if (!imu.ConfigSrd(19)) {
    Serial.println("Error configuring SRD");
    while (1) {}
  }

  Serial.println("Ready!");
}

void loop() {
  if (imu.Read()) {
    // --- Motion detection logic ---
    float raw_x = imu.accel_x_mps2();

    // Estimate gravity on X axis
    gravity_x = alpha * gravity_x + (1.0 - alpha) * raw_x;

    // Compute linear acceleration
    float ax = raw_x - gravity_x;

    // Low-pass filter for smooth ax
    axFiltered = filterAlpha * ax + (1.0 - filterAlpha) * axFiltered;

    // Dead-zone: kill tiny noise
    if (fabs(axFiltered) < noiseThreshold) {
      axFiltered = 0;
    }

    // Hysteresis logic
    prevMotion = motion; // Store current motion before updating
    if (motion == 0) {
      if (axFiltered > threshold_on)
        motion = +1;
      else if (axFiltered < -threshold_on)
        motion = -1;
    } else if (motion == +1) {
      if (axFiltered < threshold_off)
        motion = 0;
    } else if (motion == -1) {
      if (axFiltered > -threshold_off)
        motion = 0;
    }

    // --- Pitch calculation for notes ---
    float ax_imu = imu.accel_x_mps2();
    float ay_imu = imu.accel_y_mps2();
    float az_imu = imu.accel_z_mps2();

    float pitch = atan2(-ax_imu, sqrt(ay_imu * ay_imu + az_imu * az_imu)) * 180.0 / PI;

    Serial.print("axFiltered: ");
    Serial.print(axFiltered, 3);
    Serial.print(", Motion: ");
    if (motion == 0)
      Serial.print("No motion");
    else if (motion == +1)
      Serial.print("Forward");
    else if (motion == -1)
      Serial.print("Backward");
    Serial.print(", Pitch: ");
    Serial.print(pitch, 2);

    // --- UDP sending logic based on motion and pitch ---
    String message = "";

    // If motion changes from +1 to -1, send "break"
    if ((prevMotion == 1 && motion == -1)|| (prevMotion == -1 && motion == 1)) {
      message = "re bow";
      Serial.println(", Sent UDP: " + message);
    } else if (motion == 0) { // If there is no motion, send "break"
      message = "break";
      Serial.println(", Sent UDP: " + message);
    } else { // Otherwise, determine and send the note based on pitch
      if (pitch >= -26 && pitch <= 22) {
        message = "Sa";
      } else if (pitch < -26) {
        message = "Pa";
      }else if (pitch>22){
        message= "LPa";
      }
      if (message.length() > 0) {
        Serial.println(", Sent UDP: " + message);
      } else {
        Serial.println(", No Note Sent");
      }
    }

    // Send UDP if a message was determined
    if (message.length() > 0) {
      udp.beginPacket(udpHost, udpPort);
      udp.print(message);
      udp.endPacket();
    }

    Serial.println("----------------------------");
  }

  delay(50); // Faster response
}