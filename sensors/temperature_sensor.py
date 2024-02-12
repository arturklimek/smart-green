import time
from typing import Optional
from sensors.DHT11 import DHT11
from sensors.sensor import BaseSensor
import logging

class TemperatureSensor(BaseSensor):
    """
    A sensor class that extends BaseSensor for reading temperatures from a DHT11 sensor. It includes functionality
    for anomaly detection based on specified minimum and maximum temperature values.

    Attributes:
        pin (int): GPIO pin number where the DHT11 sensor is connected.
        anomaly_detection (bool): Flag indicating whether anomaly detection is enabled.
        min_value (float): Minimum acceptable temperature value for anomaly detection.
        max_value (float): Maximum acceptable temperature value for anomaly detection.
        logger (logging.Logger): Logger for recording operational messages.

    Methods:
        configure_sensor: Initializes the DHT11 sensor.
        read_sensor: Attempts to read the temperature from the sensor, with anomaly detection and range validation.
    """
    def __init__(self, pin: int, anomaly_detection: bool = True, min_value: float = 0.0, max_value: float = 50.0, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dht_sensor: Optional[DHT11] = None
        self.pin: int = pin
        self.anomaly_detection: bool = anomaly_detection
        self.min_value: float = min_value
        self.max_value: float = max_value
        self.logger: logging.Logger = logging.getLogger('app_logger')
        self.configure_sensor()

    def configure_sensor(self) -> None:
        """
        Initializes the DHT11 sensor with the specified GPIO pin.
        """
        try:
            self.dht_sensor = DHT11(self.pin)
            self.logger.info(f"Temperature sensor on pin {self.pin} configured.")
        except Exception as e:
            self.logger.error(f"Failed to configure temperature sensor on pin {self.pin}: {e}")

    def read_sensor(self) -> float:
        """
        Attempts to read the temperature from the DHT11 sensor up to three times. Validates the temperature reading
        to ensure it's within specified range and not an anomaly if anomaly detection is enabled.

        Returns:
            float: The temperature reading or NaN if the reading fails validation checks or cannot be read.
        """
        try:
            for _ in range(3):
                sensor_data = self.dht_sensor.read()
                if sensor_data is not None:
                    self.logger.info(f"Temperature read from pin {self.pin}: {sensor_data['temperature']}°C")
                    temperature = self.to_float(sensor_data['temperature'])

                    if not self.is_number(temperature):
                        self.logger.warning(f"Read value is not a number: {temperature}. Returning NaN.")
                        return float('nan')

                    if not self.is_in_range(temperature, self.min_value, self.max_value):
                        self.logger.warning(
                            f"Read value={temperature} is outside the acceptable range [{self.min_value}, {self.max_value}]. Returning NaN.")
                        return float('nan')

                    if self.anomaly_detection:
                        if self.detect_anomaly(temperature):
                            self.logger.warning(
                                f"Anomaly was detected for value temperature={temperature}, return NaN.")
                            return float('nan')
                        else:
                            self.logger.info(f"Anomaly not found.")
                    else:
                        self.logger.info(f"Anomaly detection is disabled")

                    self.logger.info(
                        f"Temperature read from pin {self.pin}: {temperature}°C. Anomaly detection: {'enabled' if self.anomaly_detection else 'disabled'}")
                    return temperature
                else:
                    self.logger.warning(f"Failed to read temperature from pin {self.pin}.")
                    time.sleep(0.5)
            self.logger.warning(f"Can not read temperature from pin {self.pin} - return NaN.")
            return float('nan')
        except Exception as e:
            self.logger.error(f"Error reading temperature sensor on pin {self.pin}: {e}")
            return float('nan')
