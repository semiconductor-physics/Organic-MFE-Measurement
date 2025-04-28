import pyvisa
import logging
import random

logger = logging.getLogger(__name__)

class Keithley_smu():
    def __init__(self, address=None):
        if address is None:
            print('Connecting with Keithley2636...')
            rm = pyvisa.ResourceManager()
            self.__Keithley_smu = rm.open_resource('GPIB0::26')
        else:
            rm = pyvisa.ResourceManager()
            self.__Keithley_smu = rm.open_resource(address)

        self.__intTime = 5.0  # standard integration time in powerline cycles: 20ms = 1 plc
        self.__waitingTime = 0.0  # in ms --> minimum waiting time to measure after setting voltage
        self.__maxPower = 2.0  # in Watt
        self.__average = 1  # number of averages for each data point measurement

    def __send(self, cmds):
        '''sends a list of commands to the device'''
        for cmd in cmds:
            self.__Keithley_smu.write(cmd)
        
    def initKeithley(self):
        optns = []
        optns.append('display.screen = display.SMUA_SMUB')
        optns.append('smua.source.func = smua.OUTPUT_DCVOLTS') #voltage source
##        optns.append('smub.source.func = smub.OUTPUT_DCVOLTS') #current source
        optns.append('smua.source.autorangev = smua.AUTORANGE_ON') #voltage source AutoRange
##        optns.append('smub.source.autorangev = smub.AUTORANGE_ON') #current source AutoRange
        optns.append('display.smua.measure.func =  display.MEASURE_DCAMPS')
##        optns.append('display.smub.measure.func =  display.MEASURE_DCAMPS')
        optns.append('smua.sense = smua.SENSE_LOCAL') #2 wire measurement
##        optns.append('smub.sense = smub.SENSE_LOCAL') #2 wire measurement
        optns.append('smua.measure.autorangei = smua.AUTORANGE_ON') #voltage measurement AutoRange
##        optns.append('smub.measure.autorangei = smub.AUTORANGE_ON') #voltage measurement AutoRange
        optns.append('smua.measure.nplc = %f' % self.__intTime) # integration time in Number of Power Line Cycles (range from 0.001 to 25) 25 MAYBE HAS A BUG
##        optns.append('smub.measure.nplc = %f' % self.__intTime) # integration time in Number of Power Line Cycles (range from 0.001 to 25) 25 MAYBE HAS A BUG
        optns.append('smua.measure.analogfilter = 1') # switches on analog filter for low current ranges
##        optns.append('smub.measure.analogfilter = 1') # switches on analog filter for low current ranges
        optns.append('smua.measure.autozero = smua.AUTOZERO_ONCE') # enables autozero once mode for more precise measurement
##        optns.append('smub.measure.autozero = smub.AUTOZERO_ONCE') # enables autozero once mode for more precise measurement
        optns.append('smua.measure.filter.enable = smua.FILTER_OFF') # turns off filter function
##        optns.append('smua.measure.filter.enable = smua.FILTER_OFF') # turns off filter function
        self.__send(optns)

    def write(self, command):
        self.__Keithley_smu.write(command)

    def query(self, query):
        return self.__Keithley_smu.query(query)
    
    def setIntegrationTime(self, time):
        '''time in seconds; for 50Hz 1 plc = 20ms --> range time from 20µs to 500ms'''
        self.__intTime = time / 0.02

    def init_voltage(self):
        self.write('smua.source.func = smua.OUTPUT_DCVOLTS')

    def init_current(self):
        self.write('smua.source.func = smua.OUTPUT_DCAMPS')

    def set_voltage(self, Volt_keithley):
        self.write('smua.source.levelv = ' + str(Volt_keithley))

    def set_current(self, Curr_Keithley):
        self.write('smua.source.leveli = ' + str(Curr_Keithley))
        
    def turn_on(self):
        self.write('smua.source.output = smua.OUTPUT_ON')
        
    def turn_off(self):
        self.write('smua.source.output = smua.OUTPUT_OFF')
        
    def autorange(self):
        self.write('smua.source.autorangei = smua.AUTORANGE_ON')
        
    def localnode(self):
        self.write('localnode.prompts = 0')
        
    def meas_current(self):
        return self.query('print(smua.measure.i())')

    def outputOn(self, cha): # cha = channel A/B
        '''turns the output on'''
        self.write(['smu%s.source.output = smu%s.OUTPUT_ON' % (cha, cha)])
        
    def outputOff(self, cha): # cha = channel A/B
        '''turns the output off'''
        self.write(['smu%s.source.output = smu%s.OUTPUT_OFF' % (cha, cha)])


class DummyKeithley_smu():
    def __init__(self, address=None):
        logging.debug('Connecting with DummyKeithley_smu...')
        if address is None:
            self.address = 'GPIB0::26'
        else:    
            self.address = address
        self.__intTime = 5.0  # standard integration time in powerline cycles: 20ms = 1 plc
        self.__waitingTime = 0.0  # in ms --> minimum waiting time to measure after setting voltage
        self.__maxPower = 2.0  # in Watt
        self.__average = 1  # number of averages for each data point measurement

    def __send(self, cmds):
        '''sends a list of commands to the device'''
        for cmd in cmds:
            logging.debug(f'keithley <<< {cmd}')
        
    def initKeithley(self):
        optns = []
        optns.append('display.screen = display.SMUA_SMUB')
        optns.append('smua.source.func = smua.OUTPUT_DCVOLTS') #voltage source
##        optns.append('smub.source.func = smub.OUTPUT_DCVOLTS') #current source
        optns.append('smua.source.autorangev = smua.AUTORANGE_ON') #voltage source AutoRange
##        optns.append('smub.source.autorangev = smub.AUTORANGE_ON') #current source AutoRange
        optns.append('display.smua.measure.func =  display.MEASURE_DCAMPS')
##        optns.append('display.smub.measure.func =  display.MEASURE_DCAMPS')
        optns.append('smua.sense = smua.SENSE_LOCAL') #2 wire measurement
##        optns.append('smub.sense = smub.SENSE_LOCAL') #2 wire measurement
        optns.append('smua.measure.autorangei = smua.AUTORANGE_ON') #voltage measurement AutoRange
##        optns.append('smub.measure.autorangei = smub.AUTORANGE_ON') #voltage measurement AutoRange
        optns.append('smua.measure.nplc = %f' % self.__intTime) # integration time in Number of Power Line Cycles (range from 0.001 to 25) 25 MAYBE HAS A BUG
##        optns.append('smub.measure.nplc = %f' % self.__intTime) # integration time in Number of Power Line Cycles (range from 0.001 to 25) 25 MAYBE HAS A BUG
        optns.append('smua.measure.analogfilter = 1') # switches on analog filter for low current ranges
##        optns.append('smub.measure.analogfilter = 1') # switches on analog filter for low current ranges
        optns.append('smua.measure.autozero = smua.AUTOZERO_ONCE') # enables autozero once mode for more precise measurement
##        optns.append('smub.measure.autozero = smub.AUTOZERO_ONCE') # enables autozero once mode for more precise measurement
        optns.append('smua.measure.filter.enable = smua.FILTER_OFF') # turns off filter function
##        optns.append('smua.measure.filter.enable = smua.FILTER_OFF') # turns off filter function
        self.__send(optns)

    def write(self, command):
        logging.debug(f'keithley <<< {command}')

    def query(self, query):
        logging.debug(f'keithley >>> {query}')
        return random.uniform(0.0, 2.0)
    
    def setIntegrationTime(self, time):
        '''time in seconds; for 50Hz 1 plc = 20ms --> range time from 20µs to 500ms'''
        self.__intTime = time / 0.02

    def init_voltage(self):
        self.write('smua.source.func = smua.OUTPUT_DCVOLTS')

    def init_current(self):
        self.write('smua.source.func = smua.OUTPUT_DCAMPS')

    def set_voltage(self, Volt_keithley):
        self.write('smua.source.levelv = ' + str(Volt_keithley))

    def set_current(self, Curr_Keithley):
        self.write('smua.source.leveli = ' + str(Curr_Keithley))
        
    def turn_on(self):
        self.write('smua.source.output = smua.OUTPUT_ON')
        
    def turn_off(self):
        self.write('smua.source.output = smua.OUTPUT_OFF')
        
    def autorange(self):
        self.write('smua.source.autorangei = smua.AUTORANGE_ON')
        
    def localnode(self):
        self.write('localnode.prompts = 0')
        
    def meas_current(self):
        return self.query('print(smua.measure.i())')

    def outputOn(self, cha): # cha = channel A/B
        '''turns the output on'''
        self.write(['smu%s.source.output = smu%s.OUTPUT_ON' % (cha, cha)])
        
    def outputOff(self, cha): # cha = channel A/B
        '''turns the output off'''
        self.write(['smu%s.source.output = smu%s.OUTPUT_OFF' % (cha, cha)])

if __name__ == '__main__':
    keithley = Keithley_smu()

    keithley.set_current(1)

    keithley.init_voltage()
    keithley.set_voltage(1.0)
    keithley.turn_on()
    measure_current = keithley.meas_current()
    print(measure_current)

