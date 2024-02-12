import threading
from typing import Optional, Type, Dict
import board
import busio
from adafruit_bh1750 import BH1750
import logging

class BH1750Sensor:
    """
    A class to manage access to the BH1750 light intensity sensor. This class provides a mechanism to read light intensity data from a BH1750 sensor using I2C.

    Attributes:
        i2c_address (int): The I2C address of the BH1750 sensor.
        last_read (dict | None): The last read light intensity value or None if no successful read.
        logger (logging.Logger): Logger instance for logging sensor operation messages.

    Class Attributes:
        _instances (dict): A dictionary holding instances of BH1750Sensor, keyed by I2C address.
        _lock (threading.Lock): A class-wide lock to ensure thread-safe instantiation.

    Args:
        i2c_address (int): The I2C address where the sensor is connected.
    """
    _instances: Dict[int, 'BH1750Sensor'] = {}
    _lock: threading.Lock = threading.Lock()

    i2c_address: int
    read: Optional[float] = None
    logger: logging.Logger

    def __new__(cls: Type['BH1750Sensor'], i2c_address: int = 0x23) -> 'BH1750Sensor':
        """
        Ensures that only one instance of BH1750Sensor per I2C address is created. If an instance for a given address
        already exists, it returns that instance; otherwise, it creates a new one.

        Args:
            i2c_address (int, optional): The I2C address of the BH1750 sensor. Defaults to 0x23.

        Returns:
            BH1750Sensor: An instance of the BH1750Sensor class for the specified I2C address.
        """
        with cls._lock:
            if i2c_address not in cls._instances:
                instance = super(BH1750Sensor, cls).__new__(cls)
                instance.i2c_address = i2c_address
                instance.read = None
                instance.logger = logging.getLogger('app_logger')
                cls._instances[i2c_address] = instance
            return cls._instances[i2c_address]

    def __init__(self, i2c_address: int = 0x23) -> None:
        """
        Initializes the BH1750 sensor with the specified I2C address.
        """
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = BH1750(self.i2c, address=i2c_address)
        self.logger.info(f"BH1750FVI light sensor on I2C address {i2c_address} configured.")

    def read_sensor_value(self) -> Optional[float]:
        """
        Performs a read operation on the BH1750 sensor to get the current light intensity value.

        Returns:
            Optional[float]: The current light intensity reading in lux, or None if the read fails.
        """
        try:
            light_intensity = self.sensor.lux
            self.read_value = light_intensity
            self.logger.info(f"BH1750 on I2C address {self.i2c_address} read {self.read_value} lux")
            return self.read_value
        except Exception as ex:
            self.logger.error(f"Error reading BH1750 sensor on I2C address {self.i2c_address}: {ex}")
            return None
