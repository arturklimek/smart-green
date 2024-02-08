import threading
import time
from collections import deque
from abc import ABC, abstractmethod
import datetime

class BaseSensor(ABC):
    def __init__(self, read_frequency: int = 60, max_readings: int = 100, start_immediately: bool = False):
        """
        Initializes the sensor with read frequency, max number of readings to store, and whether to start reading immediately.

        Args:
            read_frequency (int): How often to read the sensor (in seconds).
            max_readings (int): The maximum number of readings to store.
            start_immediately (bool): Whether to start reading immediately upon initialization.
        """
        self.read_frequency = read_frequency
        self.max_readings = max_readings
        self.readings = deque(maxlen=max_readings)
        self.read_thread = None
        self.running = False
        if start_immediately:
            self.start_reading()

    def start_reading(self):
        """Start the reading loop in a separate thread if it's not already running."""
        if not self.running:
            self.running = True
            self.read_thread = threading.Thread(target=self._read_sensor_loop, daemon=True)
            self.read_thread.start()

    def stop_reading(self):
        """Stops the reading loop if it's running."""
        self.running = False
        if self.read_thread:
            self.read_thread.join()
            self.read_thread = None

    def _read_sensor_loop(self):
        """Continuously read the sensor at the specified frequency until stopped."""
        while self.running:
            reading = self.read_sensor()
            self.readings.append(
                {
                    "datetime": datetime.datetime.now(),
                    "utc_timestamp": datetime.datetime.utcnow().timestamp(),
                    "value": reading
                }
            )
            time.sleep(self.read_frequency)

    @abstractmethod
    def read_sensor(self) -> float:
        """
        Read the sensor value. Must be implemented by subclasses.

        Returns:
            float: The sensor reading.
        """
        pass

    def get_latest_reading(self):
        """Get the most recent sensor reading along with its timestamp."""
        return self.readings[-1] if self.readings else None

    def get_all_readings(self):
        """Get all stored sensor readings."""
        return list(self.readings)

    def __del__(self):
        """Ensure the reading loop is stopped when the object is deleted."""
        self.stop_reading()
