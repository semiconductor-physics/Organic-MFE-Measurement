import pyvisa
from pyvisa.resources import GPIBInstrument
from pymeasure.instruments.oxfordinstruments import ITC503

class EA_PSU():
    def __init__(self, address=None):
        if address is None:
            print('Connecting with EA_PSU...')
            rm = pyvisa.ResourceManager()
            self.__EA_PSU = rm.open_resource('GPIB0::30::INSTR')
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

 

if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    print(rm.list_resources())
    cryo_temp_controller = ITC503('GPIB0::24::INSTR')
    cryo_temp_controller.control_mode = "RU" 
    print(f'current setpoint: {cryo_temp_controller.temperature_setpoint}')
    print(f'temp at sensor 1: {cryo_temp_controller.temperature_1}')
    cryo_temp_controller.front_panel_display = "temperature setpoint"
