import time
from typing import Optional
from sensors.DHT11 import DHT11Sensor
from sensors.sensor import BaseSensor
import logging

class HumiditySensor(BaseSensor):
    """
    A sensor class that extends BaseSensor for reading humidity from a DHT11 sensor. It includes functionality
    for anomaly detection based on specified minimum and maximum humidity values.

    Attributes:
        pin (int): GPIO pin number where the DHT11 sensor is connected.
        min_value (float): Minimum acceptable humidity value for anomaly detection.
        max_value (float): Maximum acceptable humidity value for anomaly detection.
        logger (logging.Logger): Logger for recording operational messages.

    Methods:
        configure_sensor: Initializes the DHT11 sensor.
        read_sensor: Attempts to read the humidity from the sensor, with anomaly detection and range validation.
    """
    def __init__(self, pin: int, min_value: float = 20.0, max_value: float = 90.0, *args, **kwargs) -> None:
        self.pin: int = pin
        self.dht_sensor: Optional[DHT11Sensor] = None
        self.min_value: float = min_value
        self.max_value: float = max_value
        self.logger: logging.Logger = logging.getLogger('app_logger')
        super().__init__(*args, **kwargs)

    def configure_sensor(self) -> None:
        """
        Initializes the DHT11 sensor with the specified GPIO pin.
        """
        try:
            self.dht_sensor = DHT11Sensor(self.pin)
            self.logger.info(f"Humidity sensor on pin {self.pin} configured.")
        except Exception as ex:
            self.logger.error(f"Failed to configure humidity sensor on pin {self.pin}: {ex}")

    def read_sensor(self) -> float:
        """
        Attempts to read the humidity from the DHT11 sensor up to three times. Validates the humidity reading
        to ensure it's within specified range and not an anomaly if anomaly detection is enabled.

        Returns:
            float: The humidity reading or NaN if the reading fails validation checks or cannot be read.
        """
        try:
            for _ in range(3):
                sensor_data = self.dht_sensor.read_sensor_value()
                if sensor_data is not None:
                    self.logger.info(f"Humidity read from pin {self.pin}: {sensor_data['humidity']}%")
                    humidity = self.to_float(sensor_data['humidity'])

                    if not self.is_number(humidity):
                        self.logger.warning(f"Read value is not a number: {humidity}. Returning NaN.")
                        return float('nan')

                    if not self.is_in_range(humidity, self.min_value, self.max_value):
                        self.logger.warning(
                            f"Read value={humidity} is outside the acceptable range [{self.min_value}, {self.max_value}]. Returning NaN.")
                        return float('nan')

                    if self.anomaly_detection:
                        if self.detect_anomaly(new_value=humidity, acceptable_deviation=15):
                            self.logger.warning(
                                f"Anomaly detector return True for humidity={humidity}, return NaN.")
                            return float('nan')
                        else:
                            self.logger.info(f"Anomaly not found.")
                    else:
                        self.logger.info(f"Anomaly detection is disabled")

                    self.logger.info(
                        f"Humidity read from pin {self.pin}: {humidity}%. Anomaly detection: {'enabled' if self.anomaly_detection else 'disabled'}")
                    return humidity
                else:
                    self.logger.warning(f"Failed to read humidity from pin {self.pin}.")
                    time.sleep(0.5)
            self.logger.warning(f"Cannot read humidity from pin {self.pin} - return NaN.")
            return float('nan')
        except Exception as ex:
            self.logger.error(f"Error reading humidity sensor on pin {self.pin}: {ex}")
            return float('nan')
