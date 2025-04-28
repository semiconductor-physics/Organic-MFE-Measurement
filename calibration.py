from model.magnetic_field import MagnetController
from model.daq import AnalogDaq, get_cp210x_uart_port
from collections import deque
from time import sleep
import numpy as np

class Stream_handler:
    def __init__(self, max_n_values= 2000) -> None:
        self.ch01 = deque(maxlen=max_n_values)
        self.ch23 = deque(maxlen=max_n_values)
        self.ch45 = deque(maxlen=max_n_values)
    def recieve_data(self, data: list[tuple[float, float, float]]):
        for value_tuple in data:
            self.ch01.append(value_tuple[0])
            self.ch23.append(value_tuple[1])
            self.ch45.append(value_tuple[2])
    def clear(self):
        self.ch01.clear()
        self.ch23.clear()
        self.ch45.clear()

def main():
    listener = Stream_handler(1000000)
    magnet = MagnetController()
    port = get_cp210x_uart_port()
    daq = AnalogDaq(port)
    daq.initialize()
    daq.add_stream_listener(listener.recieve_data)
    try:
        while True:
            v = float(input('Magnet Voltage: '))
            magnet._turn_on()
            magnet.set_voltage(v)
            sleep(2)  # wait for the magnet to settle
            daq.start_stream()
            sleep(2) # streaming value for x seconds
            daq.stop_stream()
            ch01 = np.array(listener.ch01)
            print(f'channel-01: {len(ch01)} values. avg: {np.mean(ch01)}, stdv: {np.std(ch01)}, max: {np.max(ch01)}, min: {np.min(ch01)}, last: {ch01[-1]}')
            ch23 = np.array(listener.ch23)
            print(f'channel-23: {len(ch23)} values. avg: {np.mean(ch23)}, stdv: {np.std(ch23)}, max: {np.max(ch23)}, min: {np.min(ch23)} , last: {ch23[-1]}')
            ch45 = np.array(listener.ch45)
            print(f'channel-45: {len(ch45)} values. avg: {np.mean(ch45)}, stdv: {np.std(ch45)}, max: {np.max(ch45)}, min: {np.min(ch45)}, last: {ch45[-1]}')
            listener.clear()
            magnet._turn_off()
    finally:
        print('turn magnet off')
        magnet._turn_off()
        daq.finalize()   


if __name__ == "__main__":
    main()