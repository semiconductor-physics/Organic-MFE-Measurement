import pyvisa
import logging

logger = logging.getLogger(__name__)

class Fxgen: 
    def __init__(self, adr: str= "GPIB0::16") -> None:
        rm = pyvisa.ResourceManager()
        self.device = rm.open_resource(adr)
        self.wave_form = None
        self.amplitude = None
        self.start_phase = None
        self.frequency = 1
        self.duty_cyle = None

    def turn_on(self):
        self.device.write('D0') # TURN ON THE FX GENERATOR OUTPUT

    def turn_off(self):
        self.device.write('D1') # TURN OFF THE FX GENERATOR OUTPUT

    def set_waveform(self, waveform: str = 'sine', start_phase: str= 'sin'):
        if waveform == 'sine':
            wf = 'W1'
        if waveform == 'triangle':
            wf = 'W2'
        if waveform == 'square':
            wf = 'W3'
        if waveform == 'puls':
            wf = 'W4'
        if waveform == 'dc':
            wf = 'W0'
        phase = 'H0'
        if start_phase == 'cos':
            phase = 'H1'
        
        if waveform not in  ['sine', 'triangle', 'square', 'puls', 'dc']:
            raise
        if start_phase not in ('sin', 'cos'):
            raise
        
        self.device.write(f'{wf},{phase}')
        self.wave_form = waveform
        self.start_phase = start_phase

    def set_timing_params(self, f: float, duty_cycle: int=50):
        f_unit = 'HZ'
        frequency = f
        if f > 100000:
           f /= 100000
           f_unit = 'MHZ'
        elif f > 1000:
           f /= 1000
           f_unit = 'KHZ'
        elif f >= 1:
           pass
        else:
            f *= 1000
            f_unit = 'MZ'
        if duty_cycle > 100 or duty_cycle < 0:
            raise
        
        self.device.write(f'FRQ {f} {f_unit}, DTY {duty_cycle} %')
        self.frequency = frequency
        self.duty_cyle = duty_cycle

    def set_amplitude(self, amp: float):
        amp_unit = 'V'
        amplitude = amp
        if amp < 1:
            amp *= 1000
            amp_unit ='MV'
        self.device.write(f'AMP {amp} {amp_unit}')
        self.amplitude = amplitude

class DummyFxgen: 
    def __init__(self, adr: str= "GPIB0::16") -> None:
        self.wave_form = None
        self.amplitude = None
        self.start_phase = None
        self.frequency = 1
        self.duty_cyle = None

    def turn_on(self):
        logger.debug('turning on fx generator')

    def turn_off(self):
        logger.debug('turning off fx generator')

    def set_waveform(self, waveform: str = 'sine', start_phase: str= 'sin'):
        logger.debug(f'setting waveform to {waveform} with start phase {start_phase}')
        self.wave_form = waveform
        self.start_phase = start_phase

    def set_timing_params(self, f: float, duty_cycle: int=50):
        f_unit = 'HZ'
        frequency = f
        if f > 100000:
           f /= 100000
           f_unit = 'MHZ'
        elif f > 1000:
           f /= 1000
           f_unit = 'KHZ'
        elif f >= 1:
           pass
        else:
            f *= 1000
            f_unit = 'MZ'
        if duty_cycle > 100 or duty_cycle < 0:
            raise
        logger.debug(f'setting frequency to {f} {f_unit} and duty cycle to {duty_cycle}')
        self.frequency = frequency
        self.duty_cyle = duty_cycle

    def set_amplitude(self, amp: float):
        amp_unit = 'V'
        amplitude = amp
        if amp < 1:
            amp *= 1000
            amp_unit ='MV'
        logger.debug(f'setting amplitude to {amp} {amp_unit}')
        self.amplitude = amplitude
