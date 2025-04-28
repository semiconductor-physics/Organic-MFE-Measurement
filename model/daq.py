from config.config import DEBUG
if DEBUG:
    from controllers.Dietrich import DummyDevice as Device
else: 
    from controllers.Dietrich import Device
from typing import Callable
import serial
import serial.tools.list_ports
import logging
logger = logging.getLogger(__name__)


DeviceListener = Callable[[list[tuple[float, float, float]]], None]

GAIN_CODES = {
    '1x': '0',
    '2x': '1',
    '4x': '2',
    '8x': '3',
    '16x': '4',
    '32x': '5',
    '64x': '6',
}

DRATE_CODES = {
    '2.5': '3',
    '5': '19',
    '10': '35',
    '15': '51',
    '25': '67',
    '30': '83',
    '50': '99',
    '60': '114',
    '100': '130',
    '500': '146',
    '1000': '161',
    '2000': '176',
    '3750': '192',
    '7500': '208',
    '15000': '224',
    '25000': '240',
}

def get_cp210x_uart_port() -> str:
        if DEBUG:
            return 'COM1'
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports):
            if p.vid == 4292 and p.pid == 60000: # vid and pid for cp210x uart bridge
                logger.info(f'Found cp210x uart bridge at {p.device}')
                return p.device
        else:
            logger.warning(f'Did not find cp210x uart bridge')
            return ''
    

def get_available_ports() -> list[str]:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in sorted(ports)]

class AnalogDaq:
    def __init__(self, port):
        self.port = port
        self.driver = Device(self.port)

    def initialize(self):
        self.driver.initialize()

    def getIDN(self):
        return self.driver.idn()

    def resetDevice(self):
        self.driver.reset()

    def setParamters(self, gain: str, sampling_rate: str):
        self.driver.set_gain(gain)
        self.driver.set_rate(sampling_rate)

    def add_stream_listener(self, listener: DeviceListener):
        self.driver.add_listener(listener)

    def remove_stream_listener(self, listener: DeviceListener):
        self.driver.remove_listener(listener)

    def start_stream(self):
        self.driver.start_stream()

    def stop_stream(self):
        self.driver.stop_stream()

    def finalize(self):
        self.driver.finalize()