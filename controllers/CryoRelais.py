import numpy as np
import serial
import logging
from typing import Callable
from time import sleep

logger = logging.getLogger(__name__)
DeviceListener = Callable[[list[tuple[float, float, float, float]]], None]

class CryoRelais:
    DEFAULTS = {
        "write_termination": "\r",
        "read_termination": "\r",
        "encoding": "utf-8",
        "baudrate": 1200,
        "read_timeout": 0.5,
        "write_timeout": 0.5,
    }

    def __init__(self, port: str):
        self.port = port
        self.rsc = None
        self._channel = None
        self._measure_mode = None

    @property
    def measure_mode(self):
        return self._measure_mode
    
    @measure_mode.setter
    def measure_mode(self, mode: str):
        logger.info(f'setting measure mode to {mode}')
        self.write_message(str(mode))
        self._measure_mode = mode
        sleep(0.5)   

    @property
    def channel(self):
        return self._channel
    
    @channel.setter
    def channel(self, channel: int):
        logger.info(f'setting channel to {channel}')
        self.write_message(str(channel))
        self._channel = channel
        sleep(0.5)

    def initialize(self):
        self.rsc = serial.Serial(
            port=self.port,
            baudrate=self.DEFAULTS["baudrate"],
            timeout=self.DEFAULTS["read_timeout"],
            write_timeout=self.DEFAULTS["write_timeout"],
        )
        sleep(0.5)  # on reset it may take some while for the ESP32 to wake up
        while self.rsc.in_waiting > 0:
            self.rsc.read_all()

    def query(self, message: str) -> str:
        if not self.rsc:
            logger.warn("Serial not initialized")
            return ""
        self.write_message(message)
        ans = self.rsc.readline()
        ans = ans.decode(self.DEFAULTS["encoding"]).strip()
        logger.debug(f"{message=}; {ans=}")
        return ans

    def write_message(self, message):
        if not self.rsc:
            logger.warn("Serial not initialized")
            return
        message = message + self.DEFAULTS["write_termination"]
        logger.debug(f'cryo relay <<< {message}')
        print(f'cryo relay <<< {message}')
        message = message.encode(self.DEFAULTS["encoding"])
        self.rsc.write(message)

    def finalize(self):
        if not isinstance(self.rsc, serial.Serial):
            return
        if self.rsc.is_open == True:
            self.rsc.close()


class DummyCryoRelais:
    DEFAULTS = {
        "write_termination": "\r",
        "read_termination": "\r",
        "encoding": "utf-8",
        "baudrate": 1200,
        "read_timeout": 0.5,
        "write_timeout": 0.5,
    }

    def __init__(self, port: str):
        self.port = port
        self.rsc = None
        self._channel = None
        self._measure_mode = None

    @property
    def measure_mode(self):
        return self._measure_mode

    @measure_mode.setter
    def measure_mode(self, mode: str):
        logger.debug(f"Setting measure mode to {mode}")
        self.write_message(f"SET MODE {mode}")
        self._measure_mode = mode
        sleep(0.5)

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel: int):
        logger.debug(f"Setting channel to {channel}")
        self.write_message(f"SET CHANNEL {channel}")
        self._channel = channel
        sleep(0.5)

    def initialize(self):
        logger.debug(f"Initializing CryoRelais on port {self.port} with defaults: {self.DEFAULTS}")
        sleep(0.5)

    def query(self, message: str) -> str:
        logger.debug(f"Querying CryoRelais with message: {message}")
        return "Dummy response"

    def write_message(self, message: str):
        message = message + self.DEFAULTS["write_termination"]
        logger.debug(f"CryoRelais <<< {message}")

    def finalize(self):
        logger.debug("Finalizing CryoRelais and closing resources")


if __name__ == '__main__':
    box = CryoRelais('COM14')
    box.initialize() 
    box.measure_mode = "V"

    channel_wait_time = 0.5
    for i in [0,1,2,3,4,5,6,7]:
        box.channel = i
        sleep(channel_wait_time)
