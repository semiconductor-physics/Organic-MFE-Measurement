from config.config import CONFIG_FILE, DEBUG
import typing
import numpy as np
import yaml
import os
import csv
from model.daq import AnalogDaq
from model.oled import Oled
from time import sleep
from utils.save_utils import create_dir, save_config_file, create_date_dir
from enum import Enum
from abc import ABC
from model.daq import GAIN_CODES, DRATE_CODES

if DEBUG:
    from controllers.CryoRelais import DummyCryoRelais as CryoRelais
    from controllers.fx_gen import DummyFxgen as Fxgen
    from controllers.Cryo import DummyCryo as Cryo
else:
    from controllers.CryoRelais import CryoRelais
    from controllers.fx_gen import Fxgen
    from pymeasure.instruments.oxfordinstruments import ITC503 as Cryo
    from controllers.Keithley_2010 import Keithley_2010

import logging
logger = logging.getLogger(__name__)


def hall_to_B(v_hall):
    return 2.545442 - 1108.27859 * v_hall

# def T_cryo_to_T_sample(T_cryo):
#     return 5.26277 + 0.99971 * T_cryo

class AbstractDataStore(ABC):
    def __init__(self, power_type: str = 'V'):
        self.V_hall_list = []
        self.magnet_B_list = []
        self.oled_list = []
        self.I_photo_list = []
        self.power_type = power_type
        self.plot_idx = 0

    def listen(self, stream_data_list: list[tuple[float, float, float, float]]) -> None:
        raise NotImplementedError
    
    def to_file(self, dir_path: str):
        raise NotImplementedError

    def reset_plot(self):
        if self.V_hall_list:
            self.plot_idx = len(self.V_hall_list)-1

class DataStore(AbstractDataStore):
    def __init__(self, power_type):
        logger.info(f'init data store with {power_type}')
        super().__init__(power_type)
        self.stages = {}

    def listen(self, stream_data_list: list[tuple[float, float, float, float]]) -> None:
        for stream_data in stream_data_list:
            self.V_hall_list.append(stream_data[0])
            self.magnet_B_list.append(hall_to_B(stream_data[0]))
            self.I_photo_list.append(stream_data[2])
            if self.power_type == 'V':
                self.oled_list.append(stream_data[1])
            elif self.power_type == 'I':
                self.oled_list.append(stream_data[3])
            else:
                logger.warn('Power type not defined')

    def to_file(self, dir_path: str):
        file_path = os.path.join(dir_path, f'data.csv')
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ['V_Hall', 'B', 'OLED', 'I_Photo',]
            writer.writerow(header)
            writer.writerows(zip(self.V_hall_list, self.magnet_B_list, self.oled_list, self.I_photo_list))
        
class CryoDataStore(AbstractDataStore):
    def __init__(self, power_type):
        super().__init__(power_type)
        self.temp = None
        self.temp_sample = None
        self.current_channel: int | None = None
        self.temp_list = []
        self.temp_sample_list = []
        self.channel_list = []

    def listen(self, stream_data_list: list[tuple[float, float, float, float]]) -> None:
        for stream_data in stream_data_list:
            self.V_hall_list.append(stream_data[0])
            self.magnet_B_list.append(hall_to_B(stream_data[0]))
            self.I_photo_list.append(stream_data[2])
            if self.power_type == 'V':
                self.oled_list.append(stream_data[1])
            elif self.power_type == 'I':
                self.oled_list.append(stream_data[3])
            self.channel_list.append(self.current_channel)
            self.temp_list.append(self.temp)
            self.temp_sample_list.append(self.temp_sample)
    
    def to_file(self, dir_path: str):
        file_path = os.path.join(dir_path, f'data.csv')
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ['V_Hall', 'B', 'OLED', 'I_Photo', 'Channel', 'Temp', 'Temp_sample']
            writer.writerow(header)
            writer.writerows(zip(self.V_hall_list, self.magnet_B_list, self.oled_list, self.I_photo_list, self.channel_list, self.temp_list, self.temp_sample_list))

class MeasureMode(Enum):
    """
    VOLTAGE: measure voltage datastream[3]); const. current
    CURRENT: measure current through transimpedance datastream[1]); const. voltage
    """
    VOLTAGE = 0
    CURRENT = 1

class Experiment:
    def __init__(self, config_file: str):
        # read yaml configuration file
        self.read_config(config_file)
        self.power_type = self.config['OLED']['power_type']
        self.data_store = DataStore(self.power_type)
        self.stages = {}
        self.magnet = None
        self.oled = None
        self.cryo = None
        self.pt100 = None
        self.cryo_relais = None
        self.daq = None
        self.running = False
        self.progress = 0
        self.finish_callback: typing.Callable | None = None
        self.progress_callback: typing.Callable | None = None

    def read_config(self, path: str):
        with open(path, 'r') as file:
            self.config = yaml.safe_load(file)
        self.gain_code = GAIN_CODES[self.config['ADC']['gain']]
        self.drate_code = DRATE_CODES[self.config['ADC']['drate']]

    def set_adc_settings(self):
        logger.info('Setting adc parameters')
        self.daq.setParamters(self.gain_code, self.drate_code)

    def power_oled(self, settings, wait: bool = True):
        if not self.oled:
            self.oled = Oled()
        if settings['power_type'] == 'I':
            self.oled.current = settings['v']
        elif settings['power_type'] == 'V':
            self.oled.voltage = settings['v']
        self.oled.turn_on()
        if wait:
            self.wait(settings['prep_time'])

    def init_cryo_system(self, manual_mode = False):
        """Initializes the cryo and cryo relais system."""
        self.init_cryo(manual_mode)
        self.init_cryo_relais()

    def init_cryo(self, manual_mode = False):
        if self.cryo:
            return
        self.cryo = Cryo('GPIB0::24::INSTR')
        self.cryo.control_mode = "RU"      
        if manual_mode:
            self.cryo.heater_gas_mode = "MANUAL"
            self.cryo.heater = 0
        else:
           # Set the control mode to remote
            self.cryo.heater_gas_mode = "AUTO"    # Turn on auto heater and flow
            self.cryo.auto_pid = True

    def init_cryo_relais(self):
        if self.cryo_relais:
            return
        self.cryo_relais = CryoRelais('COM14')
        self.cryo_relais.initialize()
    
    def init_pt100(self):
        self.pt100 = Keithley_2010()
        self.pt100.init_meas()

    def cryo_routine(self, settings):
        logger.info('Cryo routine started')
        self.data_store = CryoDataStore(self.power_type)
        manual_temp_mode = settings['temp']['manual']
        self.init_cryo_system(manual_temp_mode)
        self.init_pt100()
        assert isinstance(self.cryo, Cryo)
        assert isinstance(self.cryo_relais, CryoRelais)
        if not manual_temp_mode:
            start_temp = settings['temp']['start']
            stop_temp = settings['temp']['stop']
            step_temp = settings['temp']['step']
            temperatures = np.arange(start_temp, stop_temp+step_temp, step_temp)
            self.measure_temperture_ramp(temperatures, settings['channel'])
        else:
            self.array_measurement(settings['channel'])

    def set_temperature(self, temperature: float):
        logger.info(f'Setting cryo temp to: {temperature}')
        self.cryo.temperature_setpoint = temperature
        current_temp = self.cryo.temperature_1
        if current_temp > temperature: # type: ignore
            logger.error(f'Temperature {temperature} cannot be reached. Current temperature: {current_temp}K')
            return
        self.cryo.wait_for_temperature(error=0.1, check_interval=0.2, stability_interval=1, thermalize_interval=300)
        logger.info(f'Setpoint Temperature {temperature} K reached')

    def meas_pt100(self):
        logger.info(f'Measure the pt100 temperature: {self.pt100.ask_temp()}')
        return self.pt100.ask_temp()

    def resistance_to_sample(self, resistance):
        return 13.86702 + 2.3034*resistance + 0.00116*resistance**2 #resistance to T_sample (K) with cable resistance correction

    def array_measurement(self, channels: list[int]):
        current_temp = self.cryo.temperature_1
        current_sample_temp = self.resistance_to_sample(self.meas_pt100())
        current_sample_temp = round(current_sample_temp, 3) #roundn to three digits
        self.data_store.temp = current_temp # type: ignore
        self.data_store.temp_sample = current_sample_temp
        logger.info(f'Current temperature at the cryo position: {current_temp}K')
        logger.info(f'Current temperature at the sample position: {current_sample_temp}K')
        for channel in channels:
            if not self.running:
                break
            self.data_store.current_channel = channel
            logger.info(f'switching to cryo channel {channel}')
            self.cryo_relais.measure_mode = self.power_type
            self.cryo_relais.channel = channel
            self.data_store.reset_plot()
            self.measure()

    def measure_temperture_ramp(self, temperatures: list[float], channels: list[int]):
        for temp in temperatures:
            if not self.running:
                break
            self.set_temperature(temp)
            self.array_measurement(channels)

    def wait(self, seconds: float, check_interval: float = 0.1):
        """sleep function which can be aborted"""
        t = 0.
        while self.running and t < seconds:
            sleep(check_interval)
            t += check_interval
        self.progress += seconds
        if self.progress_callback:
            self.progress_callback(self.progress/self.total_progress) 

    def measure(self):
        self.power_oled(self.config['OLED'], wait=True)
        self.wait(1)
        self.start_stream(self.data_store.listen)
        self.magnet.turn_on()
        self.wait_n_ramps()
        self.stop_stream(self.data_store.listen)
        self.oled.turn_off()
        self.wait(1)

    def standard_routine(self):
        logger.info('Standard routine started')
        self.data_store = DataStore(self.config['OLED']['power_type'])
        self.measure()

    def run_experiment(self):
        logger.info("Running experiment")
        self.running = True
        self.read_config(CONFIG_FILE)
        self.progress = 0
        self.total_progress = self.calc_total_time()
        logger.info('Initializing magnet')
        self.set_magnet_settings(self.config['Magnet'])
        logger.info('Initializing oled')
        self.power_type = self.config['OLED']['power_type']
        
        if self.config['Cryo']['enabled']:
            self.cryo_routine(self.config['Cryo'])
        else:
            self.standard_routine()
        self.finalize()
        if self.finish_callback:
            self.finish_callback()
        logger.info('Experiment finished')

    def debug_stream(self, listener) -> None:
        channel = None
        self.data_store.reset_plot()
        if self.config['Cryo']['enabled']:
            self.init_cryo_relais()
            assert isinstance(self.cryo_relais, CryoRelais)
            channel = self.config['Cryo']['channel'][0]
            self.cryo_relais.channel = channel
        self.start_stream(listener)

    def start_stream(self, listener) -> None:
        self.set_adc_settings()
        self.daq.add_stream_listener(listener)
        logger.info('starting Stream')
        self.daq.start_stream()

    def stop_stream(self, listener) -> None:
        logger.info('stopping stream')
        if self.daq:
            self.daq.stop_stream()
            self.daq.remove_stream_listener(listener) 

    def wait_n_ramps(self):
        f = self.magnet.frequency
        sleep_time = self.config['Magnet']['n_ramps']/f 
        self.wait(sleep_time)

    def save(self, path: str, probe_name: str):
        date_dir_path = create_date_dir(path)
        experiment_dir = create_dir(date_dir_path, probe_name)
        self.data_store.to_file(experiment_dir)
        save_config_file(experiment_dir)

    def load_daq(self, port: str) -> str:
        self.daq = AnalogDaq(port)
        self.daq.initialize()
        return self.daq.getIDN()

    def daq_setparameters(self):
        self.daq.setParamters(self.gain_code, self.drate_code)

    def set_magnet_settings(self, settings):
        if not self.magnet:
            self.magnet = Fxgen()
        freq = settings['frequency']
        amp = settings['amplitude']
        waveform = settings['waveform']
        self.magnet.set_timing_params(freq)
        self.magnet.set_amplitude(amp)
        self.magnet.set_waveform(waveform)
        
    def turn_off_heater(self):
        if self.cryo:
            self.cryo.heater_gas_mode = "MANUAL"
            self.cryo.heater = 0
    
    def finalize(self):
        if self.magnet:
            self.magnet.turn_off()
        if self.oled:
            self.oled.turn_off()
        self.turn_off_heater()


    def calc_total_time(self):
        total_time = 0
        ramp_time = self.config['Magnet']['n_ramps']/self.config['Magnet']['frequency'] + 2
        if self.config['Cryo']['enabled']:
            if self.config['Cryo']['temp']['manual']:
                for _ in self.config['Cryo']['channel']:
                    total_time += ramp_time
            else:
                start_temp = self.config['Cryo']['temp']['start']
                stop_temp = self.config['Cryo']['temp']['stop']
                step_temp = self.config['Cryo']['temp']['step']
                temperatures = np.arange(start_temp, stop_temp+step_temp, step_temp)
                for _ in temperatures:
                    for _ in self.config['Cryo']['channel']:
                        total_time += ramp_time
        else:
            total_time += ramp_time
        return total_time