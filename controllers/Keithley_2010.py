import pyvisa
import logging
import logging
logger = logging.getLogger(__name__)


class Keithley_2010:
    def __init__(self, address=None):
        if address is None:
            print('Connecting with Keithley2010...')
            rm = pyvisa.ResourceManager()
            self.__Keithley_2010 = rm.open_resource('GPIB0::29')
        else:
            rm = pyvisa.ResourceManager()
            self.__Keithley_2010 = rm.open_resource(address)

    def __send(self, cmds):
        '''sends a list of commands to the device'''
        for cmd in cmds:
            self.__Keithley_2010.write(cmd)

    def write(self, command):
        self.__Keithley_2010.write(command)

    def query(self, query):
        return self.__Keithley_2010.query(query)
        
    def reset(self):
        self.write("*RST") # Gerät zurücksetzen

    def remote_setting(self):
        self.write(":SYST:REM")  # Remote-Betrieb aktivieren
    
    def resistance_meas(self):
        self.write(":CONF:RES")  # Widerstandsmessung konfigurieren
        self.write(":SENS:RES:OCOM ON")  # 4-Draht-Widerstandsmessung aktivieren

    def parse_resistance(self, response):
        clean_value = response.replace("NOHM", "").strip()  # Entfernt "NOHM" und Whitespaces
        return float(clean_value)  # Konvertiert zu Float

    def ask_temp(self):
        resistance_response = self.query(":FETC?")  # Messwert vom Keithley abfragen
        resistance = self.parse_resistance(resistance_response)
        return resistance
    
    def init_meas(self):
        self.write(":INIT")

    def local_setting(self):
        self.write(":SYST:LOC")  # Gerät wieder in lokalen Modus versetzen
        
    
if __name__ == '__main__':

    keithley_2010 = Keithley_2010()
    keithley_2010.init_meas()
    measure_resistance = keithley_2010.ask_temp()
    print(measure_resistance)
    