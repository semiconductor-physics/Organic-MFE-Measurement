import shutil
import os
from datetime import date

import logging
logger = logging.getLogger(__name__)
from config.config import CONFIG_FILE

def save_config_file(path):
    configFile = os.path.join(path, f"config.yaml")
    shutil.copy(CONFIG_FILE, configFile)


def create_dir(path: str, name: str | None = None) -> str:
    if name:
        path = os.path.join(path, name)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            logger.error(f"Failed to create {path}")
            return ""
        logger.info(f"Create dir: {path}")
        return path
    else:
        logger.info(f"Already exist dir: {path}")
        return path
    
def create_date_dir(path: str) -> str:
    today = date.today()
    dirPath = os.path.join(path, f'{today.strftime("%d-%m-%Y")}')
    path = create_dir(dirPath)
    return path