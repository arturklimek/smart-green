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
    """
    Manages communication and interactions with Arduino devices connected via serial ports.

    Attributes:
        logger (logging.Logger): Logger for the class.
        arduinos (Dict[str, Any]): Stores connected Arduino devices and their serial connections.
        sensors (Dict[str, BaseSensor]): A dictionary of sensors that the manager will use to gather data.
        scan_thread (Optional[threading.Thread]): Thread for scanning and connecting to Arduino devices.
        reading_thread (Optional[threading.Thread]): Thread for reading sensor data and sending it to Arduino.
        running (bool): Indicates whether the Arduino scanning and reading processes are active.
        baud_rate (int): Baud rate for serial communication with Arduino devices.
        update_interval (int): Time interval (in seconds) between sensor data readings and updates sent to Arduino.
    """
    def __init__(self, sensors: Dict[str, BaseSensor]) -> None:
        """
        Initializes the ArduinoManager with a given set of sensors.

        Args:
            sensors (Dict[str, BaseSensor]): A dictionary mapping sensor names to sensor objects.
        """
        self.logger: logging.Logger = logging.getLogger('app_logger')
        self.arduinos: Dict[str, Any] = {}
        self.sensors: Dict[str, BaseSensor] = sensors
        self.scan_thread: Optional[threading.Thread] = None
        self.reading_thread: Optional[threading.Thread] = None
        self.running: bool = False
        self.baud_rate: int = 115200
        self.update_interval: int = 10
        atexit.register(self.close_all_connections)

    def start_scan(self) -> None:
        """Starts the scanning process for Arduino devices in a separate thread."""
        if not self.running:
            self.running = True
            self.scan_thread = threading.Thread(target=self.scan_for_arduinos)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            self.logger.info("Arduino scan started.")

    def stop_scan(self) -> None:
        """Stops the scanning process for Arduino devices and closes all serial connections."""
        self.running = False
        if self.scan_thread:
            self.scan_thread.join()
            self.logger.info("Arduino scan stopped.")
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()

    def scan_for_arduinos(self) -> None:
        """Scans for Arduino devices connected via serial ports and updates the list of connected devices."""
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

    def update_arduinos(self, connected_arduinos: Dict[str, str]) -> None:
        """
        Updates the list of connected Arduino devices based on the latest scan results.

        Args:
            connected_arduinos (Dict[str, str]): A dictionary of detected Arduino devices and their descriptions.
        """
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
                except serial.SerialException as ex:
                    self.logger.error(f"Could not open serial connection to {device}: {ex}")
        for device in list(self.arduinos):
            if device not in connected_arduinos:
                self.arduinos[device]['connection'].close()
                del self.arduinos[device]
                self.logger.info(f"Arduino disconnected: {device}")

    def sendMessage(self, arduino_device: str, command: Dict[str, Any]) -> None:
        """
        Sends a command to a specific Arduino device.

        Args:
            arduino_device (str): The device identifier (port) of the Arduino to send the command to.
            command (Dict[str, Any]): The command to send, formatted as a dictionary.
        """
        if arduino_device in self.arduinos:
            json_data = json.dumps(command) + '\n'
            self.arduinos[arduino_device]['connection'].write(json_data.encode())
        else:
            self.logger.error(f"Arduino device {arduino_device} not found.")

    def broadcast_message(self, line1: str, line2: str) -> None:
        """
        Sends a message to all connected Arduino devices.

        Args:
            line1 (str): The first line of the message.
            line2 (str): The second line of the message.
        """
        for arduino_device in self.arduinos.keys():
            self.commandPrint(arduino_device, line1, line2)

    def readMessage(self, arduino_device: str) -> Optional[Dict[str, Any]]:
        """
        Reads a message from a specific Arduino device.

        Args:
            arduino_device (str): The device identifier (port) of the Arduino to read the message from.

        Returns:
            Optional[Dict[str, Any]]: The message read from the Arduino, if any, parsed as a dictionary.
        """
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

    def commandPrint(self, arduino_device: str, line1: str, line2: str) -> bool:
        """
        Sends a print command to an Arduino device to display messages on its LCD.

        Args:
            arduino_device (str): The device identifier (port) of the Arduino.
            line1 (str): The first line of text to display.
            line2 (str): The second line of text to display.

        Returns:
            bool: True if the command was successfully sent, False otherwise.
        """
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

    def commandSet(self, arduino_device: str, element: str, value: str) -> bool:
        """
        Sends a set command to an Arduino device to change the value of a specified element.

        Args:
            arduino_device (str): The device identifier (port) of the Arduino.
            element (str): The element whose value is to be set.
            value (str): The new value for the element.

        Returns:
            bool: True if the command was successfully sent and acknowledged, False otherwise.
        """
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

    def commandGet(self, arduino_device: str, element: str) -> bool | dict:
        """
        Sends a get command to an Arduino device to retrieve the value of a specified element.

        Args:
            arduino_device (str): The device identifier (port) of the Arduino.
            element (str): The element whose value is to be retrieved.

        Returns:
            Union[bool, Dict[str, Any]]: False if the Arduino device is not found or the command couldn't be sent;
            otherwise, a dictionary containing the response from the Arduino device.
        """
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

    def takeDeviceInfo(self, arduino_device: str):
        time.sleep(0.2)
        device_type = self.arduinos[arduino_device]['connection'].commandGET("devicetype")
        self.logger.info(f"devicetype: {device_type}")
        time.sleep(0.2)
        device_version = self.arduinos[arduino_device]['connection'].commandGET("version")
        self.logger.info(f"version: {device_version}")
        time.sleep(0.2)

    def start_reading(self) -> None:
        """Starts the sensor data reading and broadcasting process in a separate thread."""
        if not self.reading_thread and self.sensors:
            self.reading_thread = threading.Thread(target=self.iterate_sensors)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            self.logger.info("Sensor reading started.")

    def stop_reading(self) -> None:
        """Stops the sensor data reading and broadcasting process."""
        self.running = False
        if self.reading_thread:
            self.reading_thread.join()
            self.logger.info("Sensor reading stopped.")

    def iterate_sensors(self) -> None:
        """Iterates over sensors, reads data, and sends updates to connected Arduino devices."""
        sensor_keys = list(self.sensors.keys())
        sensor_index = 0
        while self.running:
            sensor1_key = sensor_keys[sensor_index % len(sensor_keys)]
            sensor2_key = sensor_keys[(sensor_index + 1) % len(sensor_keys)]
            self.send_sensor_data_to_arduino(sensor1_key, sensor2_key)
            sensor_index += 1
            time.sleep(self.update_interval)

    def send_sensor_data_to_arduino(self, sensor1_key: str, sensor2_key: str) -> None:
        """
        Sends sensor data to all connected Arduino devices.

        Args:
            sensor1_key (str): The key of the first sensor whose data is to be sent.
            sensor2_key (str): The key of the second sensor whose data is to be sent.
        """
        sensor1_reading = self.sensors[sensor1_key].get_latest_reading()
        sensor2_reading = self.sensors[sensor2_key].get_latest_reading()
        line1 = self.format_sensor_message(sensor1_reading, sensor1_key)
        line2 = self.format_sensor_message(sensor2_reading, sensor2_key)
        self.broadcast_message(line1, line2)

    def format_sensor_message(self, sensor_reading: Dict[str, Any], sensor_key: str) -> str:
        """
         Formats a sensor reading into a message suitable for displaying on an Arduino's LCD.

         Args:
             sensor_reading (Dict[str, Any]): The sensor reading to format.
             sensor_key (str): The key of the sensor.

         Returns:
             str: The formatted message.
         """
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

    def close_all_connections(self) -> None:
        """Closes all serial connections to Arduino devices."""
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()
            self.logger.info(f"Connection to Arduino {device} closed.")

    def __del__(self) -> None:
        """Destructor method that ensures all Arduino serial connections are closed upon object deletion."""
        for device, arduino in self.arduinos.items():
            arduino['connection'].close()
            self.logger.info(f"Connection to Arduino {device} closed.")
