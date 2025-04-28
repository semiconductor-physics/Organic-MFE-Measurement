import logging
from log import setup_logger
setup_logger(debug_level=logging.INFO)
import sys
import os
from omc_processing import process_measurement
import yaml

if __name__ == '__main__':
    with open('process_config.yaml', mode='r') as f:
        config = yaml.safe_load(f)
    path = sys.argv[1]
    for subdir in os.listdir(path):
        if not os.path.isdir(f'{path}/{subdir}'):
            continue
        measurment_dir = f'{path}\\{subdir}'
        process_measurement(measurment_dir, config=config)
        
    
    