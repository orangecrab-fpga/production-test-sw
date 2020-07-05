# This file is part of OrangeCrab-test
# Copyright 2020 Gregory Davill <greg.davill@gmail.com> 

import serial.tools.list_ports
import serial
import subprocess
import sys
import math
import builtins

from time import sleep

Vs = 3.3
Fsamp = 96e6	# 48 MHz DDR
Csamp = 100e-9	# 100 nF
Rsamp = 5e3		# 5k

K = Fsamp * Csamp * Rsamp # ideal value
K = 40558 # best fit

Vchg = lambda t: Vs * (1 - math.exp(-((t + 200) / K)))

adc_calib = []
rails_voltage = dict()

# https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
def execute(command):
    subprocess.check_call(command, stdout=sys.stdout, stderr=sys.stdout)

def ProcessLines(line):
    if "Info:" in line:
        print(line)

    if "Test:" in line and "Pass" in line:
        print(line)

    # save ADC values in arrays
    if "CH=" in line:
        adc_calib.append(dict(map(lambda x: x.split('='), line.split(', '))))
    if "ADC" in line:
        try:
            value = int(line.split('=')[1])
            rail = line.split('=')[0].split('-')[1]
            voltage = Vchg(value)*2

            if "VBAT" in rail:
                voltage = voltage * 2

            rails_voltage[rail] = voltage
        except:
            ...

    # Compute ADC results on PC 
    if "Test:ADC, Finish" in line:
        for i in range(6):
            ch_y = [Vchg(int(x['ADC']))*2 for x in adc_calib if x['CH'] == str(i)]
            ch_x = [(int(x['DAC']) * 3.3 / 0x1000) for x in adc_calib if x['CH'] == str(i)]
        
            d = [abs((x-y)/y) for x,y in zip(ch_x,ch_y) if y != 0 and x != 0]
            if max(d) > 0.25:
                print(d)
                print("Test:ADC, Fail")
            else:
                print(f"Test:ADC, CH{i} OK")

        rails = {'VREF':3.3, '3V3':3.3, '1V35':1.35, '2V5':2.5, '1V1':1.1}

        for rail,v in rails.items():
            v_e = (rails_voltage[rail] - v) / v

            if abs(v_e) > 0.25:
                print(f"{rail}: {v_e:.3f}")
                print("Test:ADC-RAIL, Fail")
            else:
                print(f"Test:ADC-RAIL, {rail} OK")

# Load bootloader
# display info while loading the bootloader
print("-- Loading Bootloader into FLASH..")
bootloader = '../prebuilt/foboot-v3.1-orangecrab-r0.2-25F.bit'
execute(["ecpprog", bootloader])

# Load test-bitstream over JTAG
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
    else:
        print("JTAG: Load Error")
else:
    print("JTAG: Load Error")


print("-- Wait for USB device..")

test_running = False
# Simple python script to find and connect to a serial port automtically when it's connected. 
while test_running == False:
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
                        test_running = True
                        #print(data.decode(encoding='ascii'), end='')

                        if "Test:DONE, Finish" in data:
                            #test_complete = True
                            break
                    else:
                        sleep(0.01)
            except:
                print('--- Device Disconnect ---')
                print(" Error:", sys.exc_info()[0])
                ser.close()
                ...
            
    sleep(0.2)

   
