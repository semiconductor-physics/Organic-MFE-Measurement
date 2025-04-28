from PyQt5.QtCore import Qt, QSize, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QVBoxLayout,
    QSizePolicy,
    QFrame,
    QGridLayout,
    QCheckBox,
    QHBoxLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QRadioButton,
    QProgressBar,
)
from PyQt5.QtGui import QColor, QPixmap, QIcon, QPainter
from typing import Iterable, Callable
from model.daq import get_available_ports, get_cp210x_uart_port, DRATE_CODES, GAIN_CODES
import pyqtgraph as pg
import os
from model.experiment import Experiment

import logging
logger = logging.getLogger(__name__)

gain_labels = list(GAIN_CODES.keys())
drate_labels = list(DRATE_CODES.keys())

class ExperimentWorker(QObject):
    finished_signal = pyqtSignal()
    started_signal = pyqtSignal()
    progress_signal = pyqtSignal(float)

    def __init__(self, experiment: Experiment):
        super().__init__()
        self.experiment = experiment

    @pyqtSlot()
    def run_experiment(self):
        self.experiment.progress_callback = self._on_progress
        self.started_signal.emit()
        self.experiment.run_experiment()
        self.experiment.progress_callback = None
        self.finished_signal.emit()

    def stop(self):
        self.experiment.running = False

    def _on_progress(self, progress: float):
        self.progress_signal.emit(progress)

class StatusWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        title = SettingsTitle("Status:")
        self.status = QLineEdit()
        self.status.setReadOnly(True)
        layout.addWidget(title)
        layout.addWidget(self.status)
        self.running_counter = 0
        self._text = ""

    def set_status(self, status: str):
        self._text = status
        self.status.setText(status)

    def continue_status(self):
        self.running_counter += 1
        self.status.setText(self._text + "." * (self.running_counter % 6))


class DebugActions(QWidget):
    def __init__(
        self,
        experiment: Experiment,
        start_callback: Callable[[], None] | None = None,
        stop_callback: Callable[[], None] | None = None,
        status_widget: StatusWidget | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.experiment = experiment
        self.start_button = QPushButton("Start Debug")
        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button = QPushButton("Stop Debug")
        self.stop_button.setProperty("class", "danger")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        layout = QHBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.status_widget = status_widget
        self.status_refresh_timer = QTimer()
        self.status_refresh_timer.timeout.connect(self._on_status_refresh)

    def update_status(self, status: str):
        if self.status_widget:
            self.status_widget.set_status(status)

    def _on_start_clicked(self):
        self.update_status("Debugging")
        if self.start_callback:
            self.start_callback()
        self.experiment.debug_stream(self.experiment.data_store.listen)
        self.start_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.status_refresh_timer.start(1000)

    def _on_stop_clicked(self):
        self.update_status("")
        self.experiment.stop_stream(self.experiment.data_store.listen)
        self.start_button.setVisible(True)
        self.stop_button.setVisible(False)
        if self.stop_callback:
            self.stop_callback()
        self.status_refresh_timer.stop()

    def _on_status_refresh(self):
        if self.status_widget:
            self.status_widget.continue_status()

    def close(self):
        self._on_stop_clicked()


class ExperiementActions(QWidget):
    def __init__(
        self,
        experiment: Experiment,
        cryo_callback: Callable[[object], None],
        save_callback: Callable[[], None],
        run_callback: Callable[[], None] | None = None,
        status_widget: StatusWidget | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.experiment = experiment
        self.status_widget = status_widget
        self.status_refresh_timer = QTimer()
        self.status_refresh_timer.timeout.connect(self._on_status_refresh)
        self.run_callback = run_callback
        self.save_callback = save_callback
        self.run_button = QPushButton("Run")
        self.run_button.setProperty("class", "action")
        self.run_button.clicked.connect(self._on_run_clicked)
        self.abort_button = QPushButton("Abort")
        self.abort_button.setProperty("class", "danger")
        self.abort_button.clicked.connect(self._on_abort_clicked)
        self.abort_button.hide()
        self.save_button = QPushButton("Save data")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.cryo_mode_checkbox = QCheckBox("Cryo-Mode", self)
        self.cryo_mode_checkbox.toggled.connect(cryo_callback)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)

        run_layout = QHBoxLayout()
        run_layout.addWidget(self.cryo_mode_checkbox)
        run_layout.addWidget(self.run_button)
        run_layout.addWidget(self.abort_button)
        layout = QVBoxLayout()
        layout.addWidget(self.progress_bar)
        layout.addLayout(run_layout)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def _on_run_clicked(self):
        if self.run_callback:
            self.run_callback()
        self.thread = QThread()
        self.worker = ExperimentWorker(self.experiment)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run_experiment)
        self.worker.started_signal.connect(self.on_experiment_started)
        self.worker.finished_signal.connect(self.on_experiment_finished)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.progress_signal.connect(self.update_progress)  
        self.thread.start()

    def _on_abort_clicked(self):
        self.update_status("")
        self.experiment.running = False
        self.run_button.show()
        self.abort_button.hide()
        self.status_refresh_timer.stop()

    def _on_save_clicked(self):
        self.save_callback()

    def update_status(self, status: str):
        if self.status_widget:
            self.status_widget.set_status(status)

    def update_progress(self, progress: float):
        self.progress_bar.setValue(int(progress*100))

    def _on_status_refresh(self):
        if self.status_widget:
            self.status_widget.continue_status()

    def on_experiment_started(self):
        self.run_button.hide()
        self.abort_button.show()
        self.update_status("Experiment running")
        self.status_refresh_timer.start(1000)

    def on_experiment_finished(self):
        self.run_button.show()
        self.abort_button.hide()
        self.status_refresh_timer.stop()
        self.update_status("Experiment finished")

    def close(self):
        self._on_abort_clicked()


class ResultPlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, experiment: Experiment, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setBackground(os.environ.get("QTMATERIAL_SECONDARYDARKCOLOR"))
        self.oled_plot_widget = self.addPlot(row=0, col=0)
        self.I_photo_plot_widget = self.addPlot(row=1, col=0)
        self.configure_plot_widget(self.oled_plot_widget, "LED/B")
        self.configure_plot_widget(self.I_photo_plot_widget, "Photo/B")
        self.I_photo_plot_widget.setXLink(self.oled_plot_widget)
        self.oled_plot = self.oled_plot_widget.plot()
        self.I_photo_plot = self.I_photo_plot_widget.plot()
        self.configure_plot(self.oled_plot, QColor(36, 252, 3))
        self.configure_plot(self.I_photo_plot, QColor(3, 215, 252))
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plots)
        self.update_timer.start(1000)
        self.experiment = experiment

    def configure_plot_widget(self, plot_widget, name):
        fg_color = os.environ.get("QTMATERIAL_PRIMARYCOLOR")
        text_color = os.environ.get("QTMATERIAL_SECONDARYTEXTCOLOR")
        plot_widget.showGrid(x=True, y=True, alpha=0.2)
        plot_widget.getAxis("left").setTextPen(text_color)
        plot_widget.getAxis("left").setPen(fg_color)
        plot_widget.getAxis("bottom").setTextPen(text_color)
        plot_widget.getAxis("bottom").setPen(fg_color)
        plot_widget.setTitle(name, color=text_color)
        plot_widget.setLabel("left", "Voltage", units="V")
        plot_widget.setLabel("bottom", "B", units="T")
        plot_widget.enableAutoRange()

    def configure_plot(self, plot, color):
        plot.setPen(color)
        plot.setDownsampling(ds=None, auto=True, method="mode")

    def _update_plots(self):
        idx = self.experiment.data_store.plot_idx
        self.oled_plot.setData(
            y=self.experiment.data_store.oled_list[idx:], x=self.experiment.data_store.magnet_B_list[idx:]
        )
        self.I_photo_plot.setData(
            y=self.experiment.data_store.I_photo_list[idx:], x=self.experiment.data_store.magnet_B_list[idx:]
        )


class ADCPlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, experiment: Experiment, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setBackground(os.environ.get("QTMATERIAL_SECONDARYDARKCOLOR"))
        self.hall_plot_widget = self.addPlot(row=0, col=0)
        self.oled_plot_widget = self.addPlot(row=1, col=0)
        self.I_photo_plot_widget = self.addPlot(row=2, col=0)
        self.configure_plot_widget(self.hall_plot_widget, "Hall")
        self.configure_plot_widget(self.oled_plot_widget, "LED")
        self.configure_plot_widget(self.I_photo_plot_widget, "Photodiode")
        self.hall_plot = self.hall_plot_widget.plot()
        self.oled_plot = self.oled_plot_widget.plot()
        self.I_photo_plot = self.I_photo_plot_widget.plot()
        self.oled_plot_widget.setXLink(self.hall_plot_widget)
        self.I_photo_plot_widget.setXLink(self.hall_plot_widget)
        self.configure_plot(self.hall_plot, QColor(207, 3, 252))
        self.configure_plot(self.oled_plot, QColor(36, 252, 3))
        self.configure_plot(self.I_photo_plot, QColor(3, 215, 252))
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plots)
        self.update_timer.start(50)
        self.experiment = experiment

    def configure_plot_widget(self, plot_widget, name):
        fg_color = os.environ.get("QTMATERIAL_PRIMARYCOLOR")
        text_color = os.environ.get("QTMATERIAL_SECONDARYTEXTCOLOR")
        plot_widget.showGrid(x=True, y=True, alpha=0.2)
        plot_widget.getAxis("left").setTextPen(text_color)
        plot_widget.getAxis("left").setPen(fg_color)
        plot_widget.getAxis("bottom").setTextPen(text_color)
        plot_widget.getAxis("bottom").setPen(fg_color)
        plot_widget.setTitle(name, color=text_color)
        plot_widget.setLabel("left", "Voltage", units="V")
        plot_widget.setLabel("bottom", "Sample")
        plot_widget.enableAutoRange()

    def configure_plot(self, plot, color):
        plot.setPen(color)

    def _update_plots(self):
        idx = self.experiment.data_store.plot_idx
        self.hall_plot.setData(y=self.experiment.data_store.V_hall_list[idx:])
        self.oled_plot.setData(y=self.experiment.data_store.oled_list[idx:])
        self.I_photo_plot.setData(y=self.experiment.data_store.I_photo_list[idx:])

    def set_auto_range(self):
        self.hall_plot_widget.enableAutoRange()
        self.oled_plot_widget.enableAutoRange()
        self.I_photo_plot_widget.enableAutoRange()


class SettingsTitle(QLabel):
    def __init__(self, title: str, parent=None):
        super().__init__(title)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("font-size: 14px; margin-bottom: 2px;")


class InputLabel(QLabel):
    def __init__(self, label: str):
        super().__init__(label)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignLeft)
        self.setIndent(8)


class LabeledComboBox(QWidget):
    def __init__(self, label: str):
        super().__init__()
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        self.label = InputLabel(label)
        self.combobox = QComboBox()
        layout.addWidget(self.label)
        layout.addWidget(self.combobox)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

    def set_current_index(self, index: int):
        self.combobox.setCurrentIndex(index)

    def add_items(self, items: Iterable[str]):
        self.combobox.addItems(items)

    def current_index(self) -> int:
        return self.combobox.currentIndex()


class SettingsWindow(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self._layout = QVBoxLayout()
        self._layout.addWidget(SettingsTitle(title))
        self.setLayout(self._layout)
        self.setObjectName("CardFrame")


def colorize_icon(pixmap, color):
    # Create a new pixmap with the same size as the original
    colored_pixmap = QPixmap(pixmap.size())
    colored_pixmap.fill(Qt.transparent)  # Fill with transparent background
    # Create a QPainter to draw on the new pixmap
    painter = QPainter(colored_pixmap)
    # Draw the original pixmap
    painter.drawPixmap(0, 0, pixmap)
    # Set the composition mode to source in
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    # Fill the pixmap with the desired color
    painter.fillRect(colored_pixmap.rect(), color)
    painter.end()  # End the painter
    return colored_pixmap


class ADCSettingsWindow(SettingsWindow):
    def __init__(self, port_refresh_callback: Callable[[], None], parent=None):
        super().__init__("ADC", parent)
        port_objects = QVBoxLayout()
        port_objects.setContentsMargins(0, 0, 0, 0)
        port_objects.setSpacing(0)
        port_label = InputLabel("Serial port:")
        self.COM_port_selectbox = QComboBox()
        self.refresh_ports_button = QPushButton()
        self.icon = QPixmap("assets/refresh-icon.png")
        reload_icon = colorize_icon(
            self.icon, QColor(os.environ.get("QTMATERIAL_PRIMARYCOLOR"))
        )
        self.refresh_ports_button.setIcon(QIcon(reload_icon))
        self.refresh_ports_button.setIconSize(QSize(28, 28))
        self.refresh_ports_button.setObjectName("refresh-ports")
        self.refresh_ports_button.clicked.connect(self._on_refresh_ports)
        self.refresh_ports_button.pressed.connect(self.on_button_pressed)
        self.refresh_ports_button.released.connect(self.on_button_released)
        port_layout = QHBoxLayout()
        port_layout.setSpacing(12)
        port_layout.addWidget(self.COM_port_selectbox)
        port_layout.addWidget(self.refresh_ports_button)
        port_objects.addWidget(port_label)
        port_objects.addLayout(port_layout)
        self._layout.addLayout(port_objects)
        self.sample_rate_selectbox = LabeledComboBox("Rate:")
        self.sample_rate_selectbox.add_items(drate_labels)
        self.gain_selectbox = LabeledComboBox("Gain:")
        self.gain_selectbox.add_items(gain_labels)
        adc_settings_hbox = QHBoxLayout()
        adc_settings_hbox.addWidget(self.sample_rate_selectbox)
        adc_settings_hbox.addWidget(self.gain_selectbox)
        self._layout.addLayout(adc_settings_hbox)
        self.port_refresh_callback = port_refresh_callback

    def set_settings(self, settings: dict):
        self.gain_selectbox.set_current_index(gain_labels.index(settings["gain"]))
        self.sample_rate_selectbox.set_current_index(
            drate_labels.index(settings["drate"])
        )

    def get_settings(self) -> dict:
        return {
            "gain": gain_labels[self.gain_selectbox.current_index()],
            "drate": drate_labels[self.sample_rate_selectbox.current_index()],
            "port": self.ports[self.COM_port_selectbox.currentIndex()],
        }

    def get_port(self) -> str:
        return self.ports[self.COM_port_selectbox.currentIndex()]

    def init_ports(self):
        self.COM_port_selectbox.clear()
        self.ports = get_available_ports()
        self.COM_port_selectbox.addItems(self.ports)

    def select_cp210x_uart_port(self) -> bool:
        if not self.ports:
            return False
        port = get_cp210x_uart_port()
        if not port:
            return False
        self.COM_port_selectbox.setCurrentIndex(self.get_port_idx(port))
        return True

    def update_button_icon(self, color):
        colored_icon = colorize_icon(self.icon, color)
        self.refresh_ports_button.setIcon(QIcon(colored_icon))

    def on_button_pressed(self):
        self.update_button_icon(QColor(os.environ.get("QTMATERIAL_SECONDARYDARKCOLOR")))

    def on_button_released(self):
        self.update_button_icon(QColor(os.environ.get("QTMATERIAL_PRIMARYCOLOR")))

    def get_port_idx(self, port: str) -> int:
        if not port:
            return 0
        return self.ports.index(port)

    def _on_refresh_ports(self):
        self.init_ports()
        self.port_refresh_callback()


class MagnetSettingsWindow(SettingsWindow):
    def __init__(self, parent=None):
        super().__init__("Magnet", parent)
        grid = QGridLayout()
        self._layout.addLayout(grid)

        self.frequency_input = LabeledNumericInput("Freq. [Hz]", 0, max_w=80)
        grid.addWidget(self.frequency_input, 0, 0)

        self.n_ramps_input = LabeledNumericInput("Ramps", 0, max_w=80)
        grid.addWidget(self.n_ramps_input, 0, 1)

        self.amplitude_input = LabeledNumericInput("Amplitude [V]", 0, max_w=80)
        grid.addWidget(self.amplitude_input, 1, 0)

        self.waveform_options = ("sine", "triangle")
        self.waveform_select = LabeledComboBox("Waveform")
        self.waveform_select.setContentsMargins(0, 0, 0, 0)
        self.waveform_select.add_items(self.waveform_options)
        grid.addWidget(self.waveform_select, 1, 1)

    def set_settings(self, settings: dict):
        self.frequency_input.value = settings["frequency"]
        self.n_ramps_input.value = settings["n_ramps"]
        self.amplitude_input.value = settings["amplitude"]
        self.waveform_select.set_current_index(
            self.waveform_options.index(settings["waveform"])
        )

    def get_settings(self) -> dict:
        return {
            "frequency": self.frequency_input.value,
            "n_ramps": self.n_ramps_input.value,
            "amplitude": self.amplitude_input.value,
            "waveform": self.waveform_options[self.waveform_select.current_index()],
        }


class OLEDSettingsWindow(SettingsWindow):
    def __init__(self, parent=None):
        super().__init__("OLED", parent)
        grid = QGridLayout()
        self._layout.addLayout(grid)

        self.powet_type_current_button = QRadioButton("Const. I")
        self.powet_type_current_button.type = "I"
        self.powet_type_current_button.toggled.connect(self._on_power_type_changed)
        self.powet_type_voltage_button = QRadioButton("Const. U")
        self.powet_type_voltage_button.type = "V"
        self.powet_type_voltage_button.toggled.connect(self._on_power_type_changed)
        self.value_input = LabeledNumericInput("V", 0, max_w=80)
        self.prep_time_input = LabeledNumericInput("Prep time [s]", 0, max_w=80)

        grid.addWidget(self.powet_type_current_button, 0, 0)
        grid.addWidget(self.powet_type_voltage_button, 0, 1)
        grid.addWidget(self.value_input, 1, 0)
        grid.addWidget(self.prep_time_input, 1, 1)

    def _on_power_type_changed(self):
        radio: QRadioButton = self.sender()
        if radio.isChecked():
            logger.info(f"Updated oled power type to {radio.type}")
            if radio.type == "I":
                self.value_input.set_label(f"I [A]")
            if radio.type == "V":
                self.value_input.set_label(f"U [V]")

    def get_settings(self):
        return {
            "power_type": self.get_power_type(),
            "v": self.value_input.value,
            "prep_time": self.prep_time_input.value,
        }

    def set_settings(self, settings):
        self.value_input.set_label(settings["power_type"])
        self.value_input.value = settings["v"]
        self.prep_time_input.value = settings["prep_time"]
        if settings["power_type"] == "I":
            self.powet_type_current_button.setChecked(True)
        elif settings["power_type"] == "V":
            self.powet_type_voltage_button.setChecked(True)

    def get_power_type(self):
        if self.powet_type_current_button.isChecked():
            return "I"
        elif self.powet_type_voltage_button.isChecked():
            return "V"


class LabeledNumericInput(QWidget):
    def __init__(self, label, value, max_w=None, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self._value = value
        self.label = InputLabel(label)

        self.input = QLineEdit(str(value))
        if max_w:
            self.input.setMaximumWidth(max_w)
        self.input.textChanged.connect(self.on_input_changed)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.input.setText(str(value))

    def on_input_changed(self):
        if self.input.text():
            self._value = float(self.input.text())

    def set_label(self, label: str):
        self.label.setText(label)


class SaveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Probe name")
        layout = QVBoxLayout()
        label = QLabel("Probe name:")
        label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        label.setAlignment(Qt.AlignCenter)
        label.setIndent(8)
        layout.addWidget(label)
        self.probeTextBox = QLineEdit()
        self.probeTextBox.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        layout.addWidget(self.probeTextBox)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_probe_name(self):
        return self.probeTextBox.text()


class CryoSettingsWindow(QDialog):
    def __init__(self, parent=None, settings: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Cryomeasurement settings")
        main_layout = QVBoxLayout()
        checkbox_widget = QFrame()
        checkbox_layout = QGridLayout(checkbox_widget)
        checkbox_widget.setObjectName("CardFrame")

        self.channel_checkboxes = []
        channel_title = QLabel("Channel:")
        channel_title.setStyleSheet(
            "font-size: 14px; margin-bottom: 2px; font-weight: bold;"
        )
        channel_title.setIndent(8)
        for i in range(8):
            checkbox = QCheckBox(f"{i+1}")
            checkbox_layout.addWidget(checkbox, i // 4 + 1, i % 4)
            self.channel_checkboxes.append(checkbox)

        checkbox_layout.addWidget(channel_title, 0, 0, 1, 4)
        main_layout.addWidget(checkbox_widget)
        main_layout.addSpacing(8)

        temperature_widget = QFrame()
        temperature_layout = QVBoxLayout(temperature_widget)
        temperature_layout.sizeHint
        temperature_widget.setObjectName("CardFrame")
        temperature_title = QLabel("Temperature [K]:")
        temperature_title.setStyleSheet(
            "font-size: 14px; margin-bottom: 2px; font-weight: bold;"
        )
        temperature_title.setIndent(8)
        temperature_layout.addWidget(temperature_title)
        self.manual_temp_checkbox = QCheckBox("Manual")
        self.manual_temp_checkbox.toggled.connect(self._on_manual_temp_changed)
        self.manual_temp_checkbox.setStyleSheet("margin-left: 10px;")
        temperature_layout.addWidget(self.manual_temp_checkbox)
        temp_input_layout = QHBoxLayout()
        self.start_input = LabeledNumericInput("Start", 0, max_w=60)
        self.stop_input = LabeledNumericInput("Stop", 0, max_w=60)
        self.step_input = LabeledNumericInput("Step", 0, max_w=60)
        temp_input_layout.addWidget(self.start_input)
        temp_input_layout.addWidget(self.stop_input)
        temp_input_layout.addWidget(self.step_input)
        temperature_layout.addLayout(temp_input_layout)
        temperature_layout.addStretch()
        main_layout.addWidget(temperature_widget)

        self.buttonBox = QDialogButtonBox()
        accept_button = QPushButton("OK")
        accept_button.setProperty("class", "action")
        accept_button.clicked.connect(self.accept)
        reject_button = QPushButton("Cancel")
        reject_button.setProperty("class", "danger")
        reject_button.clicked.connect(self.reject)
        self.buttonBox.addButton(accept_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttonBox.addButton(reject_button, QDialogButtonBox.ButtonRole.RejectRole)
        main_layout.addWidget(self.buttonBox)

        self.setLayout(main_layout)
        if settings:
            self.set_selected_channels(settings["channel"])
            self.set_temp_settings(settings["temp"])
        self.resize(250, 300)

    def set_selected_channels(self, channels):
        for i, checkbox in enumerate(
            self.channel_checkboxes, start=1
        ):  # start=1 for enumeration from 1
            checkbox.setChecked(i in channels)

    def set_temp_settings(self, settings):
        self.start_input.value = settings["start"]
        self.stop_input.value = settings["stop"]
        self.step_input.value = settings["step"]
        self.manual_temp_checkbox.setChecked(settings["manual"])

    def get_selected_channels(self):
        return [
            i
            for i, checkbox in enumerate(self.channel_checkboxes, start=1)
            if checkbox.isChecked()
        ]

    def set_settings(self, settings):
        self.set_selected_channels(settings["channel"])
        self.set_temp_settings(settings["temp"])

    def get_settings(self):
        return {
            "channel": self.get_selected_channels(),
            "temp": self.get_temp_settings(),
        }

    def get_temp_settings(self):
        return {
            "manual": self.manual_temp_checkbox.isChecked(),
            "start": self.start_input.value,
            "stop": self.stop_input.value,
            "step": self.step_input.value,
        }

    def _on_manual_temp_changed(self):
        if self.manual_temp_checkbox.isChecked():
            self.start_input.setVisible(False)
            self.stop_input.setVisible(False)
            self.step_input.setVisible(False)
        else:
            self.start_input.setVisible(True)
            self.stop_input.setVisible(True)
            self.step_input.setVisible(True)
