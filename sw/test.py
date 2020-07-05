# This file is part of OrangeCrab-test
# Copyright 2020 Gregory Davill <greg.davill@gmail.com> 

import serial.tools.list_ports
import serial

from time import sleep


def ProcessLines(line):
    if "Info:" in line:
        print(line, end='')

    if "Test:" in line:
        print(line, end='')

# Simple python script to find and connect to a serial port automtically when it's connected. 
while True:
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "OrangeCrab ACM" or "OrangeCrab CDC" in p.description:
            print(f"--- Found {p.description} [{p.vid:04x}:{p.pid:04x} - Serial:{p.serial_number}] ---")
            
            # Connect and output feed
            try:
                ser = serial.Serial(p.device)

                while True:
                    data = ser.readline()
                    if data:
                        ProcessLines(data.decode(encoding='ascii'))
                        #print(data.decode(encoding='ascii'), end='')
                    else:
                        sleep(0.01)
            except:
                print('--- Device Disconnect ---')
                ser.close()
                ...
            
    sleep(0.2)

   
