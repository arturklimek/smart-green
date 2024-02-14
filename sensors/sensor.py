import logging
import math
import threading
import time
from collections import deque
from abc import ABC, abstractmethod
import datetime
import numpy as np


class BaseSensor(ABC):
    def __init__(self, read_frequency: int = 60, max_readings: int = 100, start_immediately: bool = False, anomaly_detection: bool = True):
        """
        Abstract base class for sensors, providing a framework for reading sensor data at a regular interval, storing a fixed number of recent readings, and allowing for immediate or delayed start of data collection.

        Attributes:
            logger (logging.Logger): Logger instance for logging sensor operation messages.
            read_frequency (int): Frequency in seconds at which the sensor readings are taken.
            anomaly_detection (bool): Flag indicating whether anomaly detection is enabled.
            max_readings (int): Maximum number of recent sensor readings to store.
            readings (collections.deque): A deque object storing the latest sensor readings along with their timestamps.
            read_thread (threading.Thread | None): The thread object that runs the sensor reading loop. None if not started.
            running (bool): Flag indicating whether the sensor reading loop is currently running.

        Args:
            read_frequency (int, optional): How often to read the sensor in seconds. Defaults to 60.
            max_readings (int, optional): The maximum number of readings to store. Defaults to 100.
            start_immediately (bool, optional): Whether to start reading sensor data immediately upon object creation. Defaults to False.
        """
        self.logger = logging.getLogger('app_logger')
        self.read_frequency = read_frequency
        self.anomaly_detection: bool = anomaly_detection
        self.max_readings = max_readings
        self.readings = deque(maxlen=max_readings)
        self.read_thread = None
        self.running = False

        try:
            self.configure_sensor()
        except Exception as ex:
            self.logger.error(f"Error configuring sensor: {ex}")
            raise

        if start_immediately:
            self.start_reading()

    @abstractmethod
    def configure_sensor(self) -> None:
        """
        Configures the sensor for reading. This method must be implemented by subclasses to set up sensor-specific configurations.
        """
        pass

    def start_reading(self) -> None:
        """
        Starts the sensor reading loop in a separate thread. If the loop is already running, this method does nothing.
        """
        if not self.running:
            self.running = True
            try:
                self.read_thread = threading.Thread(target=self._read_sensor_loop, daemon=True)
                self.read_thread.start()
                self.logger.info("Sensor reading started.")
            except Exception as ex:
                self.logger.error(f"Failed to start sensor reading: {ex}")

    def stop_reading(self) -> None:
        """
        Stops the sensor reading loop if it is currently running. Waits for the reading thread to terminate.
        """
        self.running = False
        if self.read_thread:
            try:
                self.read_thread.join()
                self.read_thread = None
                self.logger.info("Sensor reading stopped.")
            except Exception as ex:
                self.logger.error(f"Error while stopping sensor reading: {ex}")

    def _read_sensor_loop(self) -> None:
        """
        The main loop that reads sensor data at the specified frequency until stopped. Each reading is stored with its timestamp and UTC timestamp in the readings deque.
        """
        while self.running:
            try:
                reading = self.read_sensor() # TODO: Update - add database usage
                if reading is not None and not math.isnan(reading):
                    new_record = {
                        "datetime": datetime.datetime.now(),
                        "utc_timestamp": datetime.datetime.utcnow().timestamp(),
                        "timestamp": time.time(),
                        "value": reading
                    }
                    self.logger.info(f"Add to readings new value: {new_record}")
                    self.readings.append(new_record)
                else:
                    self.logger.warning(f"Incorrect data for reading={reading}")
            except Exception as ex:
                self.logger.error(f"Error during sensor reading: {ex}")
            finally:
                time.sleep(self.read_frequency)

    @abstractmethod
    def read_sensor(self) -> float:
        """
        Reads the current value from the sensor. This method must be implemented by subclasses to return the actual sensor reading.

        Returns:
            float: The current sensor reading.
        """
        pass

    def get_latest_reading(self) -> dict:
        """
        Retrieves the most recent sensor reading along with its timestamp.

        Returns:
            dict | None: The latest sensor reading and its timestamps, or None if no readings have been taken.
        """
        return self.readings[-1] if self.readings else None

    def get_all_readings(self) -> list:
        """
        Retrieves all stored sensor readings.

        Returns:
            list of dicts: A list of all stored sensor readings with their timestamps.
        """
        return list(self.readings)

    @staticmethod
    def is_number(value) -> bool:
        """
        Checks if the given value is a number (either an integer or a float).

        Args:
            value: The value to check.

        Returns:
            bool: True if the value is a number, False otherwise.
        """
        return isinstance(value, (int, float))

    @staticmethod
    def to_float(value) -> float:
        """
        Attempts to convert the given value to a float. If the conversion is not possible, raises a ValueError.

        Args:
            value: The value to convert.

        Returns:
            float: The converted value.

        Raises:
            ValueError: If the value cannot be converted to a float.
        """
        try:
            return float(value)
        except ValueError as ex:
            raise ValueError(f"Cannot convert value to float: {value}") from ex

    @staticmethod
    def to_int(value) -> int:
        """
        Attempts to convert the given value to an integer. If the conversion is not possible, raises a ValueError.

        Args:
            value: The value to convert.

        Returns:
            int: The converted value.

        Raises:
            ValueError: If the value cannot be converted to an int.
        """
        try:
            return int(value)
        except ValueError as ex:
            raise ValueError(f"Cannot convert value to int: {value}") from ex

    def is_in_range(self, value: float, min_value: float, max_value: float) -> bool:
        """
        Checks if a given value is within a specified range, inclusive.

        Args:
            value: The value to check.
            min_value: The minimum value of the range.
            max_value: The maximum value of the range.

        Returns:
            bool: True if the value is within the range, False otherwise.

        Raises:
            ValueError: If the provided value is not a number.
        """
        if not BaseSensor.is_number(value):
            raise ValueError("Provided value is not a number.")
        return min_value <= value <= max_value

    def detect_anomaly(self, new_value, max_history=10, required_history=3, max_age_seconds=800, acceptable_deviation=3) -> bool:
        """
        Detects anomalies in sensor readings using Z-score calculation. It considers only the latest 'max_history' readings
        within the 'max_age_seconds' to ensure relevance and gradual changes are not marked as anomalies.

        Args:
            new_value (float): The new sensor value to evaluate.
            max_history (int): Maximum number of recent readings to consider for anomaly detection.
            required_history (int): Determines the minimum number of historical entries to correctly perform the analysis
            max_age_seconds (int): Maximum age in seconds for readings to be considered in the analysis.
            acceptable_deviation (int): Determines the threshold for anomaly detection

        Returns:
            bool: True if the value is an anomaly, False otherwise.
        """
        try:
            now = datetime.datetime.now()
            relevant_readings = [reading['value'] for reading in self.readings
                                 if now - reading['datetime'] <= datetime.timedelta(seconds=max_age_seconds)]

            if len(relevant_readings) < required_history:
                self.logger.warning(f"After time filtering (max_age_seconds={max_age_seconds}), the list has too few elements = {len(relevant_readings)},  required={required_history} - returned False to complete the list.")
                return False

            if len(relevant_readings) < max_history:
                relevant_readings = relevant_readings[-max_history:]

            mean = np.mean(relevant_readings)
            standard_deviation = np.std(relevant_readings)

            self.logger.info(f"relevant_readings={relevant_readings}, mean={mean}, standard_deviation={standard_deviation}")

            if standard_deviation == 0:
                self.logger.warning(f"The standard_deviation is 0 (all readings are identical), the Z-score cannot be calculated, function returns False.")
                return False

            z_score = (new_value - mean) / standard_deviation
            reply = abs(z_score) > acceptable_deviation
            self.logger.info(f"z_score={z_score}, reply={reply}")
            return reply
        except Exception as ex:
            self.logger.error(f"Error on anomaly detector: {ex}")

    def get_read_frequency(self):
        return self.read_frequency

    def get_anomaly_detection(self):
        return self.anomaly_detection

    def set_anomaly_detection(self, anomaly_detection_state: bool = True):
        self.anomaly_detection = anomaly_detection_state

    def __del__(self):
        """
        Destructor method that ensures the sensor reading loop is stopped before the object is deleted.
        """
        self.logger.info("Destroying BaseSensor instance.")
        self.stop_reading()
