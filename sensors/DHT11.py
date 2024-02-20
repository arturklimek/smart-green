from typing import Dict, Optional, Type
import Adafruit_DHT
import threading
import RPi.GPIO as GPIO
import logging

class DHT11Sensor:
    """
    A singleton class to manage access to a DHT sensor. This class ensures that only one instance per GPIO pin is created, facilitating shared access to DHT sensors across different parts of an application without initializing the sensor multiple times.

    This class uses Adafruit_DHT for sensor reading, and RPi.GPIO for GPIO management, providing a thread-safe mechanism to read humidity and temperature data from a DHT sensor.

    Attributes:
        sensor_type (Adafruit_DHT.DHT11): The type of DHT sensor
        pin (int): The GPIO pin number that the sensor is connected to.
        last_read (dict | None): The last read humidity and temperature values or None if no successful read.
        logger (logging.Logger): Logger instance for logging sensor operation messages.

    Class Attributes:
        _instances (dict): A dictionary holding instances of DHTSensorSingleton, keyed by GPIO pin numbers.
        _lock (threading.Lock): A class-wide lock to ensure thread-safe singleton instantiation.

    Args:
        pin (int): The GPIO pin number where the sensor is connected.
        sensor_type (Adafruit_DHT.DHT11, optional): The type of DHT sensor. Defaults to Adafruit_DHT.DHT11.
    """
    _instances: Dict[int, 'DHT11Sensor'] = {}
    _lock: threading.Lock = threading.Lock()

    sensor_type: Adafruit_DHT.DHT11
    pin: int
    last_read: Optional[Dict[str, float]] = None
    logger: logging.Logger

    def __new__(cls: Type['DHT11Sensor'], pin: int, sensor_type: Adafruit_DHT.DHT11 = Adafruit_DHT.DHT11) -> 'DHT11Sensor':
        """
        Ensures that only one instance of DHTSensorSingleton per GPIO pin is created. If an instance for a given pin already exists, it returns that instance; otherwise, it creates a new one.

        Args:
            pin (int): The GPIO pin number where the sensor is connected.
            sensor_type (Adafruit_DHT.DHT11, optional): The type of DHT sensor.

        Returns:
            DHT11: An instance of the DHTSensorSingleton class for the specified GPIO pin.
        """
        with cls._lock:
            if pin not in cls._instances:
                instance = super(DHT11Sensor, cls).__new__(cls)
                instance.sensor_type = sensor_type
                instance.pin = pin
                instance.last_read = None
                instance.logger = logging.getLogger('app_logger')
                instance._initialize_gpio(pin)
                cls._instances[pin] = instance
            return cls._instances[pin]

    def _initialize_gpio(self, pin: int) -> None:
        """
        Initializes the GPIO settings for the specified pin. This method sets the GPIO mode and prepares the pin for input.

        Args:
            pin (int): The GPIO pin number to initialize.
        """
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(pin, GPIO.IN)
            self.logger.info(f"GPIO pin {pin} has been set up for DHT sensor.")
        except Exception as ex:
            self.logger.error(f"Failed to initialize GPIO pin {pin} for DHT sensor: {ex}")
            raise

    def read_sensor_value(self) -> Optional[Dict[str, float]]:
        """
        Performs a read operation on the DHT sensor to get the current humidity and temperature values.

        Returns:
            dict: A dictionary containing the current humidity and temperature readings, or None if the read fails.
        """
        try:
            humidity, temperature = Adafruit_DHT.read_retry(self.sensor_type, self.pin)
            self.last_read = {'humidity': humidity, 'temperature': temperature}
            self.logger.info(f"DHT11 on PIN: {self.pin} read {self.last_read}")
            return self.last_read
        except Exception as ex:
            self.logger.error(f"Error reading DHT sensor on pin {self.pin}: {ex}")
            return None
