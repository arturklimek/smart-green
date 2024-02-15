import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

class LoggerManager:
    """
    LoggerManager is responsible for setting up and configuring loggers
    in the application. It uses the Python logging module to create loggers
    that write to both the console and a rotating file.

    Static Methods:
        setup_logger: Configures and returns a logger with the specified name and settings.
    """

    @staticmethod
    def setup_logger(log_name: str, log_file: str, level_console: Optional[int] = logging.INFO, level_file: Optional[int] = logging.DEBUG) -> logging.Logger:
        """
        Sets up a logger with given configurations.

        This method configures a logger to write logs to a rotating file and the console.
        It ensures that multiple handlers are not added to the same logger.

        Args:
            log_name (str): The name of the logger.
            log_file (str): The path to the log file.
            level_console (Optional[int]): The logging level for the console handler. Defaults to logging.INFO.
            level_file (Optional[int]): The logging level for the file handler. Defaults to logging.DEBUG.

        Returns:
            logging.Logger: Configured logger instance.
        """
        try:
            logger = logging.getLogger(log_name)
            if not logger.handlers:
                logger.setLevel(logging.DEBUG)
                file_handler = RotatingFileHandler(log_file, maxBytes=5000000, backupCount=2, encoding='utf-8')
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - (%(filename)s:%(lineno)d) - %(message)s')
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(level_file)
                console_handler = logging.StreamHandler(sys.stdout)
                console_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
                console_handler.setFormatter(console_formatter)
                console_handler.setLevel(level_console)
                logger.addHandler(file_handler)
                logger.addHandler(console_handler)
            return logger
        except Exception as ex:
            print(f"Error setting up logger {log_name}: {ex}")
            raise
