from typing import Optional

from sensors.ADS1115 import ADS1115Converter
from sensors.sensor import BaseSensor
import logging

class SoilMoistureSensor(BaseSensor):
    """
    A sensor class that extends BaseSensor for reading soil moisture levels from an analog soil moisture sensor
    connected through an ADS1115 ADC converter. It includes functionality for anomaly detection based on
    specified minimum and maximum moisture values.

    Attributes:
        i2c_address (int): I2C address where the ADS1115 ADC converter is connected.
        channel (int): ADC channel to which the soil moisture sensor is connected.
        anomaly_detection (bool): Flag indicating whether anomaly detection is enabled.
        min_value (float): Minimum acceptable soil moisture value for anomaly detection.
        max_value (float): Maximum acceptable soil moisture value for anomaly detection.
        logger (logging.Logger): Logger for recording operational messages.

    Methods:
        configure_sensor: Initializes the ADS1115 ADC converter.
        read_sensor: Attempts to read the soil moisture level from the sensor, with anomaly detection and range validation.
    """
    def __init__(self, i2c_address: int = 0x48, channel: int = 0, min_value: float = 0.0, max_value: float = 3.3, *args, **kwargs) -> None:
        self.i2c_address: int = i2c_address
        self.channel: int = channel
        self.ads1115_converter: Optional[ADS1115Converter] = None
        self.min_value: float = min_value
        self.max_value: float = max_value
        self.logger: logging.Logger = logging.getLogger('app_logger')
        super().__init__(*args, **kwargs)
        self.configure_sensor()

    def configure_sensor(self) -> None:
        """
        Initializes the ADS1115 ADC converter with the specified I2C address and channel for soil moisture sensor.
        """
        try:
            self.ads1115_converter = ADS1115Converter(self.i2c_address, self.channel)
            self.logger.info(f"Soil moisture sensor name={self.name} on ADS1115 I2C address {self.i2c_address}, channel {self.channel} configured.")
        except Exception as ex:
            self.logger.error(f"Failed to configure soil moisture sensor name={self.name} on ADS1115 I2C address {self.i2c_address}, channel {self.channel}: {ex}")

    def read_sensor(self) -> float:
        """
        Attempts to read the soil moisture level from the ADS1115 ADC converter. Validates the moisture reading
        to ensure it's within specified range and not an anomaly if anomaly detection is enabled.

        Returns:
            float: The soil moisture reading or NaN if the reading fails validation checks or cannot be read.
        """
        try:
            moisture_value = self.ads1115_converter.read()
            if moisture_value is not None:
                self.logger.info(f"Soil moisture sensor name={self.name} read from ADS1115 I2C address {self.i2c_address}, channel {self.channel}: {moisture_value} V")

                if not self.is_number(moisture_value):
                    self.logger.warning(f"Sensor name={self.name}  read value is not a number: {moisture_value}. Returning NaN.")
                    return float('nan')

                if not self.is_in_range(moisture_value, self.min_value, self.max_value):
                    self.logger.warning(
                        f"Sensor name={self.name} read value={moisture_value} V is outside the acceptable range [{self.min_value}, {self.max_value} V]. Returning NaN.")
                    return float('nan')

                self.logger.info(f"Sensor name={self.name} voltage value before conversion: {moisture_value}")
                moisture_percentage_value = self.convert_to_percentage(moisture_value)

                if self.anomaly_detection:
                    if self.detect_anomaly(new_value=moisture_percentage_value, acceptable_deviation=5):
                        self.logger.warning(f"Sensor name={self.name} - Anomaly detected for soil moisture_value={moisture_value} V, moisture_percentage_value={moisture_percentage_value}, returning NaN.")
                        return float('nan')
                    else:
                        self.logger.info(f"Sensor name={self.name} - Anomaly not found.")

                return moisture_percentage_value
            else:
                self.logger.warning(f"Failed to read soil moisture sensor name={self.name} from ADS1115 I2C address {self.i2c_address}, channel {self.channel}.")
                return float('nan')
        except Exception as ex:
            self.logger.error(f"Error reading soil moisture sensor name={self.name} on ADS1115 I2C address {self.i2c_address}, channel {self.channel}: {ex}")
            return float('nan')

    def convert_to_percentage(self, value: float, min_value: float = 0.8, max_value: float = 3.3) -> float:
        """
        Converts an analog value to a percentage based on the specified minimum and maximum values,
        with an inverse relationship between the analog value and the percentage.

        Args:
            value (float): The raw analog value to convert.
            min_value (float): The analog value corresponding to 100% moisture.
            max_value (float): The analog value corresponding to 0% moisture.

        Returns:
            float: The converted value as a percentage from 0 to 1, with higher percentages
                   representing higher moisture levels (and thus lower voltage levels).
        """
        try:
            value = max(min(value, max_value), min_value)
            percentage = 1 - (value - min_value) / (max_value - min_value)
            return percentage
        except Exception as ex:
            self.logger.error(f"Failed to convert to a percentage: {ex}")
