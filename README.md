# Smart Green Garden 🌱 (IoT)
This repository contains a description and solutions for creating a simple automated green garden system.

![Raspberry Pi](https://img.shields.io/badge/RaspberryPi-8A2BE2)
![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-blue)
![Python 3.10](https://img.shields.io/badge/Python-3.10-blue)
![Dependencies up to date](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen)
![License MIT](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-FFCC00)

## Table of Contents
- [🌐 General Information](#-general-information)
- [🛠 Hardware Setup](#-hardware-setup)
  - [Example Hardware Setup](#example-hardware-setup)
  - [System Central Unit Diagram](#system-central-unit-diagram)
  - [Display Module Diagram](#display-module-diagram)
- [💻 Software Setup](#-software-setup)
  - [Technologies](#technologies)
  - [Central Unit](#central-unit)
  - [Display Module](#display-module)
- [🚀 Start-up](#-start-up)
- [⚙ Configuration](#-configuration)
- [📌 Additional Information](#-additional-information)
- [💡 Project Genesis](#-project-genesis)
- [🔍 Improvement Concepts](#-improvement-concepts)
- [📩 Contact](#-contact)



## 🌐 General Information

The project aims to create a simple, cost-effective, and accessible system for automatic monitoring and control of the microclimate for plant cultivation in homes or backyard greenhouses. 
The system is designed to use inexpensive and readily available components. 
The current version of the system and software allows for data collection from individual sensors such as soil moisture, light intensity, and air temperature and humidity. 
The system enables climate control through the activation of specific actuators directly affecting the environment/microclimate of the cultivation - the decision-making process uses the collected data applying appropriate data filtering mechanisms. 
The system allows data accumulation in the InfluxDB database, facilitating easy integration with the 'Grafana' tool for visualizing the collected data.


## 🛠 Hardware Setup

### Example Hardware Setup:
_The hardware configuration should be adjusted according to individual needs_

- **Central unit**: Raspberry Pi
- **MicroSD card**: Samsung EVO Plus 128 GB A2 V30
- **Relays**: Relay module
- **Air temperature and humidity sensor**: DHT11 [HW-036A]
- **Light intensity sensor**: GY-30 [BH1750FVI]
- **Soil moisture sensor** (analog - resistive)
- **ADC converter**: ADS1115
- **Step-Down Converter**: LM2596
- **Power supply**: HKW-150-12 (12 V, 150 W)
- **Display Module**: Arduino UNO + 2x16 LCD Display (ADDITIONAL MODULE)

#### System Central Unit Diagram
All components of the central unit, such as sensors, actuators, power, etc., should be connected according to the following diagram:
<br> <img alt="SYSTEM_SCHEME" src="https://github.com/arturklimek/smart-green/assets/119898929/b480e462-07e0-4b50-9dbf-4da69cea2199" width="65%" height="65%"/>

#### Display Module Diagram
The display module is an optional element connected to the central unit via a USB serial interface, which powers the module and facilitates communication with the central unit.

The Arduino UNO should be connected to the display as per the following diagram:
<br> <img alt="AruinoDisplayModule" src="https://docs.arduino.cc/static/87dafeba444f77d41fe0061e5a34bfde/4ff83/LCD_Base_bb_Schem.png" width="50%" height="50%"/>


## 💻 Software Setup

### Technologies

#### Central Unit:
- Ubuntu 22.04
- Python
- InfluxDB (Optional)
- Grafana (Optional)

#### Display Module:
- C++

### Central Unit:
1. Install the Ubuntu 22.04 operating system on the Raspberry Pi device (Core version recommended).
2. On the Raspberry Pi, install Python version 3.10:
   ```sudo apt update && sudo apt install python3.10```
3. Install the required libraries listed in the `requirements.txt` file.
4. ___Optionally__ - Install and configure the [InfluxDB](https://docs.influxdata.com/influxdb/v2/install/?t=Linux) database and [Grafana](https://grafana.com)<br> (w pliku `GrafanaPanelExample.json` umieszczono przykładową konfigurację panelu grafany)._

### Display Module:
1. Download [ArduinoIDE](https://www.arduino.cc/en/software)
2. Connect the Arduino UNO device to the computer using a USB serial interface.
3. Upload the `ArduinoDisplayModule.ino` file using [ArduinoIDE](https://www.arduino.cc/en/software)


## 🚀 Start-up

1. Clone the repository: ```git clone https://github.com/arturklimek/smart-green.git```
2. Start the software: ```python3 ./main.py```

It is recommended to run the software as a system service by creating and deploying an appropriate `.service` file.

__NOTE__: Operating the system in harsh conditions requires the development and application of a suitable enclosure and protection for the system components.


## ⚙ Configuration

The default configuration includes four types of sensors (one of each), three actuators, and three controllers.
<br>
Adjust the software configuration to your needs by modifying the `config.yaml` file.

- The `influxdb` section contains information on the InfluxDB database used for storing sensor data:
  - `host` - the database server address (default: `localhost`)
  - `port` -  the database port (default: `8086`)
  - `username` - the username used for writing data (default: `garden_core_user`)
  - `password` - the password used for writing data
  - `database` - the name of the database (default: `garden`)
- The `sensors` section lists the sensors and their configuration, each containing:
  - `name` - a unique name for each sensor
  - `type` - the type of sensor, options include: `TemperatureSensor`, `HumiditySensor`, `SoilMoistureSensor`, `LightSensor`
  - `params` - the sensor's configuration parameters
    - `read_frequency` - the data collection frequency in seconds
    - `pin` -  the GPIO pin designation (for `TemperatureSensor` or `HumiditySensor` only)
    - `i2c_address` - the I2C address of the sensor (for `SoilMoistureSensor` or `LightSensor` only)
- The `actuators` section lists the actuators and their configuration, each containing:
  - `name` - a unique name for each actuator
  - `type` -  a unique name for each actuator: `BaseActuator`
  - `params` - the actuator's configuration parameters
    - `gpio_pin` - the GPIO pin used for controlling the actuator
    - `initial_state` - the initial state of the actuator, either `True` or `False`
- The `controllers` section lists the controllers and their configuration, each containing:
  - `type` - the type of controller, options include: `IrrigationController`, `VentilationController`, `LightingController`
  - `sensors` - the list of sensors whose data are used to control the actuator, each identified by the sensor's name and containing its configuration:
    - `threshold` - the value at which the actuator is activated
    - `comparison` - determines whether activation is triggered by exceeding the value upwards or downwards, options: `HIGHER` lub `LOWER`
  - `actuator` - specifies the actuator controlled by the controller, identified by its unique name
  - `params` - the controller's configuration parameters
    - `check_interval` - the frequency of controller operation in seconds
    - `cooldown_period` - the minimum time in seconds that must elapse between activations
    - `pump_flow_rate` -  the flow rate of the pump in liters per hour, needed to calculate activation time (for `IrrigationController` only)
    - `water_volume` - the desired amount of water to be pumped during one irrigation session (for `IrrigationController` only)
    - `max_lift_height` - the maximum lifting height of the pump [optional] (for `IrrigationController` only)
    - `current_lift_height` - the current lifting height of the pump [optional] (for `IrrigationController` only)
    - `activation_time` - the duration in seconds for which the actuator should be activated upon reaching the trigger condition
    - `start_hour` - the start hour of the period during which the controller operates upon exceeding the trigger threshold (mainly for `LightingController`)
    - `end_hour` - the end hour of the period during which the controller operates upon exceeding the trigger threshold (mainly for `LightingController`)

<br>


### 📌 Additional Information
The program has a built-in logging mechanism; in case of operational issues, debugging the software by analyzing the entries saved in the `./logs` directory is recommended.

---

### 💡 Project Genesis
The project was initiated and designed as part of an engineering thesis. The system was built using physical components and was tested. The entire process of designing and creating the basic version of the system is detailed in the engineering thesis, titled 'Automatic garden control and monitoring system - designing and implementing a system, intelligent garden management tools.'

During the project development, a prototype was created, and test data were collected under real usage conditions. The collected data underwent thorough analysis, leading to the implementation of data filtering mechanisms in the software, including anomaly detection and appropriate decision-making mechanisms based on average values. In the project development process, the test data were also compared with external sources, highlighting the importance of proper sensor placement and protection against external atmospheric influences.

### 🔍 Improvement concepts:

- Development of an enclosure for the system
- Development of proper sensor placement
- Protection of the soil moisture sensor against excessive corrosion
- Introduction of support for a wider variety of sensors
- Introduction of support for multiple sensors of the same type and the ability to make decisions based on data from a group of sensors
- Implementation of power supply from a 230V installation/emergency power supply + solar panel power

### 🤝 Contribution
We welcome contributions to our project. If you have suggestions or improvements, please fork the repository and submit a pull request.

### 📩 Contact
For support or collaboration, please contact us at [artur@aklimek.com](mailto:artur@aklimek.com).