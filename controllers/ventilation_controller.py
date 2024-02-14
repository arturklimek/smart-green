from typing import List, Dict
from actuators.actuator import BaseActuator
from controllers.controller import BaseController

class VentilationController(BaseController):
    def __init__(self, sensors: List[Dict], actuator: BaseActuator, check_interval: float = 60.0, cooldown_period: int = 1800):
        """
        Initializes the VentilationController with predefined values suitable for controlling ventilation based on temperature or humidity and a cooldown period.

        Args:
            sensors (List[Dict]): List of sensor configuration dictionaries.
            actuator (BaseActuator): The actuator to control the ventilation system.
            check_interval (float): Interval in seconds between checks. Defaults to 60.0 seconds.
            cooldown_period (int): Cooldown period in seconds after the actuator has been deactivated before it can be activated again. Defaults to 1800 seconds (30 minutes).
        """
        super().__init__(
            check_interval=check_interval,
            sensors=sensors,
            actuator=actuator,
            cooldown_period=cooldown_period
        )