import threading
from typing import Dict, Optional, Type, Tuple
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS1115
import logging

class ADS1115Converter:
    """
    A class to manage access to the ADS1115 ADC converter. This class provides a mechanism to read analog values
    from a specific channel of the ADS1115, using I2C communication.

    Attributes:
        i2c_address (int): The I2C address of the ADS1115 ADC converter.
        channel (int): The channel of the ADS1115 ADC converter to read from.
        last_read (float | None): The last read analog value or None if no successful read.
        logger (logging.Logger): Logger instance for logging operation messages.

    Class Attributes:
        _instances (dict): A dictionary holding instances of ADS1115Converter, keyed by a tuple of I2C address and channel.
        _lock (threading.Lock): A class-wide lock to ensure thread-safe instantiation.

    Args:
        i2c_address (int, optional): The I2C address of the ADS1115 ADC converter. Defaults to 0x48.
        channel (int): The channel to read from (0-3).
    """
    _instances: Dict[Tuple[int, int], 'ADS1115Converter'] = {}
    _lock: threading.Lock = threading.Lock()

    def __new__(cls: Type['ADS1115Converter'], i2c_address: int = 0x48, channel: int = 0) -> 'ADS1115Converter':
        key = (i2c_address, channel)
        with cls._lock:
            if key not in cls._instances:
                instance = super(ADS1115Converter, cls).__new__(cls)
                cls._instances[key] = instance
            return cls._instances[key]

    def __init__(self, i2c_address: int = 0x48, channel: int = 0) -> None:
        self.logger = logging.getLogger('app_logger')
        self.i2c_address = i2c_address
        self.channel = channel
        self.last_read = None
        self._initialize_adc(i2c_address, channel)

    def _initialize_adc(self, i2c_address: int, channel: int) -> None:
        """
        Initializes the ADS1115 ADC converter with the specified I2C address and channel.
        """
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS1115.ADS1115(i2c, address=i2c_address)
            channels = [ADS1115.P0, ADS1115.P1, ADS1115.P2, ADS1115.P3]
            if channel < 0 or channel > 3:
                raise ValueError("Channel must be between 0 and 3")
            self.analog_input = AnalogIn(ads, channels[channel])
            self.logger.info(f"ADS1115 ADC converter on I2C address {i2c_address}, channel {channel} configured.")
        except Exception as ex:
            self.logger.error(f"Problem when initializing the ADC: {ex}")

    def read(self) -> Optional[float]:
        """
        Performs a read operation on the ADS1115 ADC converter to get the current analog value.

        Returns:
            Optional[float]: The current analog reading in volts, or None if the read fails.
        """
        try:
            voltage = self.analog_input.voltage
            self.last_read = voltage
            self.logger.info(f"ADS1115 on I2C address {self.i2c_address}, channel {self.channel} read {voltage} V")
            return voltage
        except Exception as ex:
            self.logger.error(f"Error reading ADS1115 on I2C address {self.i2c_address}, channel {self.channel}: {ex}")
            return None

    def read_raw(self) -> Optional[int]:
        """
        Performs a read operation on the ADS1115 ADC converter to get the current raw analog value.

        Returns:
            Optional[int]: The current raw analog reading, or None if the read fails.
        """
        try:
            raw_value = self.analog_input.value
            self.logger.info(f"ADS1115 on I2C address {self.i2c_address}, channel {self.channel} read raw value {raw_value}")
            return raw_value
        except Exception as ex:
            self.logger.error(f"Error reading raw value from ADS1115 on I2C address {self.i2c_address}, channel {self.channel}: {ex}")
            return None
