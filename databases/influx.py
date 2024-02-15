import logging
from influxdb import InfluxDBClient, exceptions
from typing import Dict
from app_config import APP_CONFIG_PATH, AppConfig
import time

class InfluxDBManager:
    """
    Manages connections and data operations with an InfluxDB database instance.
    Implements a singleton pattern to ensure only one connection exists throughout the application.
    Handles reconnection attempts if the initial connection fails or if the connection is lost.

    Attributes:
        client (InfluxDBClient): Client instance for connecting to an InfluxDB database.
        logger (logging.Logger): Logger instance for logging messages.
    """
    _instance = None

    def __new__(cls):
        """
        Ensures a single instance of the InfluxDBManager class is created. Initializes the connection to the InfluxDB database using configuration from the application's config file.

        Returns:
            InfluxDBManager: The singleton instance of the InfluxDBManager class.
        """
        if cls._instance is None:
            cls._instance = super(InfluxDBManager, cls).__new__(cls)
            cls._instance.logger = logging.getLogger('app_logger')
            cls._instance.client = None
            cls._initialize_connection()
        return cls._instance

    @classmethod
    def _initialize_connection(cls):
        """
        Initializes the connection to the InfluxDB database using the configuration specified in the application's configuration file. Attempts to reconnect if the initial connection fails, with a defined number of retries and interval between retries.
        """
        app_config = AppConfig(APP_CONFIG_PATH).get_config()
        influx_config = app_config.get('influxdb', {})
        retry_interval = 60
        max_retries = 10
        retries = 0

        while retries < max_retries:
            try:
                cls._instance.client = InfluxDBClient(
                    host=influx_config.get('host', 'localhost'),
                    port=influx_config.get('port', 8086),
                    username=influx_config.get('username', ''),
                    password=influx_config.get('password', ''),
                    database=influx_config.get('database', 'garden')
                )
                cls._instance.client.ping()
                cls._instance.logger.info("Successfully connected to InfluxDB.")
                return
            except (KeyError, exceptions.InfluxDBClientError, Exception) as ex:
                cls._instance.logger.error(f"Failed to connect to InfluxDB, attempt {retries + 1} of {max_retries}: {ex}")
                time.sleep(retry_interval)
                retries += 1

        cls._instance.logger.error("Exceeded maximum number of retries to connect to InfluxDB. Data write operations will be skipped.")
        cls._instance.client = None

    def write_data(self, measurement: str, fields: Dict[str, float], tags: Dict[str, str]):
        """
        Writes a single data point to the InfluxDB database. If the InfluxDB client is not initialized, it attempts to reinitialize the connection before writing.

        Args:
            measurement (str): The measurement name to which the data point belongs.
            fields (Dict[str, float]): A dictionary of field names and their values for the data point.
            tags (Dict[str, str]): A dictionary of tag names and their values associated with the data point.
        """
        if not self.client:
            self.logger.warning("InfluxDB client is not initialized. Attempting to reconnect.")
            self._initialize_connection()
            if not self.client:
                self.logger.error("Reconnection to InfluxDB failed. Data write aborted.")
                return
        json_body = [{"measurement": measurement, "tags": tags, "fields": fields}]
        try:
            self.client.write_points(json_body)
            self.logger.info(f"Data written to InfluxDB: {json_body}")
        except exceptions.InfluxDBServerError as ex:
            self.logger.error(f"InfluxDB server error, failed to write data: {ex}")
        except exceptions.InfluxDBClientError as ex:
            self.logger.error(f"InfluxDB client error, failed to write data: {ex}")
        except Exception as ex:
            self.logger.error(f"Unexpected error occurred while writing data to InfluxDB: {ex}")
