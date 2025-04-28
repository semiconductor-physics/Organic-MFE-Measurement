import logging
logger = logging.getLogger(__name__)

class DummyCryo:
    def __init__(self, adapter):
        self.adapter = adapter
        self._heater = 0
        self._heater_gas_mode = 'MANUAL'
        self._control_mode = 'RU'
        self._temperature_1 = 0
        self._temperature_2 = 0
        self._temperature_3 = 0
        self._temperature_error = 0
        self._temperature_setpoint = 0
        
    
    @property
    def control_mode(self):
        return self._control_mode

    @control_mode.setter
    def control_mode(self, mode: str):
        self._control_mode = mode
        logger.debug(f'control mode: {mode}')

    @property
    def temperature_1(self):
        return self._temperature_1
    
    @temperature_1.setter
    def temperature_1(self, temperature: float):
        self._temperature_1 = temperature
        logger.debug(f'temperature_1: {temperature}')

    @property
    def temperature_2(self):
        return self._temperature_2
    
    @temperature_2.setter
    def temperature_2(self, temperature: float):
        self._temperature_2 = temperature
        logger.debug(f'temperature_2: {temperature}')
        
    @property
    def temperature_3(self):
        return self._temperature_3
    
    @temperature_3.setter
    def temperature_3(self, temperature: float):
        self._temperature_3 = temperature
        logger.debug(f'temperature_3: {temperature}')
    
    @property
    def temperature_error(self):
        return self._temperature_error
    
    @property
    def temperature_setpoint(self):
        return self._temperature_setpoint
    
    @temperature_setpoint.setter
    def temperature_setpoint(self, temperature: float):
        self._temperature_setpoint = temperature
        logger.debug(f'temperature_setpoint: {temperature}')
    
    def wait_for_temperature(self, error=0.01, timeout=3600, check_interval=0.5, stability_interval=10, thermalize_interval=300, should_stop=lambda: False):
        pass

    @property
    def heater(self):
        return self._heater
    
    @heater.setter
    def heater(self, heater: float):
        self._heater = heater
        logger.debug(f'heater: {heater}')

    @property
    def heater_gas_mode(self):
        return self._heater_gas_mode
    
    @heater_gas_mode.setter
    def heater_gas_mode(self, mode: str):
        self._heater_gas_mode = mode
        logger.debug(f'heater_gas_mode: {mode}')