
import os
import sys


from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets, QtCore, Qt
from PyQt5.QtWidgets import QStyleFactory
from PyQt5.QtGui import QFont
from model.experiment import Experiment
from frontend.main_window import MainWindow
from colorama import Fore
import logging
from utils.Log import set_root_logger
from qt_material import apply_stylesheet
from config.config import DEBUG, CONFIG_FILE

def setup_logger():
    if DEBUG:
        logger = set_root_logger(logging.DEBUG)
    else:
        logger = set_root_logger(logging.INFO)

def run_gui():
    try:
        experiment = Experiment(CONFIG_FILE)
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        app = QApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        apply_stylesheet(app, theme='assets/custom_theme.xml')
        style_sheet = app.styleSheet()
        with open('assets/custom.css', 'r') as file:
            app.setStyleSheet(style_sheet + file.read().format(**os.environ))
        window = MainWindow(experiment)
        window.show()
        window.try_init_adc_box()
        app.exec()
        if window.isExperimentLoad:
            experiment.finalize()
    except:
        logging.error("Failed to finalize", exc_info=True)
        experiment.finalize()

if __name__ == '__main__':
    setup_logger()
    run_gui()
