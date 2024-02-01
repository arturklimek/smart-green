from typing import Optional

import RPi.GPIO as GPIO
import logging
import threading
import datetime
import time

class BaseActuator:
    """
    A class representing a basic actuator.

    Attributes:
        relay_pin (int): The GPIO pin number associated with the actuator.
        state (bool): The current state of the actuator (True for active, False for inactive).
        last_state_change (datetime.datetime): Timestamp of the last state change.
        previous_state (bool): The state of the actuator prior to the current state.
        active_thread (threading.Thread): The thread used for changing the actuator's state over time.
        _stop_thread (bool): Flag to signal the active thread to stop its operation.
    """

    def __init__(self, relay_pin: int, initial_state: Optional[bool] = None):
        """
        Initializes the actuator with the specified GPIO pin and an optional initial state.

        Args:
            relay_pin (int): The GPIO pin to control the actuator.
            initial_state (Optional[bool]): The initial state to set the actuator to. If None, the state is not set.
        """
        self.relay_pin = relay_pin
        self.state = False
        self.last_state_change = None
        self.previous_state = None
        self.active_thread = None
        self._stop_thread = False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relay_pin, GPIO.OUT)

        if initial_state is not None:
            try:
                self._update_state(initial_state, initial=True)
            except Exception as e:
                logging.error(f"Error setting initial state of actuator on pin {self.relay_pin}: {e}")

    def _update_state(self, new_state: bool, initial: bool = False):
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
            self.last_state_change = datetime.datetime.now()
            logging.info(f"State of actuator {self.relay_pin} changed to {self.state}.")
        except Exception as e:
            logging.error(f"Error updating state of actuator on pin {self.relay_pin}: {e}")

    def activate(self):
        """
        Activates the actuator by setting the GPIO pin high.

        Raises:
            Exception: If there is an error in setting the GPIO pin.
        """
        try:
            GPIO.output(self.relay_pin, GPIO.HIGH)
            self._update_state(True)
            logging.info(f"Actuator {self.relay_pin} has been activated.")
        except Exception as e:
            logging.error(f"Failed to activate actuator on pin {self.relay_pin}: {e}")
            raise

    def deactivate(self):
        """
        Deactivates the actuator by setting the GPIO pin low.

        Raises:
            Exception: If there is an error in setting the GPIO pin.
        """
        try:
            GPIO.output(self.relay_pin, GPIO.LOW)
            self._update_state(False)
            logging.info(f"Actuator {self.relay_pin} has been deactivated.")
        except Exception as e:
            logging.error(f"Failed to deactivate actuator on pin {self.relay_pin}: {e}")
            raise

    def toggle(self):
        """
        Toggles the state of the actuator between active and inactive.
        """
        try:
            if self.state:
                self.deactivate()
            else:
                self.activate()
            logging.info(f"Actuator {self.relay_pin} state toggled.")
        except Exception as e:
            logging.error(f"Error toggling actuator on pin {self.relay_pin}: {e}")
            raise

    def change_state_for(self, new_state: Optional[bool] = None, duration: Optional[int] = None):
        """
        Changes the state of the actuator for a specified duration using a separate thread.

        Args:
            new_state (Optional[bool]): The state to change to. If None, toggles the current state.
            duration (Optional[int]): The duration in seconds for which the state should be maintained.

        Returns:
            None
        """
        if self.is_thread_active():
            logging.warning(f"Another operation is already in progress on actuator {self.relay_pin}.")
            return
        resolved_new_state = not self.state if new_state is None else new_state
        try:
            self.active_thread = threading.Thread(target=self._change_state_with_timer, args=(resolved_new_state, duration))
            self.active_thread.start()
            logging.info(f"Started a thread to change state of actuator {self.relay_pin} for {duration} seconds.")
        except Exception as e:
            logging.error(f"Failed to start thread for changing state of actuator on pin {self.relay_pin}: {e}")

    def _change_state_with_timer(self, new_state: bool, duration: int):
        """
        A private method to change the state of the actuator for a specified duration.

        Args:
            new_state (bool): The state to change to.
            duration (int): The duration in seconds for which the state should be maintained.
        """
        try:
            initial_state = self.state
            self._update_state(new_state)
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
            while datetime.datetime.now() < end_time:
                if self._stop_thread:
                    logging.info(f"Thread for actuator {self.relay_pin} has been stopped.")
                    return
                time.sleep(0.1)
            self._update_state(not initial_state)
            logging.info(f"State of actuator {self.relay_pin} reverted after {duration} seconds.")
        except Exception as e:
            logging.error(f"Error in maintaining state for actuator on pin {self.relay_pin}: {e}")
            raise

    def schedule_state_change(self, new_state: Optional[bool] = None, start_time: Optional[datetime.time] = None, end_time: Optional[datetime.time] = None):
        """
        Schedules a state change for the actuator within a specified time interval.

        Args:
            new_state (Optional[bool]): The state to change to. If None, toggles the current state.
            start_time (Optional[datetime.time]): The start time for the state change.
            end_time (Optional[datetime.time]): The end time for the state change.

        Returns:
            None
        """
        if self.is_thread_active():
            logging.warning(f"Another operation on actuator {self.relay_pin} is already in progress.")
            return
        resolved_new_state = not self.state if new_state is None else new_state
        try:
            self.active_thread = threading.Thread(target=self._scheduled_state_change, args=(resolved_new_state, start_time, end_time))
            self.active_thread.start()
            logging.info(f"Scheduled state change for actuator {self.relay_pin}.")
        except Exception as e:
            logging.error(f"Failed to schedule state change for actuator on pin {self.relay_pin}: {e}")

    def _scheduled_state_change(self, new_state: bool, start_time: Optional[datetime.time], end_time: Optional[datetime.time]):
        """
        A private method that handles the scheduled state change.

        Args:
            new_state (bool): The state to change to.
            start_time (Optional[datetime.time]): The start time for the state change.
            end_time (Optional[datetime.time]): The end time for the state change.
        """
        try:
            now = datetime.datetime.now()
            start = datetime.datetime.combine(now.date(), start_time) if start_time else now
            end = datetime.datetime.combine(now.date(), end_time) if end_time else now + datetime.timedelta(days=1)

            while now < start:
                if self._stop_thread:
                    logging.info(f"Scheduled state change for actuator {self.relay_pin} stopped.")
                    return
                time.sleep(0.1)
                now = datetime.datetime.now()

            self._update_state(new_state)

            while now < end:
                if self._stop_thread:
                    logging.info(f"Scheduled state change for actuator {self.relay_pin} stopped.")
                    return
                time.sleep(0.1)
                now = datetime.datetime.now()

            self._update_state(not new_state)
            logging.info(f"Scheduled state change for actuator {self.relay_pin} completed.")
        except Exception as e:
            logging.error(f"Error during scheduled state change for actuator on pin {self.relay_pin}: {e}")

    def activate_for(self, duration: int):
        """
        Activates the actuator for a specified duration.

        Args:
            duration (int): The duration in seconds for which the actuator should be activated.

        Returns:
            None
        """
        self.change_state_for(True, duration)

    def deactivate_for(self, duration: int):
        """
        Deactivates the actuator for a specified duration.

        Args:
            duration (int): The duration in seconds for which the actuator should be deactivated.

        Returns:
            None
        """
        self.change_state_for(False, duration)

    def schedule_activation(self, start_time: datetime.time, end_time: datetime.time):
        """
        Schedules the activation of the actuator between specified start and end times.

        Args:
            start_time (datetime.time): The time at which the actuator should be activated.
            end_time (datetime.time): The time at which the actuator should be deactivated.

        Returns:
            None
        """
        self.schedule_state_change(True, start_time, end_time)

    def schedule_deactivation(self, start_time: datetime.time, end_time: datetime.time):
        """
        Schedules the deactivation of the actuator between specified start and end times.

        Args:
            start_time (datetime.time): The time at which the actuator should be deactivated.
            end_time (datetime.time): The time at which the actuator should be reactivated.

        Returns:
            None
        """
        self.schedule_state_change(False, start_time, end_time)

    def cancel_activation(self) -> None:
        """
        Cancels the current activation of the actuator, if any, by stopping the active thread.

        Raises:
            Exception: If there is an error in stopping the thread.
        """
        self._stop_thread = True
        try:
            if self.active_thread and self.active_thread.is_alive():
                self.active_thread.join()
                self._stop_thread = False
                logging.info(f"Activation of actuator {self.relay_pin} has been cancelled.")
        except Exception as e:
            logging.error(f"Failed to cancel activation of actuator on pin {self.relay_pin}: {e}")
            raise

    def is_thread_active(self) -> bool:
        """
        Checks if there is an active thread controlling the actuator.

        Returns:
            bool: True if there is an active thread, False otherwise.
        """
        return self.active_thread is not None and self.active_thread.is_alive()

    def get_state(self) -> bool:
        """
        Retrieves the current state of the actuator.

        Returns:
            bool: The current state of the actuator.
        """
        return self.state

    def get_last_state_change(self) -> Optional[Any]:
        """
        Retrieves the timestamp of the last state change of the actuator.

        Returns:
            Optional[datetime.datetime]: The timestamp of the last state change, or None if not set.
        """
        return self.last_state_change

    def get_previous_state(self) -> Optional[bool]:
        """
        Retrieves the previous state of the actuator.

        Returns:
            Optional[bool]: The previous state of the actuator, or None if not set.
        """
        return self.previous_state

    def __del__(self) -> None:
        """
        Destructor for the BaseActuator class. Cancels any ongoing activation and cleans up the GPIO pin.
        """
        try:
            self.cancel_activation()
            GPIO.cleanup(self.relay_pin)
            logging.info(f"Actuator {self.relay_pin} has been cleaned up.")
        except Exception as e:
            logging.error(f"Error during cleanup of actuator on pin {self.relay_pin}: {e}")
            raise
