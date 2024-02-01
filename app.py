import logging
import os
from app_config import LOG_DIR_PATH, AppConfig, APP_CONFIG_PATH
from logger import LoggerManager

class App:
    def __init__(self):
        self.setup_app()
        self.logger = logging.getLogger('app_logger')

    def setup_app(self):
        self.setup_dir_structure([LOG_DIR_PATH])
        LoggerManager.setup_logger('app_logger', os.path.join(LOG_DIR_PATH, 'app.log'), level_console=logging.INFO, level_file=logging.DEBUG)
        self.logger.info('Application initialized')
        app_config = AppConfig(APP_CONFIG_PATH)

    @staticmethod
    def setup_dir_structure(dir_list):
        for dir_path in dir_list:
            try:
                App.create_dir(dir_path)
            except Exception as ex:
                print(f'Error creating directory {dir_path}: {ex}')

    @staticmethod
    def create_dir(dir_path: str):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def start_app(self):
        pass
