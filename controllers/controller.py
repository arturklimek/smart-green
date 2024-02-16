import datetime
import time
import logging
import threading
from typing import List, Dict, Callable, Optional, Union
from actuators.actuator import BaseActuator
from sensors.sensor import BaseSensor

class BaseController:
    def __init__(self, sensors: List[Dict],  actuator: Optional[BaseActuator] = None, check_interval: float = 60 , activation_time: Optional[int] = None, cooldown_period: int = 60, start_hour: Optional[int] = None, end_hour: Optional[int] = None):
        """
        Initialize the base controller with the given configuration.

        Args:
            check_interval (float): How often to check sensors in seconds.
            sensors (List[Dict]): List of dictionaries containing sensor configurations.
            actuator (Optional[BaseActuator]): The actuator to control based on sensor readings.
            activation_time (Optional[int]): Time in seconds the actuator stays activated. None means control based on sensor.
            cooldown_period (int): Minimum time in seconds between actuator activations.
            start_hour (Optional[int]): Starting hour of the day when actuation can occur.
            end_hour (Optional[int]): Ending hour of the day when actuation can no longer occur.
        """
        self.logger: logging.Logger = logging.getLogger('app_logger')
        self.check_interval: float = check_interval
        self.cooldown_period: datetime.timedelta = datetime.timedelta(seconds=cooldown_period)
        self.start_hour: Optional[int] = start_hour
        self.end_hour: Optional[int] = end_hour
        self.activation_time: Optional[int] = activation_time
        self.sensors: List[Dict[str, Union[BaseSensor, int, Callable]]] = [self.validation_sensor(sensor_dict) for sensor_dict in sensors if self.validation_sensor(sensor_dict)]
        self.actuator: Optional[BaseActuator] = actuator
        self.thread: Optional[threading.Thread] = None
        self.running: bool = False
        self.last_activation: Optional[datetime.datetime] = None
        self.last_deactivation: Optional[datetime.datetime] = None

    def validation_sensor(self, sensor_dict: Dict) -> Optional[Dict]:
        """
        Validates a sensor configuration dictionary.

        Args:
            sensor_dict (Dict): Sensor configuration dictionary to validate.

        Returns:
            Optional[Dict]: The validated sensor dictionary or None if validation fails.
        """
        required_keys = {'sensor', 'threshold', 'comparison'}
        valid_types = {
            'sensor': BaseSensor,
            'threshold': (int, float),
            'comparison': Callable
        }
        if not required_keys.issubset(sensor_dict.keys()):
            self.logger.error("Sensor info is missing required keys: " + str(sensor_dict))
            return None
        for key, value in sensor_dict.items():
            expected_type = valid_types.get(key)
            if expected_type and not isinstance(value, expected_type):
                self.logger.error(
                    f"Invalid type for key '{key}': expected {expected_type}, got {type(value)} in sensor configuration: {sensor_dict}")
                return None
        if not callable(sensor_dict.get('comparison')):
            self.logger.error(
                "The 'comparison' key must be a callable function in sensor configuration: " + str(sensor_dict))
            return None
        self.logger.info(f"Sensor configuration validated successfully")
        return sensor_dict

    def add_sensor(self, sensor_dict: Dict):
        """
        Adds a validated sensor to the controller's sensor list.

        Args:
            sensor_dict (Dict): Sensor configuration dictionary.
        """
        sensor = self.validation_sensor(sensor_dict)
        if sensor:
            self.sensors.append(sensor)
            self.logger.info(f"Sensor added successfully: {sensor_dict}")
        else:
            self.logger.warning(f"Failed to add sensor due to validation failure: {sensor_dict}")

    def set_actuator(self, actuator: BaseActuator):
        """
        Sets the actuator for this controller.

        Args:
            actuator (BaseActuator): The actuator to be controlled.
        """
        self.actuator = actuator
        self.logger.info(f"Actuator set successfully: {actuator}")

    def start(self):
        """
        Starts the controller loop in a separate thread.
        """
        if not self.running:
            self.running = True
            try:
                self.thread = threading.Thread(target=self.control_loop, daemon=True)
                self.thread.start()
                self.logger.info("Controller loop started successfully.")
            except Exception as ex:
                self.logger.error(f"Failed to start controller loop: {ex}")
                self.running = False

    def stop(self):
        """
        Stops the controller loop if it's running.
        """
        self.running = False
        if self.thread:
            try:
                self.thread.join()
                self.logger.info("Controller loop stopped successfully.")
            except Exception as ex:
                self.logger.error(f"Failed to stop controller loop properly: {ex}")

    def control_loop(self):
        """
        The main loop that checks sensors and controls the actuator based on the configured logic.
        """
        self.logger.info("Control loop started.")
        while self.running:
            try:
                self.logger.debug("Checking conditions...")
                time.sleep(self.check_interval)
                if not self.is_within_operating_hours():
                    self.logger.info("Outside of operating hours, skipping activation checks.")
                    continue
                if not self.check_if_cooldown_passed():
                    self.logger.info("Cooldown period has not passed, skipping activation checks.")
                    continue
                activation_needed = False
                for sensor_dict in self.sensors:
                    try:
                        if self.check_sensor(sensor_dict):
                            activation_needed = True
                            self.logger.info(f"Sensor {sensor_dict['sensor']} triggered activation.")
                            break
                    except Exception as ex:
                        self.logger.error(f"Error during sensor check: {ex}")
                actuator_state = self.actuator.get_state() if self.actuator else None
                self.logger.debug(f"Actuator state: {actuator_state}, Activation needed: {activation_needed}")
                if activation_needed:
                    if not actuator_state:
                        self.logger.info("Activating actuator.")
                        self.activate_actuator()
                        if self.activation_time:
                            self.logger.info(f"Actuator will deactivate after {self.activation_time} seconds.")
                            threading.Timer(self.activation_time, self.deactivate_actuator).start()
                    elif self.activation_time and (
                            datetime.datetime.now() - self.last_activation).total_seconds() > self.activation_time:
                        self.logger.info("Deactivating actuator after activation time.")
                        self.deactivate_actuator()
                else:
                    if actuator_state and not self.activation_time:
                        self.logger.info("Deactivating actuator due to sensor deactivation criteria.")
                        self.deactivate_actuator()
            except Exception as ex:
                self.logger.error(f"Error during control loop execution: {ex}")
        self.logger.info("Control loop stopped.")

    def check_if_cooldown_passed(self) -> bool:
        """
        Checks if the cooldown period has passed since the last actuator deactivation.

        Returns:
            bool: True if the cooldown has passed, False otherwise.
        """
        if self.last_deactivation is not None:
            time_since_reference = datetime.datetime.now() - self.last_deactivation
            self.logger.debug(
                f"time_since_reference: {time_since_reference}, cooldown_period: {self.cooldown_period}")

            if time_since_reference >= self.cooldown_period:
                self.logger.info("The cooldown has passed, allowing new activations.")
                return True
            else:
                self.logger.info("The cooldown has not yet passed, skipping new activations.")
                return False
        else:
            self.logger.info("No previous deactivation, allowing activations.")
            return True

    def is_within_operating_hours(self) -> bool:
        """
        Checks if the current time is within the operating hours, correctly handling
        cases where the operating period spans across midnight.

        Returns:
            bool: True if within operating hours, False otherwise.
        """
        current_time = datetime.datetime.now()
        if self.start_hour is not None and self.end_hour is not None:
            current_hour = current_time.hour
            if self.start_hour < self.end_hour:
                in_hours = self.start_hour <= current_hour < self.end_hour
            else:
                in_hours = current_hour >= self.start_hour or current_hour < self.end_hour
            self.logger.debug(f"Operating hours check, Current hour: {current_hour}, start_hour: {self.start_hour}, end_hour: {self.end_hour}, Within hours: {in_hours}")
            return in_hours
        return True

    def check_sensor(self, sensor_dict: Dict) -> bool:
        """
        Checks if a sensor's reading meets its activation criteria.

        Args:
            sensor_dict (Dict): Sensor configuration dictionary.

        Returns:
            bool: True if the sensor meets the activation criteria, False otherwise.
        """
        try:
            sensor = sensor_dict['sensor']
            threshold = sensor_dict['threshold']
            comparison = sensor_dict.get('comparison', lambda x, y: x > y)
            data = self.calculate_average_from_last_readings(sensor)
            if data is None:
                self.logger.info(f"No average data available for sensor: {sensor}. Skipping activation check.")
                return False
            result = comparison(data, threshold)
            self.logger.debug(f"Sensor data: {data}, threshold: {threshold}, comparison result: {result}")
            if result:
                self.logger.info(f"Sensor meets activation criteria. Triggering action. result={result} data={data} threshold={threshold}")
            else:
                self.logger.info(f"Sensor does not meet activation criteria. result={result} data={data} threshold={threshold}")
            return result
        except Exception as ex:
            self.logger.error(f"Error during checking sensor {sensor_dict['sensor']}: {ex}")
            return False

    def calculate_average_from_last_readings(self, sensor: BaseSensor, number_of_readings: int = 10,
                                             minimum_entries: int = 5, max_age_seconds: int = 800) -> Optional[float]:
        """
        Calculates the average value from the last readings of a sensor.

        Args:
            sensor (BaseSensor): The sensor from which to calculate the average.
            number_of_readings (int): Number of recent readings to consider.
            minimum_entries (int): Minimum number of entries required to calculate an average.
            max_age_seconds (int): Maximum age in seconds for readings to be considered.

        Returns:
            Optional[float]: The average value or None if not enough data.
        """
        try:
            current_time = time.time()
            all_readings = sensor.get_all_readings()
            recent_readings = [reading for reading in all_readings if
                               current_time - reading['timestamp'] <= max_age_seconds]
            if len(recent_readings) < minimum_entries:
                self.logger.warning(f"Not enough recent entries for sensor to perform average analysis.")
                return None
            last_readings = recent_readings[-number_of_readings:]
            if last_readings:
                average_value = sum(reading['value'] for reading in last_readings) / len(last_readings)
                self.logger.debug(f"Calculated average value for sensor: {average_value}")
                return average_value
            else:
                self.logger.warning(f"Not enough entries within max age for sensor to calculate average.")
                return None
        except Exception as ex:
            self.logger.error(f"Failed to calculate average from last readings for sensor: {ex}")
            return None

    def activate_actuator(self):
        """
        Activates the actuator and handles anomaly detection for sensors.
        """
        if self.actuator:
            try:
                self.last_activation = datetime.datetime.now()  # datetime
                self.actuator.activate()
                self.logger.info(f"Actuator activated at {self.last_activation}.")
                for sensor_dict in self.sensors:
                    sensor = sensor_dict['sensor']
                    anomaly_detection_reset_time = sensor.get_read_frequency() * 10
                    sensor.set_anomaly_detection(False)
                    threading.Timer(anomaly_detection_reset_time, lambda: sensor.set_anomaly_detection(True)).start()
                    self.logger.debug(f"Anomaly detection for sensor {sensor} temporarily disabled.")
            except Exception as ex:
                self.logger.error(f"Failed to activate actuator: {ex}")

    def deactivate_actuator(self):
        """
        Deactivates the actuator.
        """
        if self.actuator:
            try:
                self.last_deactivation = datetime.datetime.now()
                self.actuator.deactivate()
                self.logger.info(f"Actuator deactivated at {self.last_deactivation}.")
            except Exception as ex:
                self.logger.error(f"Failed to deactivate actuator: {ex}")

    @staticmethod
    def get_comparison(key: str):
        if key == "HIGHER":
            return lambda x, y: x > y
        if key == "LOWER":
            return lambda x, y: x < y