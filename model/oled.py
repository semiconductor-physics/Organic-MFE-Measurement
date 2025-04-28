import logging
logger = logging.getLogger(__name__)
from config.config import DEBUG
if DEBUG:
    from controllers.Keithley_smu import DummyKeithley_smu as Keithley_smu
else:
    from controllers.Keithley_smu import Keithley_smu

from enum import Enum

class OutputMode(Enum):
    """
    VOLTAGE
    CURRENT
    """
    CURRENT = 0
    VOLTAGE = 1
    


class Oled:
    def __init__(self, smu_address = None) -> None:
        self.smu = Keithley_smu(address=smu_address)
        self.smu.initKeithley()
        self._voltage = 0
        self._current = 0
        logger.info('init led')
        self._mode = OutputMode.VOLTAGE

    @property
    def voltage(self):
        return self._voltage
    
    @voltage.setter
    def voltage(self, value):
        if self._mode != OutputMode.VOLTAGE:
            self.smu.init_voltage()
            self._mode = OutputMode.VOLTAGE
        self.smu.set_voltage(value)
        self._voltage = value

    @property
    def current(self):
        return self._current
    
    @current.setter
    def current(self, value):
        if self._mode != OutputMode.CURRENT:
            self.smu.init_current()
            self._mode = OutputMode.CURRENT
        self.smu.set_current(value)
        self._current = value

    def turn_on(self):
        self.smu.turn_on()

    def turn_off(self):
        self.smu.turn_off()