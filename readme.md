# TAMK Air Quality Monitoring

This project is a Wi-Fi connected air quality monitoring system based on the Arduino Nano ESP32 microcontroller with I2C-connected air quality sensors to measure enviromental data and send it to a database. The main goal of the project is to collect and store data for teaching purposes.

## Features

### Hardware (Arduino Nano ESP32)
 - Air quality monitoring over I2C
 - Wi-Fi connectivity with connection recovery
 - Time synchronization via NTP
 - MQTT messaging with highest quality of service

### Backend (VM server)
 - MQTT Broker
 - PostgreSQL database
 -

### Frontend
 - Real time monitoring dashboard?
 - CO2 over time graph and air quality index available

## Details

 - [Arduino Nano ESP32](https://store.arduino.cc/products/nano-esp32) ([datasheet](https://docs.arduino.cc/resources/datasheets/ABX00083-datasheet.pdf))
 - [APC1 Air Quality Combo Sensor](https://www.sciosense.com/apc1-air-quality-combo-sensor/)([datasheet](https://www.sciosense.com/wp-content/uploads/2024/07/APC1-Datasheet.pdf))
 - [Adafruit SCD-41](https://www.adafruit.com/product/5190)([datasheet](https://cdn-learn.adafruit.com/downloads/pdf/adafruit-scd-40-and-scd-41.pdf))

 The circuit is built around [Arduino Nano ESP32](https://store.arduino.cc/products/nano-esp32) board with the [ACP1](https://www.sciosense.com/apc1-air-quality-combo-sensor/) and [SCD-41](https://www.adafruit.com/product/5190) sensors connected via I2C bus. On startup, the ESP32 is set to establish a Wi-Fi connection to specified wireless network and synchonize the onboard RTC for time keeping. Once completed, it will read data from the sensors on **TODO: UPDATE INTERVAL** second intervals. Collected data will then be transformed to JSON format and sent to MQTT broker on a VM server via MQTT messaging.

 **TODO: ADD SERVER SIDE AND FRONTEND DETAILS**

## Installation & Use

- Build a circuit that connects the air quality sensors to Arduino.
**TODO: IMAGE HERE**
- Install Arduino IDE and libraries used in the project.
- Connect Arduino board via USB and upload project code in "a3_air_quality.ino".
**TODO: BACKEND INSTALLATION**

