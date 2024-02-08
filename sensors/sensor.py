import logging
import threading
import time
from collections import deque
from abc import ABC, abstractmethod
import datetime

class BaseSensor(ABC):
    def __init__(self, read_frequency: int = 60, max_readings: int = 100, start_immediately: bool = False):
        """
        Abstract base class for sensors, providing a framework for reading sensor data at a regular interval, storing a fixed number of recent readings, and allowing for immediate or delayed start of data collection.

        Attributes:
            logger (logging.Logger): Logger instance for logging sensor operation messages.
            read_frequency (int): Frequency in seconds at which the sensor readings are taken.
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
        self.max_readings = max_readings
        self.readings = deque(maxlen=max_readings)
        self.read_thread = None
        self.running = False

        try:
            self.configure_sensor()
        except Exception as e:
            self.logger.error(f"Error configuring sensor: {e}")
            raise

        if start_immediately:
            self.start_reading()

    @abstractmethod
    def configure_sensor(self):
        """
        Configures the sensor for reading. This method must be implemented by subclasses to set up sensor-specific configurations.
        """
        pass

    def start_reading(self):
        """
        Starts the sensor reading loop in a separate thread. If the loop is already running, this method does nothing.
        """
        if not self.running:
            self.running = True
            try:
                self.read_thread = threading.Thread(target=self._read_sensor_loop, daemon=True)
                self.read_thread.start()
                self.logger.info("Sensor reading started.")
            except Exception as e:
                self.logger.error(f"Failed to start sensor reading: {e}")

    def stop_reading(self):
        """
        Stops the sensor reading loop if it is currently running. Waits for the reading thread to terminate.
        """
        self.running = False
        if self.read_thread:
            try:
                self.read_thread.join()
                self.read_thread = None
                self.logger.info("Sensor reading stopped.")
            except Exception as e:
                self.logger.error(f"Error while stopping sensor reading: {e}")

    def _read_sensor_loop(self):
        """
        The main loop that reads sensor data at the specified frequency until stopped. Each reading is stored with its timestamp and UTC timestamp in the readings deque.
        """
        while self.running:
            try:
                reading = self.read_sensor()
                self.readings.append({
                    "datetime": datetime.datetime.now(),
                    "utc_timestamp": datetime.datetime.utcnow().timestamp(),
                    "value": reading
                })
            except Exception as e:
                self.logger.error(f"Error during sensor reading: {e}")
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

    def get_latest_reading(self):
        """
        Retrieves the most recent sensor reading along with its timestamp.

        Returns:
            dict | None: The latest sensor reading and its timestamps, or None if no readings have been taken.
        """
        return self.readings[-1] if self.readings else None

    def get_all_readings(self):
        """
        Retrieves all stored sensor readings.

        Returns:
            list of dicts: A list of all stored sensor readings with their timestamps.
        """
        return list(self.readings)

    def __del__(self):
        """
        Destructor method that ensures the sensor reading loop is stopped before the object is deleted.
        """
        self.logger.info("Destroying BaseSensor instance and stopping the reading loop.")
        self.stop_reading()
