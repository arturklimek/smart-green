import atexit
import json
import logging
from typing import Optional, Dict, Any
import serial
import serial.tools.list_ports
import threading
import time
from sensors.sensor import BaseSensor

class ArduinoManager:
    def __init__(self, sensors: Dict[str, BaseSensor]):
        self.logger = logging.getLogger('app_logger')
        self.arduinos = {}
        self.sensors = sensors
        self.scan_thread = None
        self.reading_thread = None
        self.running = False
        self.baud_rate = 115200
        self.update_interval = 10
        atexit.register(self.close_all_connections)

    def start_scan(self):
        if not self.running:
            self.running = True
            self.scan_thread = threading.Thread(target=self.scan_for_arduinos)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            self.logger.info("Arduino scan started.")

    def stop_scan(self):
        self.running = False
        if self.scan_thread:
            self.scan_thread.join()
            self.logger.info("Arduino scan stopped.")
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()

    def scan_for_arduinos(self):
        self.logger.debug(f"Start arduino scanning, self.running: {self.running}")
        while self.running:
            self.logger.debug(f"Try find new devices")
            ports = serial.tools.list_ports.comports()
            self.logger.debug(f"ports: {ports}")
            connected_arduinos = {
                port.device: port.description for port in ports
                if port.vid == 0x1a86 and port.pid == 0x7523
            }
            self.logger.debug(f"connected_arduinos: {connected_arduinos}")
            self.update_arduinos(connected_arduinos)
            time.sleep(1)

    def update_arduinos(self, connected_arduinos):
        for device, description in connected_arduinos.items():
            if device not in self.arduinos:
                try:
                    connection = serial.Serial(device, self.baud_rate, timeout=5)
                    connection.setDTR(False)
                    time.sleep(1)
                    connection.flushInput()
                    connection.setDTR(True)
                    time.sleep(2)
                    self.arduinos[device] = {'description': description, 'connection': connection}
                    self.logger.info(f"Arduino connected: {device}")
                except serial.SerialException as e:
                    self.logger.error(f"Could not open serial connection to {device}: {e}")
        for device in list(self.arduinos):
            if device not in connected_arduinos:
                self.arduinos[device]['connection'].close()
                del self.arduinos[device]
                self.logger.info(f"Arduino disconnected: {device}")

    def sendMessage(self, arduino_device, command: dict):
        if arduino_device in self.arduinos:
            json_data = json.dumps(command) + '\n'
            self.arduinos[arduino_device]['connection'].write(json_data.encode())
        else:
            self.logger.error(f"Arduino device {arduino_device} not found.")

    def broadcast_message(self, line1: str, line2: str):
        for arduino_device in self.arduinos.keys():
            self.commandPrint(arduino_device, line1, line2)

    def readMessage(self, arduino_device) -> dict:
        tempMessage = None
        timeout = 5
        start_time = time.time()
        while True:
            if self.arduinos[arduino_device]['connection'].in_waiting > 0:
                line = self.arduinos[arduino_device]['connection'].readline().decode().strip()
                try:
                    tempMessage = json.loads(line)
                    break
                except json.JSONDecodeError:
                    tempMessage = None
                    break
            elif time.time() - start_time > timeout:
                tempMessage = None
                break
        return tempMessage

    def commandPrint(self, arduino_device, line1: str, line2: str) -> bool:
        if not arduino_device:
            self.logger.warning("No arduino indicated")
            return False
        if line1 and line2:
            command = {"C": "P", "L1": line1, "L2": line2}
            self.sendMessage(arduino_device, command)
            tempOutput = self.readMessage(arduino_device)
            self.logger.info(f"Return message after PRINT command: {tempOutput}")
            return True
        return False

    def commandSet(self, arduino_device, element: str, value: str) -> bool:
        if not arduino_device:
            self.logger.warning("No arduino indicated")
            return False
        if element and value:
            command = {"C": "S", "E": element, "V": value}
            self.sendMessage(arduino_device, command)
            tempOutput = self.readMessage(arduino_device)
            self.logger.info(f"Return message after SET command: {tempOutput}")
            return True
        return False

    def commandGet(self, arduino_device, element: str) -> bool | dict:
        if not arduino_device:
            self.logger.warning("No arduino indicated")
            return False
        if element:
            command = {"C": "G", "E": element}
            self.sendMessage(arduino_device, command)
            tempOutput = self.readMessage(arduino_device)
            self.logger.info(f"Return message after GET command: {tempOutput}")
            return tempOutput
        return False

    def takeDeviceInfo(self, arduino_device):
        time.sleep(0.2)
        device_type = self.arduinos[arduino_device]['connection'].commandGET("devicetype")
        self.logger.info(f"devicetype: {device_type}")
        time.sleep(0.2)
        device_version = self.arduinos[arduino_device]['connection'].commandGET("version")
        self.logger.info(f"version: {device_version}")
        time.sleep(0.2)

    def start_reading(self):
        if not self.reading_thread and self.sensors:
            self.reading_thread = threading.Thread(target=self.iterate_sensors)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            self.logger.info("Sensor reading started.")

    def stop_reading(self):
        self.running = False
        if self.reading_thread:
            self.reading_thread.join()
            self.logger.info("Sensor reading stopped.")

    def iterate_sensors(self):
        sensor_keys = list(self.sensors.keys())
        sensor_index = 0
        while self.running:
            sensor1_key = sensor_keys[sensor_index % len(sensor_keys)]
            sensor2_key = sensor_keys[(sensor_index + 1) % len(sensor_keys)]
            self.send_sensor_data_to_arduino(sensor1_key, sensor2_key)
            sensor_index += 1
            time.sleep(self.update_interval)

    def send_sensor_data_to_arduino(self, sensor1_key: str, sensor2_key: str):
        sensor1_reading = self.sensors[sensor1_key].get_latest_reading()
        sensor2_reading = self.sensors[sensor2_key].get_latest_reading()
        line1 = self.format_sensor_message(sensor1_reading, sensor1_key)
        line2 = self.format_sensor_message(sensor2_reading, sensor2_key)
        self.broadcast_message(line1, line2)

    def format_sensor_message(self, sensor_reading: Dict[str, Any], sensor_key: str) -> str:
        if sensor_reading is None:
            return "Data not available"

        sensor_type = self.sensors[sensor_key].__class__.__name__
        value = sensor_reading.get('value', 'N/A')

        if sensor_type == "HumiditySensor":
            return f"Humidity: {int(value)} %"
        elif sensor_type == "TemperatureSensor":
            return f"Temperature: {int(value)} C"
        elif sensor_type == "LightSensor":
            return f"Light: {int(value)} lux"
        elif sensor_type == "SoilMoistureSensor":
            return f"Soil: {int(round(value,2)*100)} %"
        else:
            return "Unknown sensor type"

    def close_all_connections(self):
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()
            self.logger.info(f"Connection to Arduino {device} closed.")

    def __del__(self):
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()
            self.logger.info(f"Connection to Arduino {device} closed.")
