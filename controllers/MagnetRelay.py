import serial
import logging

logger = logging.getLogger(__name__)

class Relay:
    def __init__(self, address=None):
        if address is None:
            address = 'COM3'
        try:
            logger.debug('Connecting with Arduino...')
            self.__Arduino = serial.Serial(port=address, baudrate=9600, timeout=0.1)
        except Exception as e:
            logger.error(f"Could not connect: {e}")

    def write(self, data):
        self.__Arduino.write(data)

    def query(self, data):
        self.__Arduino.write(data)
        return self.__Arduino.readline()

    def set_negative(self):
        self.write(b"U")

    def set_positive(self):
        self.write(b"E")

    def set_zero(self):
        self.write(b"S")


class DummyRelay:
    def __init__(self, address=None):
        if address is None:
            address = 'COM3'
        logger.debug(f'Connecting with Arduino at {address}...')

    def write(self, data):
        logger.debug(f'Arduino <<< {data}') 

    def query(self, data):
        logger.debug(f'Arduino >>> {data}')
        return 'U'

    def set_negative(self):
        self.write(b"U")

    def set_positive(self):
        self.write(b"E")

    def set_zero(self):
        self.write(b"S")