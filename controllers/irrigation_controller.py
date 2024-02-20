from typing import List, Dict
from actuators.actuator import BaseActuator
from controllers.controller import BaseController

class IrrigationController(BaseController):
    def __init__(self, sensors: List[Dict], actuator: BaseActuator, check_interval: float = 60.0, activation_time: int = 5, cooldown_period: int = 600, start_hour: int = None, end_hour: int = None):
        """
        A specialized controller for managing irrigation based on soil moisture levels.

        Args:
            sensors (List[Dict]): A list of sensor configurations.
            actuator (BaseActuator): The actuator to control the irrigation system.
            check_interval (float): How often (in seconds) to check the sensor readings.
            activation_time (int): How long (in seconds) the irrigation should run once activated.
            cooldown_period (int): Minimum time (in seconds) between irrigation activations.
            start_hour (int, optional): The hour of the day when irrigation can start (24-hour format). Defaults to None.
            end_hour (int, optional): The hour of the day when irrigation must stop (24-hour format). Defaults to None.
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

    @staticmethod
    def calculate_pump_activation_time(pump_flow_rate: float, water_volume: float, max_lift_height: float = None, current_lift_height: float = None) -> int:
        """
        Calculates the time (in seconds) the pump should be activated to irrigate the given volume of water, optionally considering the effect of lift height on pump efficiency.

        Args:
            pump_flow_rate (float): The pump's flow rate in liters per hour.
            water_volume (float): The volume of water to be irrigated in liters.
            max_lift_height (float, optional): The maximum lift height of the pump in meters. Defaults to None.
            current_lift_height (float, optional): The current lift height in meters. Defaults to None.

        Returns:
            int: The activation time in seconds.
        """
        if max_lift_height is not None and current_lift_height is not None and max_lift_height > 0:
            efficiency_factor = (max_lift_height - current_lift_height) / max_lift_height
            adjusted_flow_rate = pump_flow_rate * efficiency_factor
        else:
            adjusted_flow_rate = pump_flow_rate
        activation_time_hours = water_volume / adjusted_flow_rate
        activation_time_seconds = int(activation_time_hours * 3600)
        return activation_time_seconds

    def set_activation_time(self, new_activation_time: int) -> None:
        self.activation_time = new_activation_time
