# This file is part of OrangeCrab-test
# Copyright 2020 Gregory Davill <greg.davill@gmail.com> 

import serial.tools.list_ports
import serial
import subprocess

from time import sleep


def ProcessLines(line):
    if "Info:" in line:
        print(line)

    if "Test:" in line:
        print(line)

    if "Test:ADC, Finish" in line:
        print("=-=-=-=-=-= Results ==-=-=-=-=-=-")

    if "ADC" in line:
        print(" - " + line)


test_bitstream = '../hw/build/orangecrab/gateware/orangecrab.bit'
cmd = subprocess.Popen(["ecpprog", "-S", test_bitstream],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
(cmd_stdout, cmd_stderr) = cmd.communicate()

#print(cmd_stdout)
#print(cmd_stderr)
#b'IDCODE: 0x41111043 (LFE5U-25)\nECP5 Status Register: 0x00200100\nECP5 Status Register: 0x00200e10\nECP5 Status Register: 0x00200100\n'
#b'init..\nreset..\nprogramming..\nBye.\n'

# check results of programming
if "IDCODE: 0x41111043" in cmd_stdout.decode('ascii'):
    print("JTAG:LFE5U-25 Detected")
if "ECP5 Status Register: 0x00200100" in cmd_stdout.decode('ascii'):
    print("JTAG:Load Sucessful")


print("-- Wait for USB device..")

test_complete = False
# Simple python script to find and connect to a serial port automtically when it's connected. 
while test_complete == False:
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "OrangeCrab ACM" or "OrangeCrab CDC" in p.description:
            print(f"-- Found {p.description} [{p.vid:04x}:{p.pid:04x} - Serial:{p.serial_number}] ---")
            
            # Connect and output feed
            try:
                ser = serial.Serial(p.device)

                while True:
                    data = ser.readline().decode(encoding='ascii').strip("\n\r")
                    if data:
                        ProcessLines(data)
                        #print(data.decode(encoding='ascii'), end='')

                        if "Test:DONE, Finish" in data:
                            test_complete = True
                            break
                    else:
                        sleep(0.01)
            except:
                print("Unexpected error:", sys.exc_info()[0])
                print('--- Device Disconnect ---')
                ser.close()
                ...
            
    sleep(0.2)

   
