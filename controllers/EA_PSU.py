import pyvisa
import logging
import random

logger = logging.getLogger(__name__)

class EA_PSU():
    def __init__(self, address=None):
        if address is None:
            print('Connecting with EA_PSU...')
            rm = pyvisa.ResourceManager()
            self.__EA_PSU = rm.open_resource('GPIB0::30')
        else:
            rm = pyvisa.ResourceManager()
            self.__EA_PSU = rm.open_resource(address)

    def write(self, command):
        self.__EA_PSU.write(command)
        
    def query(self, query):
        return self.__EA_PSU.query(query)

    def Curr_mode(self):
        self.__EA_PSU.write("FUNC:MODE CURR")
        self.__EA_PSU.write("VOLT 50")

    def Volt_mode(self):
        self.__EA_PSU.write("FUNC:MODE VOLT")
        self.__EA_PSU.write("CURR 2")
        
    def set_current(self, Curr):
        self.__EA_PSU.write("CURR " + str(abs(Curr)))

    def set_voltage(self, Volt):
        self.__EA_PSU.write("VOLT " + str(abs(Volt)))

    def turn_on(self):
        self.__EA_PSU.write("OUTP 1")

    def turn_off(self):
        self.__EA_PSU.write("OUTP 0")

    def meas_volt(self):
        return self.__EA_PSU.query("MEAS:VOLT?")

    def meas_curr(self):
        return self.__EA_PSU.query("MEAS:CURR?")

class DummyEA_PSU:
    def __init__(self, address=None):
        if address is None:
            logger.debug("Connecting to EA_PSU with default address...")
            self.address = 'GPIB0::30'
        else:
            logger.debug(f"Connecting to EA_PSU at address: {address}")
            self.address = address
        self.mode = None
        self.voltage = 0.0
        self.current = 0.0
        self.output = False

    def write(self, command):
        logger.debug(f"EA_PSU <<< {command}")

    def query(self, query):
        logger.debug(f"EA_PSU >>> {query}")
        if query == "MEAS:VOLT?":
            return f"{random.uniform(0.0, 50.0):.2f}"  # Simulate voltage measurement
        elif query == "MEAS:CURR?":
            return f"{random.uniform(0.0, 2.0):.3f}"  # Simulate current measurement
        else:
            return "OK"

    def Curr_mode(self):
        logger.debug("Setting EA_PSU to Current Mode")
        self.mode = "CURRENT"
        self.voltage = 50
        self.write("FUNC:MODE CURR")
        self.write("VOLT 50")

    def Volt_mode(self):
        logger.debug("Setting EA_PSU to Voltage Mode")
        self.mode = "VOLTAGE"
        self.current = 2
        self.write("FUNC:MODE VOLT")
        self.write("CURR 2")

    def set_current(self, Curr):
        Curr = abs(Curr)
        logger.debug(f"Setting EA_PSU current to {Curr} A")
        self.current = Curr
        self.write(f"CURR {Curr}")

    def set_voltage(self, Volt):
        Volt = abs(Volt)
        logger.debug(f"Setting EA_PSU voltage to {Volt} V")
        self.voltage = Volt
        self.write(f"VOLT {Volt}")

    def turn_on(self):
        logger.debug("Turning on EA_PSU output")
        self.output = True
        self.write("OUTP 1")

    def turn_off(self):
        logger.debug("Turning off EA_PSU output")
        self.output = False
        self.write("OUTP 0")

    def meas_volt(self):
        voltage = self.query("MEAS:VOLT?")
        logger.debug(f"Measured voltage: {voltage} V")
        return voltage

    def meas_curr(self):
        current = self.query("MEAS:CURR?")
        logger.debug(f"Measured current: {current} A")
        return current

if __name__ == '__main__':

    ea_psu = EA_PSU()
    ea_psu.set_voltage(50)
    measure_current = ea_psu.meas_curr()
    print(measure_current)