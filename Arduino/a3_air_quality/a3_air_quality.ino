#include "arduino_secrets.h"
#include <Wire.h>
#include <apc1.h>
#include <SensirionI2cScd4x.h>
#include <WiFi.h>
#include <time.h>

// Collected sensor data
struct airQualityData {
  int pm1_0;
  int pm2_5;
  int pm10;
  int pmInAir1_0;
  int pmInAir2_5;
  int pmInAir10;
  int particles0_3;
  int particles0_5;
  int particles1_0;
  int particles2_5;
  int particles5_0;
  int particles10;
  int tvoc;
  int eco2;
  float compT;
  float compRH;
  float rawT;
  float rawRH;
  int rs0;
  int rs1;
  int rs2;
  int rs3;
  int aqi;
  u_int16_t co2;
  float temp;
  float hum;
};

// Create variable of struct to hold air quality data
airQualityData currentData;

// macro definitions
// make sure that we use the proper definition of NO_ERROR
#ifdef NO_ERROR
#undef NO_ERROR
#endif
#define NO_ERROR 0

SensirionI2cScd4x sensor;

static char errorMessage[64];
static int16_t error;

void PrintUint64(uint64_t& value) {
  Serial.print("0x");
  Serial.print((uint32_t)(value >> 32), HEX);
  Serial.print((uint32_t)(value & 0xFFFFFFFF), HEX);
}
bool dataReady = false;

// Please use "arduino_secrets.h" for your WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

const char* ntpServer = "pool.ntp.org";           // NTP server for fetching time
const char* tz = "EET-2EEST,M3.5.0/3,M10.5.0/4";  // Timezone string for Europe/Helsinki
const long interval = 10000;                      // Interval for reading sensors (ms)
int status = WL_IDLE_STATUS;                      // Default status for WiFi
unsigned long previousMillis = 0;                 // Time on last program cycle
String timestamp;                                 // Timestamp for sensor data

APC1 apc1;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  delay(100);
  // Initialize I2C bus
  Wire.begin();
  // Initialize sensors
  apc1.begin(&Wire);
  sensor.begin(Wire, SCD41_I2C_ADDR_62);

  uint64_t serialNumber = 0;
  delay(30);
  // Ensure sensor is in clean state
  error = sensor.wakeUp();
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute wakeUp(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  }
  error = sensor.stopPeriodicMeasurement();
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute stopPeriodicMeasurement(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  }
  error = sensor.reinit();
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute reinit(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  }
  // Read out information about the sensor
  error = sensor.getSerialNumber(serialNumber);
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute getSerialNumber(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }

  Serial.print("serial number: 0x");
  PrintUint64(serialNumber);
  Serial.println();


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
    readSensors();
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

void readSensors() {
  // Start periodic measurements (5sec interval)
  error = sensor.startPeriodicMeasurement();
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute startPeriodicMeasurement(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }
  delay(2000);

  error = sensor.getDataReadyStatus(dataReady);
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute getDataReadyStatus(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }
  while (!dataReady) {
    delay(100);
    error = sensor.getDataReadyStatus(dataReady);
    if (error != NO_ERROR) {
      Serial.print("Error trying to execute getDataReadyStatus(): ");
      errorToString(error, errorMessage, sizeof errorMessage);
      Serial.println(errorMessage);
      return;
    }
  }
  //
  // If ambient pressure compenstation during measurement
  // is required, you should call the respective functions here.
  // Check out the header file for the function definition.
  error = sensor.readMeasurement(currentData.co2, currentData.temp, currentData.hum);
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute readMeasurement(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }

  error = sensor.stopPeriodicMeasurement();
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute stopPeriodicMeasurement(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  }

  //
  // Print results in physical units.
  Serial.print("CO2 concentration [ppm]: ");
  Serial.print(currentData.co2);
  Serial.println();
  Serial.print("Temperature [°C]: ");
  Serial.print(currentData.temp);
  Serial.println();
  Serial.print("Relative Humidity [RH]: ");
  Serial.print(currentData.hum);
  Serial.println();
  // Long list of sensor get methods
  if (apc1.update() == RESULT_OK) {
    currentData.pm1_0 = apc1.getPM_1_0();
    Serial.print("PM1.0: ");
    Serial.println(currentData.pm1_0);

    currentData.pm2_5 = apc1.getPM_2_5();
    Serial.print("PM2.5: ");
    Serial.println(currentData.pm2_5);

    currentData.pm10 = apc1.getPM_10();
    Serial.print("PM10: ");
    Serial.println(currentData.pm10);

    currentData.pmInAir1_0 = apc1.getPMInAir_1_0();
    Serial.print("PM1.0 in air: ");
    Serial.println(currentData.pmInAir1_0);

    currentData.pmInAir2_5 = apc1.getPMInAir_2_5();
    Serial.print("PM2.5 in air: ");
    Serial.println(currentData.pmInAir2_5);

    currentData.pmInAir10 = apc1.getPMInAir_10();
    Serial.print("PM10 in air: ");
    Serial.println(currentData.pmInAir10);

    currentData.particles0_3 = apc1.getNoParticles_0_3();
    Serial.print("# particles >0.3μm: ");
    Serial.println(currentData.particles0_3);

    currentData.particles0_5 = apc1.getNoParticles_0_5();
    Serial.print("# particles >0.5μm: ");
    Serial.println(currentData.particles0_5);

    currentData.particles1_0 = apc1.getNoParticles_1_0();
    Serial.print("# particles >1.0μm: ");
    Serial.println(currentData.particles1_0);

    currentData.particles2_5 = apc1.getNoParticles_2_5();
    Serial.print("# particles >2.5μm: ");
    Serial.println(currentData.particles2_5);

    currentData.particles5_0 = apc1.getNoParticles_5_0();
    Serial.print("# particles >5.0μm: ");
    Serial.println(currentData.particles5_0);

    currentData.particles10 = apc1.getNoParticles_10();
    Serial.print("# particles >10μm: ");
    Serial.println(currentData.particles10);

    currentData.tvoc = apc1.getTVOC();
    Serial.print("TVOC: ");
    Serial.println(currentData.tvoc);

    currentData.eco2 = apc1.getECO2();
    Serial.print("ECO2: ");
    Serial.println(currentData.eco2);

    currentData.compT = apc1.getCompT();
    Serial.print("T-comp.: ");
    Serial.println(currentData.compT);

    currentData.compRH = apc1.getCompRH();
    Serial.print("RH-comp.: ");
    Serial.println(currentData.compRH);

    currentData.rawT = apc1.getRawT();
    Serial.print("T-raw: ");
    Serial.println(currentData.rawT);

    currentData.rawRH = apc1.getRawRH();
    Serial.print("RH-raw: ");
    Serial.println(currentData.rawRH);

    currentData.rs0 = apc1.getRS0();
    Serial.print("RS0: ");
    Serial.println(currentData.rs0);

    currentData.rs1 = apc1.getRS1();
    Serial.print("RS1: ");
    Serial.println(currentData.rs1);

    currentData.rs2 = apc1.getRS2();
    Serial.print("RS2: ");
    Serial.println(currentData.rs2);

    currentData.rs3 = apc1.getRS3();
    Serial.print("RS3: ");
    Serial.println(currentData.rs3);

    currentData.aqi = apc1.getAQI();
    Serial.print("AQI: ");
    Serial.println(currentData.aqi);

    Serial.print("Error code: ");
    Serial.println((uint8_t)apc1.getError(), BIN);
    Serial.println("-----------------------");
  } else {
  }
}