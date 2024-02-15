import time
from typing import Optional
from sensors.BH1750FVI import BH1750Sensor
from sensors.sensor import BaseSensor
import logging

class LightSensor(BaseSensor):
    """
    A sensor class that extends BaseSensor for reading light intensity from a BH1750 sensor. It includes functionality
    for anomaly detection based on specified minimum and maximum light intensity values.

    Attributes:
        i2c_address (int): I2C address where the BH1750 sensor is connected.
        anomaly_detection (bool): Flag indicating whether anomaly detection is enabled.
        min_value (float): Minimum acceptable light intensity value for anomaly detection.
        max_value (float): Maximum acceptable light intensity value for anomaly detection.
        logger (logging.Logger): Logger for recording operational messages.

    Methods:
        configure_sensor: Initializes the BH1750 sensor.
        read_sensor: Attempts to read the light intensity from the sensor, with anomaly detection and range validation.
    """
    def __init__(self, i2c_address: int = 0x23, min_value: float = 0.0, max_value: float = 65535.0, *args, **kwargs) -> None:
        self.i2c_address: int = i2c_address
        self.bh1750_sensor: Optional[BH1750Sensor] = None
        self.min_value: float = min_value
        self.max_value: float = max_value
        self.logger: logging.Logger = logging.getLogger('app_logger')
        super().__init__(*args, **kwargs)
        self.configure_sensor()

    def configure_sensor(self) -> None:
        """
        Initializes the BH1750 sensor with the specified I2C address.
        """
        try:
            self.bh1750_sensor = BH1750Sensor(self.i2c_address)
            self.logger.info(f"Light sensor name={self.name} on I2C address {self.i2c_address} configured.")
        except Exception as ex:
            self.logger.error(f"Failed to configure light sensor name={self.name} on I2C address {self.i2c_address}: {ex}")

    def read_sensor(self) -> float:
        """
        Attempts to read the light intensity from the BH1750 sensor. Validates the light intensity reading
        to ensure it's within specified range and not an anomaly if anomaly detection is enabled.

        Returns:
            float: The light intensity reading in lux or NaN if the reading fails validation checks or cannot be read.
        """
        try:
            light_intensity = self.bh1750_sensor.read_sensor_value()
            if light_intensity is not None:
                self.logger.info(f"Sensor name={self.name} light intensity read from I2C address {self.i2c_address}: {light_intensity} lux")

                if not self.is_number(light_intensity):
                    self.logger.warning(f"Sensor name={self.name} read value is not a number: {light_intensity}. Returning NaN.")
                    return float('nan')

                if not self.is_in_range(light_intensity, self.min_value, self.max_value):
                    self.logger.warning(
                        f"Sensor name={self.name} read value={light_intensity} lux is outside the acceptable range [{self.min_value}, {self.max_value} lux]. Returning NaN.")
                    return float('nan')

                if self.anomaly_detection:
                    if self.detect_anomaly(new_value=light_intensity, acceptable_deviation=1000):
                        self.logger.warning(
                            f"Sensor name={self.name} - Anomaly detected for light intensity={light_intensity} lux, returning NaN.")
                        return float('nan')
                    else:
                        self.logger.info(f"Sensor name={self.name} - Anomaly not found.")

                return light_intensity
            else:
                self.logger.warning(f"Failed to read light intensity sensor name={self.name} from I2C address {self.i2c_address}.")
                return float('nan')
        except Exception as ex:
            self.logger.error(f"Error reading light sensor name={self.name} on I2C address {self.i2c_address}: {ex}")
            return float('nan')
