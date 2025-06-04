#include "arduino_secrets.h"
#include <WiFi.h>
#include <time.h>

// Please use "arduino_secrets.h" for your WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

const char* ntpServer = "pool.ntp.org";           // NTP server for fetching time
const char* tz = "EET-2EEST,M3.5.0/3,M10.5.0/4";  // Timezone string for Europe/Helsinki
int status = WL_IDLE_STATUS;                      // Default status for WiFi
unsigned long previousMillis = 0;                 // Time on last program cycle
const long interval = 10000;                      // Interval for reading sensors (ms)
String timestamp;                                 // Timestamp for sensor data

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  delay(100);

  connectToWifi();
  printCurrentNet();
  // Uses NTP server to fetch time and save it to onboard RTC
  configTzTime(tz, ntpServer);
  printLocalTime();
}

void loop() {
  // Run the logic based on set interval (10 seconds atm)
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // TEST PRINT
    Serial.println(createTimestamp());
    // Reconnect WiFi if connection drops
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Connection lost! Attempting to reconnect..");
      connectToWifi();
    }
  }
}

void connectToWifi() {
  // Wifi connection
  Serial.printf("Connecting to %s ", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("CONNECTED");
  printCurrentNet();
}

void printCurrentNet() {
  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.println(rssi);
}

void printLocalTime() {
  // C language structure containing calendar date and time
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("No time available (yet)");
    return;
  }
  Serial.println(&timeinfo, "%A, %B %d %Y %H:%M:%S");
}

String createTimestamp() {
  // C language structure containing calendar date and time
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "0000-00-00 00:00:00";  // Default if no time available
  }

  char timestamp[25];
  // Fancy C funtion to format time into ISO date string
  snprintf(timestamp, sizeof(timestamp), "%04d-%02d-%02d %02d:%02d:%02d",
           timeinfo.tm_year + 1900,
           timeinfo.tm_mon + 1,
           timeinfo.tm_mday,
           timeinfo.tm_hour,
           timeinfo.tm_min,
           timeinfo.tm_sec);

  return String(timestamp);
}