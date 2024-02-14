from typing import List, Dict
from actuators.actuator import BaseActuator
from controllers.controller import BaseController

class LightingController(BaseController):
    def __init__(self, sensors: List[Dict], actuator: BaseActuator, check_interval: float = 60.0, activation_time: int = 5, cooldown_period: int = 600, start_hour: int = 8, end_hour: int = 20):
        """
        Initializes the LightingController with predefined values suitable for controlling lighting based on light intensity and operating hours.

        Args:
            sensors (List[Dict]): List of sensor configuration dictionaries.
            actuator (BaseActuator): The actuator to control the lights.
            check_interval (float): Interval in seconds between checks. Defaults to 60.0 seconds.
            start_hour (int): The hour to start lighting (24-hour format). Defaults to 8 AM.
            end_hour (int): The hour to end lighting (24-hour format). Defaults to 8 PM.
        """
        super().__init__(
            check_interval=check_interval,
            sensors=sensors,
            actuator=actuator,
            activation_time=activation_time,
            cooldown_period=cooldown_period,
            start_hour=start_hour,
            end_hour=end_hour
        )
