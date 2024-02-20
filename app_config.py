import os
import yaml
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_DIR_PATH = os.path.join(APP_PATH, 'logs')
APP_CONFIG_PATH = os.path.join(APP_PATH, 'config.yaml')

DEFAULT_CONFIG = {

}

class AppConfig:
    """
    AppConfig is a singleton class responsible for handling application configuration.
    It loads, updates, and saves configuration data from/to a YAML file. This class ensures that there is only one instance of the configuration across the application.

    Attributes:
        config_file (str): Path to the YAML configuration file.
        config_data (dict): Dictionary holding the loaded configuration data.

    Methods:
        load_config: Loads configuration data from the YAML file, merging it with default values.
        save_config: Saves the current configuration data to the YAML file.
        update_config: Updates the configuration data with provided values and saves it.
        get_config: Returns the current configuration data.
        merge_config: Merges loaded configuration with default values and saves if necessary.
    """

    _instance = None

    def __new__(cls, config_file: str):
        """
        Create a new instance of AppConfig or return the existing one.
        This method implements the singleton pattern. If an instance of AppConfig doesn't exist, it creates a new one and initializes it. If an instance already exists, it returns the existing instance.

        Args:
            config_file (str): The path to the configuration file in YAML format.

        Returns:
            AppConfig: An instance of the AppConfig class.
        """
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.config_file = config_file
            cls._instance.config_data = DEFAULT_CONFIG.copy()
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """
        Load configuration from a YAML file, merging it with default values.
        This method checks if the configuration file exists. If it does, it loads the configuration and merges it with the default values defined in DEFAULT_CONFIG. If the file does not exist, it uses the default configuration.
        """
        logger = logging.getLogger('app_logger')
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    file_config = yaml.safe_load(file) or {}
                self.merge_config(file_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as ex:
                logger.error(f"Failed to load configuration: {ex}")
                logger.info("Using default configuration.")
        else:
            logger.warning(f"Config file {self.config_file} does not exist. Using default configuration.")
            self.save_config()

    def merge_config(self, file_config: dict):
        """
        Merge loaded configuration with default values and save if necessary.

        Args:
            file_config (dict): Configuration data loaded from the YAML file.

        Compares file_config with DEFAULT_CONFIG and adds any missing keys from
        DEFAULT_CONFIG to file_config. Updates the config_data and saves changes if needed.
        """
        missing_keys = set(DEFAULT_CONFIG) - set(file_config)
        if missing_keys:
            for key in missing_keys:
                file_config[key] = DEFAULT_CONFIG[key]
            self.config_data.update(file_config)
            self.save_config()
        else:
            self.config_data = file_config

    def save_config(self):
        """
        Save the current configuration to a YAML file.
        Writes the current state of config_data to the YAML file specified in config_file. If an error occurs during saving, it logs an error message.
        """
        logger = logging.getLogger('app_logger')
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                yaml.dump(self.config_data, file, allow_unicode=True, default_flow_style=False)
                logger.info("Configuration saved successfully.")
        except Exception as ex:
            logger.error(f"Failed to save configuration: {ex}")

    def update_config(self, new_config_data: dict):
        """
        Update the configuration with new data and save it.

        Args:
            new_config_data (dict): A dictionary containing configuration data to be updated.
        """
        logger = logging.getLogger('app_logger')
        try:
            self.config_data.update(new_config_data)
            self.save_config()
            logger.info("Configuration updated successfully.")
        except Exception as ex:
            logger.error(f"Failed to update configuration: {ex}")

    def get_config(self):
        """
        Return the current configuration data.

        Returns:
            dict: The current configuration data.
        """
        return self.config_data

