import logging
from influxdb import InfluxDBClient, exceptions
from typing import Dict
from app_config import APP_CONFIG_PATH, AppConfig

class InfluxDBManager:
    """
    A singleton class to manage InfluxDB operations such as establishing a connection
    and writing data points to the database.

    Attributes:
        client (InfluxDBClient): A client connection to InfluxDB.
        logger (logging.Logger): Logger for logging messages.
    """
    _instance = None

    def __new__(cls):
        """
        Creates a new instance of the InfluxDBManager class if one doesn't already exist.
        Establishes a connection to an InfluxDB instance using the configuration specified in the
        application's configuration file.

        Returns:
            InfluxDBManager: A singleton instance of the InfluxDBManager class.
        """
        if cls._instance is None:
            cls._instance = super(InfluxDBManager, cls).__new__(cls)
            app_config = AppConfig(APP_CONFIG_PATH).get_config()
            influx_config = app_config.get('influxdb', {})
            cls._instance.logger = logging.getLogger('app_logger')
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
            except KeyError as ex:
                cls._instance.logger.error(f"Missing InfluxDB configuration: {ex}")
                cls._instance.client = None
            except exceptions.InfluxDBClientError as ex:
                cls._instance.logger.error(f"InfluxDB client error: {ex}")
                cls._instance.client = None
            except Exception as ex:
                cls._instance.logger.error(f"Failed to initialize InfluxDB connection: {ex}")
                cls._instance.client = None
        return cls._instance

    def write_data(self, measurement: str, fields: Dict[str, float], tags: Dict[str, str]):
        """
        Writes a data point to the InfluxDB database.

        Args:
            measurement (str): The name of the measurement (table) to write the data point to.
            fields (Dict[str, float]): The fields (key-value pairs) to write to the database.
            tags (Dict[str, str]): The tags (key-value pairs) associated with the data point.

        This method logs an error and aborts if the InfluxDB client has not been successfully initialized.
        """
        if not self.client:
            self.logger.error("InfluxDB client is not initialized. Data write aborted.")
            return

        json_body = [
            {
                "measurement": measurement,
                "tags": tags,
                "fields": fields
            }
        ]
        try:
            self.client.write_points(json_body)
            self.logger.info(f"Data written to InfluxDB: {json_body}")
        except exceptions.InfluxDBServerError as ex:
            self.logger.error(f"InfluxDB server error, failed to write data: {ex}")
        except exceptions.InfluxDBClientError as ex:
            self.logger.error(f"InfluxDB client error, failed to write data: {ex}")
        except Exception as ex:
            self.logger.error(f"Unexpected error occurred while writing data to InfluxDB: {ex}")
