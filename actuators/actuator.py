import logging
import threading
import time
from typing import Optional, Any
import RPi.GPIO as GPIO
import datetime
from databases.influx import InfluxDBManager

class BaseActuator:
    """
    A class representing a basic actuator.

    Attributes:
        gpio_pin (int): The GPIO pin number associated with the actuator.
        name (str): Stores the name actuator.
        state (bool): The current state of the actuator (True for active, False for inactive).
        last_state_change_time (datetime.datetime): Timestamp of the last state change.
        previous_state (bool): The state of the actuator prior to the current state.
    """

    def __init__(self, gpio_pin: int, name: str, initial_state: Optional[bool] = None, send_state_to_db: bool = False) -> None:
        """
        Initializes the actuator with the specified GPIO pin and an optional initial state.

        Args:
            gpio_pin (int): The GPIO pin to control the actuator.
            initial_state (Optional[bool]): The initial state to set the actuator to. If None, the state is not set.
        """
        self.logger = logging.getLogger('app_logger')
        self.gpio_pin = gpio_pin
        self.name = name
        self.state = False
        self.last_state_change_time = None
        self.previous_state = None
        self.send_state_to_db = send_state_to_db
        self.state_send_thread = None
        self.state_send_thread_running = False
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup(self.gpio_pin)
        GPIO.setup(self.gpio_pin, GPIO.OUT)

        if initial_state is not None:
            try:
                self._update_state(initial_state, initial=True)
                if initial_state:
                    self.activate()
                else:
                    self.deactivate()
            except Exception as ex:
                self.logger.error(f"Error setting initial state of actuator name={self.name} on pin {self.gpio_pin}: {ex}")

        if self.send_state_to_db:
            self.start_sending_state()

    def _update_state(self, new_state: bool, initial: bool = False) -> None:
        """
        Updates the state of the actuator.

        Args:
            new_state (bool): The new state to set for the actuator.
            initial (bool): Flag indicating if this is the initial state set upon creation.
        """
        try:
            if not initial:
                self.previous_state = self.state
            self.state = new_state
            self.last_state_change_time = datetime.datetime.now()
            self.logger.info(f"State of actuator name={self.name} {self.gpio_pin} changed to {self.state}.")
        except Exception as ex:
            self.logger.error(f"Error updating state of actuator name={self.name} on pin {self.gpio_pin}: {ex}")

    def _send_state_to_db(self, frequency: int = 60):
        while self.state_send_thread_running:
            influx_manager = InfluxDBManager()
            influx_manager.write_data(
                measurement="actuator_state",
                fields={"state": int(self.state)},
                tags={"actuator_name": self.name, "gpio_pin": str(self.gpio_pin)}
            )
            time.sleep(frequency)

    def start_sending_state(self):
        if not self.state_send_thread_running:
            self.state_send_thread_running = True
            self.state_send_thread = threading.Thread(target=self._send_state_to_db, daemon=True)
            self.state_send_thread.start()

    def stop_sending_state(self):
        if self.state_send_thread_running:
            self.state_send_thread_running = False
            self.state_send_thread.join()

    def is_sending_state(self) -> bool:
        return self.state_send_thread_running

    def activate(self) -> None:
        """
        Activates the actuator by setting the GPIO pin low.

        Raises:
            Exception: If there is an error in setting the GPIO pin.
        """
        influx_manager = InfluxDBManager()
        try:
            GPIO.output(self.gpio_pin, GPIO.LOW)
            self._update_state(True)
            self.logger.info(f"Actuator name={self.name} on pin: {self.gpio_pin} has been activated - set {GPIO.LOW}.")
            influx_manager.write_data(
                measurement="actuator_events",
                fields={"state": 1},
                tags={"actuator_name": self.name, "gpio_pin": str(self.gpio_pin)}
            )
        except Exception as ex:
            self.logger.error(f"Failed to activate actuator name={self.name} on pin {self.gpio_pin}: {ex}")
            raise

    def deactivate(self) -> None:
        """
        Deactivates the actuator by setting the GPIO pin high.

        Raises:
            Exception: If there is an error in setting the GPIO pin.
        """
        influx_manager = InfluxDBManager()
        try:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            self._update_state(False)
            self.logger.info(f"Actuator name={self.name} on pin: {self.gpio_pin} has been deactivated - set {GPIO.HIGH}.")
            influx_manager.write_data(
                measurement="actuator_events",
                fields={"state": 0},
                tags={"actuator_name": self.name, "gpio_pin": str(self.gpio_pin)}
            )
        except Exception as ex:
            self.logger.error(f"Failed to deactivate actuator name={self.name} on pin {self.gpio_pin}: {ex}")
            raise

    def toggle(self) -> None:
        """
        Toggles the state of the actuator between active and inactive.
        """
        try:
            if self.state:
                self.deactivate()
            else:
                self.activate()
            self.logger.info(f"Actuator {self.gpio_pin} state toggled.")
        except Exception as ex:
            self.logger.error(f"Error toggling actuator name={self.name} on pin {self.gpio_pin}: {ex}")
            raise

    def get_state(self) -> bool:
        """
        Retrieves the current state of the actuator.

        Returns:
            bool: The current state of the actuator.
        """
        return self.state

    def get_last_state_change_time(self) -> Optional[Any]:
        """
        Retrieves the timestamp of the last state change of the actuator.

        Returns:
            Optional[datetime.datetime]: The timestamp of the last state change, or None if not set.
        """
        return self.last_state_change_time

    def get_previous_state(self) -> Optional[bool]:
        """
        Retrieves the previous state of the actuator.

        Returns:
            Optional[bool]: The previous state of the actuator, or None if not set.
        """
        return self.previous_state

    def get_gpio_pin(self) -> int:
        """
        Retrieves the GPIO pin number associated with the actuator.

        Returns:
            int: The GPIO pin number.
        """
        return self.gpio_pin

    def get_name(self) -> str:
        """
        Retrieves the name of the associated actuator.

        Returns:
            str: The actuator name
        """
        return self.name

    def __del__(self) -> None:
        """
        Destructor for the BaseActuator class. Cancels any ongoing activation and cleans up the GPIO pin.
        """
        try:
            self.stop_sending_state()
            GPIO.cleanup(self.gpio_pin) # TODO: clearing will change the setting to the default - such as IN mode, which may be unwanted
            self.logger.info(f"Actuator name={self.name} on pin: {self.gpio_pin} has been cleaned up.")
        except Exception as ex:
            self.logger.error(f"Error during cleanup of actuator name={self.name} on pin {self.gpio_pin}: {ex}")
            raise
