import struct
import serial
import threading
import logging
from typing import Callable
from time import sleep
import random

logger = logging.getLogger(__name__)
DeviceListener = Callable[[list[tuple[float, float, float, float]]], None]

class Device:
    DEFAULTS = {
        "write_termination": "\r\n",
        "read_termination": "\r\n",
        "encoding": "ascii",
        "baudrate": 250000,
        "read_timeout": 0.5,
        "write_timeout": 0.5,
    }

    def __init__(self, port: str):
        self.port = port
        self.rsc = None
        self.streaming = False
        self.listeners = []
        self.stream_buffer = bytearray()

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
        self.set_debug(False)
        logger.debug("Device::initialize before reset")
        self.reset()
        logger.debug("Device::initialize after reset")

    def query(self, message: str) -> str:
        if not self.rsc:
            logger.warning("Serial not initialized")
            return ""
        self.writeMessage(message)
        ans = self.rsc.readline()
        ans = ans.decode(self.DEFAULTS["encoding"]).strip()
        logger.debug(f"{message=}; {ans=}")
        return ans

    def writeMessage(self, message):
        if not self.rsc:
            logger.warning("Serial not initialized")
            return
        message = message + self.DEFAULTS["write_termination"]
        message = message.encode(self.DEFAULTS["encoding"])
        self.rsc.write(message)

    def set_debug(self, debug: bool):
        message = f"SET DEBUG {int(debug)}"
        self.writeMessage(message)

    def set_gain(self, gain: str):
        msg = f"SET GAIN {gain}"
        self.writeMessage(msg)

    def set_rate(self, sps: str):
        msg = f"SET DRATE {sps}"
        self.writeMessage(msg)

    def idn(self):
        return self.query("IDN")

    def reset(self) -> None:
        logger.debug("reset")
        self.writeMessage("RST")

    def get_analog_input(self, channel):
        message = f"IN {channel}"
        ans = self.query(message)
        return float(ans)

    def add_listener(self, listener: DeviceListener) -> None:
        self.listeners.append(listener)

    def remove_listener(self, listener: DeviceListener) -> None:
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass

    def notify_listeners(self, values: list[tuple[float, float, float, float]]):
        for listener in self.listeners:
            listener(values)

    def stream(self):
        if not self.rsc:
            logger.warn("Serial not initialized")
            return
        while self.streaming:
            bytes_in_serial = self.rsc.in_waiting
            if not bytes_in_serial:
                continue
            self.stream_buffer += self.rsc.read(bytes_in_serial)
            n_bytes_package = 4*4 # 4 floats with 4 bytes each
            n_complete_vals = len(self.stream_buffer) // (n_bytes_package) 
            adc_values: list[tuple[float, float, float, float]] = []
            for _ in range(n_complete_vals):
                val_tuple = struct.unpack_from("ffff", self.stream_buffer[:n_bytes_package])
                adc_values.append(val_tuple)
                del self.stream_buffer[:n_bytes_package]
            self.notify_listeners(adc_values)

    def start_stream(self):
        if not self.rsc:
            logger.warning("Serial not initialized")
            return
        logger.info("Start Stream on Device")
        self.rsc.flush()
        self.rsc.reset_output_buffer()
        self.rsc.reset_input_buffer()
        self.writeMessage("START")
        self.streaming = True
        self.stream_buffer = bytearray()
        thread = threading.Thread(target=self.stream)
        thread.start()

    def get_true_samplerate(self, sample_time=5):
        self.start_stream()
        sleep(sample_time)
        self.stop_stream()
        rate_string = self.query('INFO')
        rate = float(rate_string)
        sample_rate_per_channel = rate / 4 #using 4 channel
        logger.info(f'samplerate per channel {sample_rate_per_channel}')
        return sample_rate_per_channel
    
    def stop_stream(self):
        if not self.rsc:
            logger.warning("Serial not initialized")
            return
        message = "STOP"
        self.writeMessage(message)
        self.streaming = False
        self.rsc.reset_input_buffer()

    def finalize(self):
        if not isinstance(self.rsc, serial.Serial):
            return
        self.set_debug(False)
        if self.rsc.is_open == True:
            self.rsc.close()

class DummyDevice:
    DEFAULTS = {
        "write_termination": "\r\n",
        "read_termination": "\r\n",
        "encoding": "ascii",
        "baudrate": 250000,
        "read_timeout": 0.5,
        "write_timeout": 0.5,
    }

    def __init__(self, port: str):
        self.port = port
        self.rsc = None
        self.streaming = False
        self.listeners = []
        self.stream_buffer = bytearray()

    def initialize(self):
        logger.debug(f"Initializing device on port {self.port} with defaults: {self.DEFAULTS}")

    def query(self, message: str) -> str:
        logger.debug(f"Querying device with message: {message}")
        return "Dummy response"

    def writeMessage(self, message):
        logger.debug(f"Writing message to device: {message}")

    def set_debug(self, debug: bool):
        logger.debug(f"Setting debug mode to: {debug}")

    def set_gain(self, gain: str):
        logger.debug(f"Setting gain to: {gain}")

    def set_rate(self, sps: str):
        logger.debug(f"Setting data rate to: {sps}")

    def idn(self):
        logger.debug("Fetching device ID")
        return "DummyDevice v1.0"

    def reset(self) -> None:
        logger.debug("Resetting device")

    def get_analog_input(self, channel):
        logger.debug(f"Getting analog input for channel: {channel}")
        return 0.0

    def add_listener(self, listener):
        logger.debug("Adding listener")
        self.listeners.append(listener)

    def remove_listener(self, listener):
        try:
            self.listeners.remove(listener)
            logger.debug("Removed listener")
        except ValueError:
            logger.debug("Listener not found")

    def notify_listeners(self, values: list[tuple[float, float, float, float]]):
        for listener in self.listeners:
            listener(values)
        

    def stream(self):
        logger.debug("Starting dummy stream loop")
        while self.streaming:
            num_tuples = random.randint(1, 10)  # Random amount of tuples
            dummy_values = [
                (random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100))
                for _ in range(num_tuples)
            ]
            self.notify_listeners(dummy_values)
            sleep(1/100)

    def start_stream(self):
        logger.debug("Starting stream")
        self.streaming = True
        thread = threading.Thread(target=self.stream)
        thread.start()

    def stop_stream(self):
        logger.debug("Stopping stream")
        message = "STOP"
        self.writeMessage(message)
        self.streaming = False

    def get_true_samplerate(self, sample_time=5):
        logger.debug(f"Calculating true sample rate over {sample_time} seconds")
        return 1000.0  # Dummy sample rate

    def finalize(self):
        logger.debug("Finalizing device and closing resources")