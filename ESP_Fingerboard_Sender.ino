#include <WiFi.h>
#include <WiFiUdp.h>

// --- WiFi Credentials ---
const char* ssid     = "";
const char* password = "";

// --- UDP Settings ---
const char* udpAddress = "";  
const int udpPort = 5005;                    // Must match Python listener port

WiFiUDP udp;

// --- Touch Sensor Configuration ---
const int touchPins[3] = {13, 2, 15};        // Pad A, B, C
const char* labels[3] = {"Pad A", "Pad B", "Pad C"};
const int thresholds[3] = {30, 30, 30};      // Adjust if needed

void setup() {
  Serial.begin(115200);
  delay(1000);

  // --- Connect to WiFi ---
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  Serial.println("Touch Sensor Monitor with Tick/Cross + UDP Sender");
}

void loop() {
  String binaryStatus = "";

  // --- Read Touch Pads and Print Status ---
  for (int i = 0; i < 3; i++) {
    int val = touchRead(touchPins[i]);
    bool touched = (val < thresholds[i]);

    // Show tick/cross in Serial Monitor
    Serial.print(labels[i]);
    Serial.print(": ");
    Serial.print(touched ? "YES" : "NO");
    Serial.print("  ");

    // Build binary string
    binaryStatus += touched ? "1" : "0";
  }

  Serial.println();  // New line after all statuses
  Serial.println("Sending UDP: " + binaryStatus);

  // --- Send Binary Status Over UDP ---
  udp.beginPacket(udpAddress, udpPort);
  udp.write((const uint8_t*)binaryStatus.c_str(), binaryStatus.length());
  udp.endPacket();

  delay(30);  // Send 10 times per second
}
