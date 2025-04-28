from config.config import DEBUG
if DEBUG:
    from controllers.EA_PSU import DummyEA_PSU as EA_PSU
    from controllers.MagnetRelay import DummyRelay as Relay
else:
    from controllers.EA_PSU import EA_PSU
    from controllers.MagnetRelay import Relay

import numpy as np
from time import sleep
import logging

logger = logging.getLogger(__name__)


class MagnetController:
    def __init__(self, psu_address = None) -> None:
        self.psu = EA_PSU(psu_address)
        self.relay = Relay()
        self._is_on = False
        logger.info('Magnet controller init')
    
    @property
    def is_on(self) -> bool:
        return self._is_on

    def _turn_on(self):
        if self._is_on:
            return
        self.psu.Volt_mode()
        self.psu.turn_on()
        self._is_on = True

    def _turn_off(self):
        if self._is_on == False:
            return 
        self.psu.set_voltage(0)
        self.psu.turn_off()
        self.relay.set_zero()
        self._is_on = False

    def set_voltage(self, voltage):
        if voltage < 0:
            self.relay.set_negative()
        elif voltage > 0:
            self.relay.set_positive()
        sleep(0.1)
        self.psu.set_voltage(voltage)

    def ramp(self, start_v: float, stop_v: float, step_size: float, step_time: float, pause_at_zero: None | float = None) -> None:
        eps = 0.00002
        if start_v < 0:
            self.relay.set_negative()
        else:
            self.relay.set_positive()
        if stop_v < start_v:
            step_size = -1* step_size
        for current_v in np.arange(start_v, stop_v+step_size, step_size):
            if self.is_on == False:
                return
            if (current_v - eps) < 0 and (current_v + eps) > 0:
                if pause_at_zero:
                    sleep(pause_at_zero)
                if stop_v > 0:
                    self.relay.set_positive()
                else:
                    self.relay.set_negative()
            self.psu.set_voltage(current_v)
            sleep(step_time)
            
    
    def triangle_wave(self, min_v, max_v, period, step_size=1, n_periods= 1):
        self._turn_on()
        step_time = (period * step_size) / (2 *abs(max_v-min_v))
        for _ in range(n_periods):
            self.ramp(min_v, max_v, step_size, step_time=step_time)
            self.ramp(max_v, min_v, -step_size, step_time=step_time)
        self._turn_off()

    def finalize(self):
        if self.is_on:
            self._turn_off()
