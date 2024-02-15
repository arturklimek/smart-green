import logging
import os
import time
from typing import List, Optional, Dict, Any
from actuators.actuator import BaseActuator
from app_config import LOG_DIR_PATH, AppConfig, APP_CONFIG_PATH
from arduino.ArduinoManager import ArduinoManager
from controllers.controller import BaseController
from controllers.irrigation_controller import IrrigationController
from controllers.lighting_controller import LightingController
from controllers.ventilation_controller import VentilationController
from logger import LoggerManager
from sensors.humidity_sensor import HumiditySensor
from sensors.light_sensor import LightSensor
from sensors.sensor import BaseSensor
from sensors.soil_moisture_sensor import SoilMoistureSensor
from sensors.temperature_sensor import TemperatureSensor
import uuid

class App:
    """
    A main application class responsible for initializing and managing the entire application lifecycle.

    This class initializes the application's logging system, loads the configuration, manages sensors,
    actuators, and controllers, and handles the starting and stopping of the application.

    Attributes:
        logger (logging.Logger): Application-wide logger.
        app_config (AppConfig): Configuration manager for the application.
        sensors (Dict[BaseSensor]): Dict of sensor objects used in the application.
        actuators (Dict[BaseActuator]): Dict of actuator objects used in the application.
        controllers (Dict[BaseController]): Dict of controller objects that manage the application logic.
        running (bool): Flag indicating if the application is currently running.
    """
    def __init__(self) -> None:
        """
        Initializes the application, sets up the directory structure, initializes logging,
        loads components based on the application configuration, and logs the initialization completion.
        """
        self.setup_dir_structure([LOG_DIR_PATH])
        LoggerManager.setup_logger('app_logger', os.path.join(LOG_DIR_PATH, 'app.log'), level_console=logging.INFO, level_file=logging.DEBUG)
        self.logger: logging.Logger = logging.getLogger('app_logger')
        self.app_config: AppConfig = AppConfig(APP_CONFIG_PATH)
        self.sensors: Dict[str, BaseSensor] = {}
        self.actuators: Dict[str, BaseActuator] = {}
        self.controllers: Dict[str, BaseController] = {}
        self.load_components()
        self.logger.info('Application initialized')
        self.running: bool = False

    def reload_config(self) -> None:
        """
        Reloads the application configuration from the configuration file and logs the outcome.
        """
        try:
            self.app_config.load_config()
            self.logger.info("Configuration reloaded successfully.")
        except Exception as ex:
            self.logger.error(f"Failed to reload configuration: {ex}")

    def run_app(self) -> None:
        """
        Starts the application by beginning sensor readings, starting controllers,
        and entering the main application loop until a stop signal is received.
        """
        self.running = True
        self.start_sensors_reading()
        self.start_controllers()
        self.run_arduinoLCD()
        try:
            while self.running:
                time.sleep(0.5)
        finally:
            self.stop_sensors_reading()
            self.stop_controllers()

    def stop_app(self) -> None:
        """
        Stops the application by signaling the main loop to terminate and waits for a short period
        to ensure all components are properly shutdown.
        """
        self.running = False
        time.sleep(4)

    @staticmethod
    def setup_dir_structure(dir_list: List[str]) -> None:
        """
        Sets up the required directory structure for the application.

        Args:
            dir_list (List[str]): A list of directory paths that should be created.
        """
        for dir_path in dir_list:
            try:
                App.create_dir(dir_path)
            except Exception as ex:
                logging.error(f'Error creating directory {dir_path}: {ex}')

    @staticmethod
    def create_dir(dir_path: str) -> None:
        """
        Creates a directory if it does not already exist.

        Args:
            dir_path (str): Path of the directory to be created.
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logging.info(f"Directory created: {dir_path}")

    def start_controllers(self) -> None:
        """
        Initiates the start sequence for all configured controllers within the application.
        """
        self.logger.debug(f"start_controllers - controllers len: {len(self.controllers)}.")
        for name, controller in self.controllers.items():
            self.logger.debug(f"Try start controller by name: {name}.")
            try:
                if controller:
                    controller.start()
                    self.logger.info(f"{controller.__class__.__name__} started - name: {name}.")
            except Exception as ex:
                self.logger.error(f"Failed to start {controller.__class__.__name__} - name: {name}: {ex}")

    def stop_controllers(self) -> None:
        """
        Initiates the stop sequence for all running controllers within the application.
        """
        for name, controller in self.controllers.items():
            try:
                if controller:
                    controller.stop()
                    self.logger.info(f"{controller.__class__.__name__} stopped.")
            except Exception as ex:
                self.logger.error(f"Failed to stop {controller.__class__.__name__}: {ex}")

    def start_sensors_reading(self) -> None:
        """
        Starts the data reading process for all configured sensors.
        """
        for name, sensor in self.sensors.items():
            try:
                if sensor:
                    sensor.start_reading()
                    self.logger.info(f"{sensor.__class__.__name__} reading started.")
            except Exception as ex:
                self.logger.error(f"Failed to start reading {sensor.__class__.__name__}: {ex}")

    def stop_sensors_reading(self) -> None:
        """
        Stops the data reading process for all sensors that are currently reading data.
        """
        for name, sensor in self.sensors.items():
            try:
                if sensor:
                    sensor.stop_reading()
                    self.logger.info(f"{sensor.__class__.__name__} stopped reading.")
            except Exception as ex:
                self.logger.error(f"Failed to stop reading {sensor.__class__.__name__}: {ex}")

    def load_components(self) -> None:
        """
        Loads sensors, actuators, and controllers based on the application configuration.
        Adds successfully created components to their respective lists within the application.
        """
        config: Dict[str, Any] = self.app_config.get_config()
        try:
            for sensor_config in config.get('sensors', []):
                name = sensor_config['name']
                sensor = self.create_sensor(sensor_config)
                if sensor:
                    self.sensors[name] = sensor

            self.logger.debug(f"config.get('actuators', []) len: {len(config.get('actuators', []))}")
            for actuator_config in config.get('actuators', []):
                self.logger.debug(f"actuator_config: {actuator_config}")
                name = actuator_config['name']
                actuator = self.create_actuator(actuator_config)
                if actuator:
                    self.actuators[name] = actuator
                    self.logger.debug(f"Actuator added to dict on name: {name}")
                else:
                    self.logger.error(f"Actuator not created - can not add to dict")

            self.logger.debug(f"config.get('controllers', []) len: {len(config.get('controllers', []))}")
            for controller_config in config.get('controllers', []):
                self.logger.debug(f"controller_config: {controller_config}")
                name = controller_config.get('name', self.generate_unique_name())
                controller = self.create_controller(controller_config)
                if controller:
                    while name in self.controllers:
                        name = self.generate_unique_name()
                    self.controllers[name] = controller
                    self.logger.debug(f"Controller added to dict on name: {name}")
                else:
                    self.logger.error(f"Controller not created - can not add to dict")
        except Exception as ex:
            self.logger.error(f"Error loading components: {ex}")

    def create_sensor(self, sensor_config: Dict[str, Any]) -> Optional[BaseSensor]:
        """
        Creates and returns an instance of a sensor based on the provided configuration.

        Args:
            sensor_config (Dict[str, Any]): A dictionary containing the sensor configuration.

        Returns:
            Optional[BaseSensor]: An instance of the specified sensor type if successfully created, or None if there was an error or if required parameters were missing.
        """
        try:
            sensor_type = sensor_config['type']
            sensor_name = sensor_config.get('name', None)
            if not sensor_name:
                self.logger.error(f"Missing 'name' for sensor of type {sensor_type}.")
                return None
            params = sensor_config.get('params', {})
            params['name'] = sensor_name
            sensor_params = {
                'BaseSensor': {'optional': ['read_frequency', 'max_readings', 'start_immediately', 'anomaly_detection'],
                               'required': ['name']},
                'TemperatureSensor': {
                    'optional': ['max_value', 'min_value', 'read_frequency', 'max_readings', 'start_immediately',
                                 'anomaly_detection'], 'required': ['pin', 'name']},
                'HumiditySensor': {
                    'optional': ['max_value', 'min_value', 'read_frequency', 'max_readings', 'start_immediately',
                                 'anomaly_detection'], 'required': ['pin', 'name']},
                'LightSensor': {'optional': ['i2c_address', 'min_value', 'max_value', 'read_frequency', 'max_readings',
                                             'start_immediately', 'anomaly_detection'], 'required': ['name']},
                'SoilMoistureSensor': {
                    'optional': ['i2c_address', 'channel', 'min_value', 'max_value', 'read_frequency', 'max_readings',
                                 'start_immediately', 'anomaly_detection'], 'required': ['name']}
            }
            valid_params = {'name': sensor_name}
            if sensor_type in sensor_params:
                for param in params:
                    if param in sensor_params[sensor_type]['required'] + sensor_params[sensor_type]['optional']:
                        if isinstance(params[param], (int, float, bool, str)) or params[param] is None:
                            valid_params[param] = params[param]
                        else:
                            self.logger.warning(f"Incorrect type for {param} in {sensor_type}, using default value.")
                    else:
                        self.logger.warning(f"Unknown parameter {param} for {sensor_type}, ignoring it.")
                missing_required = [r for r in sensor_params[sensor_type]['required'] if r not in valid_params]
                if missing_required:
                    self.logger.error(f"Missing required parameters {missing_required} for {sensor_type}.")
                    return None
                try:
                    sensor_class = eval(sensor_type)
                    return sensor_class(**valid_params)
                except Exception as ex:
                    self.logger.error(f"Failed to create sensor {sensor_type} with params {valid_params}: {ex}")
                    return None
            else:
                self.logger.error(f"Unknown sensor type: {sensor_type}")
                return None
        except Exception as ex:
            self.logger.error(f"Cannot create sensor: {ex}")

    def create_actuator(self, actuator_config: Dict[str, Any]) -> Optional[BaseActuator]:
        """
        Creates an actuator object based on the validated configuration, including a name read from the configuration.

        Args:
            actuator_config (Dict[str, Any]): Configuration dictionary for the actuator, including 'name'.

        Returns:
            Optional[BaseActuator]: The created actuator object with its name set, or None if creation failed.
        """
        try:
            actuator_type = actuator_config['type']
            params = actuator_config.get('params', {})
            actuator_name = actuator_config.get('name', None)
            if not actuator_name:
                self.logger.error(f"Cant not create actuator without name")
                return None
            required_params = ['gpio_pin']
            optional_params = ['initial_state']
            valid_params = {'name': actuator_name}
            if actuator_type == 'BaseActuator':
                for param in params:
                    if param in required_params + optional_params:
                        if param == 'gpio_pin' and isinstance(params[param], int):
                            valid_params[param] = params[param]
                        elif param == 'initial_state' and isinstance(params[param], bool):
                            valid_params[param] = params[param]
                        else:
                            self.logger.warning(f"Incorrect type for {param} in {actuator_type}, using default value.")
                    else:
                        self.logger.warning(f"Unknown parameter {param} for {actuator_type}, ignoring it.")
                missing_required = [r for r in required_params if r not in valid_params]
                if missing_required:
                    self.logger.error(f"Missing required parameters {missing_required} for {actuator_type}.")
                    return None
                try:
                    return BaseActuator(**valid_params)
                except Exception as ex:
                    self.logger.error(f"Failed to create actuator {actuator_type} with params {valid_params}: {ex}")
                    return None
            else:
                self.logger.error(f"Unknown actuator type: {actuator_type}")
                return None
        except Exception as ex:
            self.logger.error(f"Cannot create actuator: {ex}")
            return None

    def create_controller(self, controller_config: Dict[str, Any]) -> Optional[BaseController]:
        """
        Creates a controller object based on the validated configuration, linking it with its sensors and actuator.

        Args:
            controller_config (Dict[str, Any]): Configuration dictionary for the controller.

        Returns:
            Optional[BaseController]: The created controller object or None if creation failed due to invalid configuration or missing components.
        """
        try:
            controller_type = controller_config['type']
            sensor_names = controller_config.get('sensors', {})
            actuator_name = controller_config.get('actuator')
            params = controller_config.get('params', {})
            sensors_list = []
            for sensor_name, sensor_info in sensor_names.items():
                sensor = self.sensors.get(sensor_name)
                if sensor:
                    sensor_info_validated = {
                        'sensor': sensor,
                        'threshold': sensor_info.get('threshold'),
                        'comparison': BaseController.get_comparison(sensor_info.get('comparison')),
                    }
                    sensors_list.append(sensor_info_validated)
                else:
                    self.logger.error(f"Sensor '{sensor_name}' not found.")
                    return None
            actuator = self.actuators.get(actuator_name)
            if not actuator:
                self.logger.error(f"Actuator '{actuator_name}' not found.")
                return None
            if controller_type == 'IrrigationController':
                irrigation_params = {
                    'pump_flow_rate': params.pop('pump_flow_rate', None),
                    'water_volume': params.pop('water_volume', None),
                    'max_lift_height': params.pop('max_lift_height', None),
                    'current_lift_height': params.pop('current_lift_height', None),
                }
                if irrigation_params['pump_flow_rate'] is not None and irrigation_params['water_volume'] is not None:
                    activation_time = IrrigationController.calculate_pump_activation_time(**irrigation_params)
                    params['activation_time'] = activation_time
            try:
                if controller_type in ['IrrigationController', 'VentilationController', 'LightingController']:
                    controller_class = eval(controller_type)
                    controller_instance = controller_class(sensors=sensors_list, actuator=actuator, **params)
                    return controller_instance
                else:
                    self.logger.error(f"Unknown controller type: {controller_type}")
                    return None
            except Exception as ex:
                self.logger.error(f"Failed to create controller {controller_type} with error: {ex}")
                return None
        except Exception as ex:
            self.logger.error(f"Can not create controller: {ex}")

    def get_sensor_by_name(self, name: str) -> Optional[BaseSensor]:
        """
        Retrieves a sensor object by its name from the list of configured sensors.

        Args:
            name (str): The name identifier for the sensor.

        Returns:
            Optional[BaseSensor]: The sensor object if found, None otherwise.
        """
        return self.sensors.get(name, None)

    def get_actuator_by_name(self, name: str) -> Optional[BaseActuator]:
        """
        Retrieves an actuator object by its name from the list of configured actuators.

        Args:
            name (str): The name identifier for the actuator.

        Returns:
            Optional[BaseActuator]: The actuator object if found, None otherwise.
        """
        return self.actuators.get(name, None)

    def generate_unique_name(self):
        """
        Generates a unique name for a controller using a combination of timestamp and UUID.

        Returns:
            str: A unique name string.
        """
        unique_name = f"Controller_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        return unique_name

    def run_arduinoLCD(self):
        arduino_lcd_manager = ArduinoManager(self.sensors)
        arduino_lcd_manager.start_scan()
        arduino_lcd_manager.start_reading()

    def __del__(self) -> None:
        """
        Destructor method to ensure all application resources are properly cleaned up before the application exits.
        Stops the application, sensors, and controllers, and logs the cleanup process.
        """
        try:
            self.stop_app()
            self.stop_sensors_reading()
            self.stop_controllers()
            self.logger.info("Application resources have been cleaned up.")
        except Exception as ex:
            self.logger.error(f"Error during application cleanup: {ex}")
