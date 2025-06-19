# TAMK Air Quality Monitoring

This project is a Wi-Fi connected air quality monitoring system based on the Arduino Nano ESP32 microcontroller with I2C-connected air quality sensors to measure enviromental data and send it to a database. The main goal of the project is to collect and store data for teaching purposes.

## Features

### Hardware (Arduino Nano ESP32)
 - Air quality monitoring over I2C
 - Wi-Fi connectivity with connection recovery
 - Time synchronization via NTP
 - MQTT messaging with highest quality of service

### Backend (VM server 172.16.7.177)
 - MQTT Broker
 - PostgreSQL database
 -

### Frontend
 - Real time monitoring dashboard
 - CO2 over time graph and air quality index available

## Details

 - [Arduino Nano ESP32](https://store.arduino.cc/products/nano-esp32) ([datasheet](https://docs.arduino.cc/resources/datasheets/ABX00083-datasheet.pdf))
 - [APC1 Air Quality Combo Sensor](https://www.sciosense.com/apc1-air-quality-combo-sensor/) ([datasheet](https://www.sciosense.com/wp-content/uploads/2024/07/APC1-Datasheet.pdf))
 - [Adafruit SCD-41](https://www.adafruit.com/product/5190) ([datasheet](https://cdn-learn.adafruit.com/downloads/pdf/adafruit-scd-40-and-scd-41.pdf))

 The circuit is built around [Arduino Nano ESP32](https://store.arduino.cc/products/nano-esp32) board with the [ACP1](https://www.sciosense.com/apc1-air-quality-combo-sensor/) and [SCD-41](https://www.adafruit.com/product/5190) sensors connected via I2C bus. Sensors provide data about CO2 levels, temperature, humidity, as well as Air Quality Index (AQI) and various particle parameters that can be found on the APC1 datasheet. On startup, the ESP32 is set to establish a Wi-Fi connection to specified wireless network and synchonize the onboard RTC for time keeping. Once completed, it will read data from the sensors on 60 second intervals. Collected data will then be transformed to JSON format and sent to MQTT broker on a VM server via MQTT messaging. The hardware was packaged in a custom 3D-printed case, and the design file is included in the project files. Each device has an unique ID, generated at first startup and stored in the ESP32's non-volatile storage. IDs for the three existing devices are as follows:
- Pink device: 5d156a9d-7a7e-4f9c-9a42-899c07ae6068
- Green device: 7f34dd9f-44bc-4163-aef2-a6b44fc2da98
- Purple device: 001d29e2-4b78-4c79-ba9d-6c85573d1f02

 **TODO: ADD SERVER SIDE AND FRONTEND DETAILS**

 <img src="Images/diagram.png" alt="project diagram" width="700">

## Installation & Use

- Build a circuit that connects the air quality sensors to Arduino.  
**Note:** APC1 uses JST GHR-08V-S connector, SCD-41 has STEMMA QT/Qwiic type.  
- Install Arduino IDE and libraries used in the project.
- Add required connection information to "arduino_secrets.h file" 
- Connect Arduino board via USB and upload project code in "a3_air_quality.ino".
- <a href="Arduino/a3_air_quality/case_and_top_cover.step">Case</a> for Arduino and sensors is designed to be used with a half size breadboard.
<img src="Images/circuit.png" alt="project circuit" width="600"> 


**TODO: BACKEND INSTALLATION**

