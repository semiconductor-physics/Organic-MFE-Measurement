import re
import numpy as np
import serial
import yaml
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    qApp,
    QSizeGrip,
    QDialog,
)
from PyQt5 import QtWidgets
from config.config import CONFIG_FILE
from frontend.TitleBar import MyBar
from model.experiment import Experiment
import logging
import os

from frontend.Widgets import (
    SaveDialog,
    ADCSettingsWindow,
    MagnetSettingsWindow,
    OLEDSettingsWindow,
    CryoSettingsWindow,
    StatusWidget,
    ADCPlotWidget,
    ResultPlotWidget,
    DebugActions,
    ExperiementActions,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, experiment: Experiment):
        super().__init__()
        self.experiment = experiment
        self.build_gui()
        self.set_gui_from_config()
        self.setMinimumSize(900, 820)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    def set_gui_from_config(self):
        self.adc_settings_window.init_ports()
        self.adc_settings_window.set_settings(self.experiment.config["ADC"])
        self.magnet_settings_window.set_settings(self.experiment.config["Magnet"])
        self.oled_settings_window.set_settings(self.experiment.config["OLED"])

    def build_gui(self):
        self.setWindowTitle("MFE Measurement")
        self.isExperimentLoad = False
        self.widget = QWidget()
        self._layout = QVBoxLayout(self.widget)
        self.titleBar = MyBar(self)
        self._layout.addWidget(self.titleBar)
        self.widget.mouseMoveEvent = self.mouseMoveEvent
        self.layoutLMR = QHBoxLayout()
        self.controls_layout = QVBoxLayout()
        self.controls_layout.setSpacing(8)
        self.adc_plots_layout = ADCPlotWidget(self.experiment)
        self.layout_right = ResultPlotWidget(self.experiment)
        self.layoutLMR.addLayout(self.controls_layout)
        self.layoutLMR.addWidget(self.adc_plots_layout, 5)
        self.layoutLMR.addWidget(self.layout_right, 4)
        self._layout.addLayout(self.layoutLMR)
        self.save_dialog = SaveDialog(self)
        self.cryo_dialog = CryoSettingsWindow(self, self.experiment.config["Cryo"])
        self.status_widget = StatusWidget()
        self.controls_layout.addWidget(self.status_widget)
        self.adc_settings_window = ADCSettingsWindow(
            port_refresh_callback=self.try_init_adc_box
        )
        self.controls_layout.addWidget(self.adc_settings_window)
        self.magnet_settings_window = MagnetSettingsWindow()
        self.controls_layout.addWidget(self.magnet_settings_window)
        self.oled_settings_window = OLEDSettingsWindow()
        self.controls_layout.addWidget(self.oled_settings_window)
        self.controls_layout.addStretch(1)

        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(QSize(8, 8))
        self._layout.addWidget(size_grip, 0, Qt.AlignBottom | Qt.AlignRight)

        # Buttons
        self.debug_buttons = DebugActions(
            self.experiment,
            self.adc_plots_layout.set_auto_range,
            status_widget=self.status_widget,
        )
        self.controls_layout.addWidget(self.debug_buttons)
        self.experiment_actions = ExperiementActions(
            self.experiment,
            self._on_cryo_mode_changed,
            self.save_clicked,
            self._on_run,
            status_widget=self.status_widget,
        )
        self.controls_layout.addWidget(self.experiment_actions)

        self.setCentralWidget(self.widget)
        

    def _on_refresh_ports(self):
        self.init_ports()
        self.try_init_experiment()

    def try_init_adc_box(self, auto_port_select=True):
        if auto_port_select:
            if not self.adc_settings_window.select_cp210x_uart_port():
                self.status_widget.set_status("DAQ not found")
                return
        port = self.adc_settings_window.get_port()
        self.status_widget.set_status(f"Connecting to {port}...")
        qApp.processEvents()
        try:
            logger.info(f"Connecting to {port}...")
            ans = self.experiment.load_daq(port)
            logger.info(f"{ans=}")
            if re.match("Here is .* with 24 Bit ADC and 16 Bit DAC", ans):
                logger.info("Connected")
                self.status_widget.set_status(f"Connected to {port}!")
                self.isExperimentLoad = True
            else:
                logger.info("Device answer not ok")
                self.status_widget.set_status(f"DAQ not found")
                self.isExperimentLoad = False

        except serial.serialutil.SerialException:
            self.status_widget.set_status(f"DAQ not found")
            logger.warning(f"Serial Exception")
            self.isExperimentLoad = False

    def closeEvent(self, event):
        self.debug_buttons.close()
        self.experiment_actions.close()
        self._updateConfigFile()

    def _updateConfigFile(self):
        with open(CONFIG_FILE, "r") as file:
            config = yaml.safe_load(file)
            config["ADC"].update(self.adc_settings_window.get_settings())
            config["Magnet"].update(self.magnet_settings_window.get_settings())
            config["OLED"].update(self.oled_settings_window.get_settings())
            config["Cryo"][
                "enabled"
            ] = self.experiment_actions.cryo_mode_checkbox.isChecked()
            config["Cryo"].update(self.cryo_dialog.get_settings())

        with open(CONFIG_FILE, "w") as file:
            yaml.safe_dump(config, file)

    def _on_cryo_mode_changed(self, state):
        if state:
            if self.cryo_dialog.exec() != QDialog.Accepted:
                self.experiment_actions.cryo_mode_checkbox.setChecked(False)
                self.cryo_dialog.set_settings(self.experiment.config["Cryo"])

    def save_clicked(self):
        self.status_widget.set_status("Saving...")
        if self.save_dialog.exec() != QDialog.Accepted:
            return
        probe_name = self.save_dialog.get_probe_name()
        self._updateConfigFile()
        last_path = self.experiment.config["Saving"]["folder"]
        dirPath = QtWidgets.QFileDialog.getExistingDirectory(self, "Save to", last_path)
        if not os.path.isdir(dirPath):
            return
        self.experiment.save(dirPath, probe_name=probe_name)


    def _on_run(self):
        self.adc_plots_layout.set_auto_range()
        self._updateConfigFile()
        
    def _on_experiment_finished(self):
        self.status_widget.set_status('Experiment finished!')
        self.experiment_actions.on_experiment_finished()