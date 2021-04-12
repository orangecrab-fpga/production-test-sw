# This file is part of OrangeCrab-test
# Copyright 2020 Gregory Davill <greg.davill@gmail.com> 

import serial.tools.list_ports
import serial
import subprocess
import sys
import os
import math
import builtins
import statistics

from time import sleep, localtime, strftime


BRIGHTGREEN = '\033[92;1m'
BRIGHTRED = '\033[91;1m'
ENDC = '\033[0m'


Vs = 3.3
Fsamp = 96e6	# 48 MHz DDR
Csamp = 100e-9	# 100 nF
Rsamp = 5e3		# 5k

K = Fsamp * Csamp * Rsamp # ideal value
K = 40558 # best fit

Vchg = lambda t: Vs * (1 - math.exp(-((t + 200) / K)))

adc_calib = []
rails_voltage = dict()

batt_values = []

serial_log = []
output_log = []

# https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
def execute(command):
    subprocess.check_call(command, stdout=sys.stdout, stderr=sys.stdout)

def finish(result):
    if result == "PASS":
        print(BRIGHTGREEN + """
  ############################
  #          PASS            #
  ############################""" + ENDC)
    if result == "FAIL":
        print(BRIGHTRED + """
  ############################
  #          FAIL            #
  ############################""" + ENDC)

    # Flush log out to file
    os.makedirs('log', exist_ok=True)

    t = localtime()
    current_time = strftime("%Y-%m-%d-%H:%M:%S", t)
    #print(current_time)


    f= open(f"log/{result}-{current_time}.txt","w+")
    for l in output_log:
        f.write(l + '\n')
    f.write("\r\n-=-=-=-=-= RAW serial log -=-=-=-=-=-=\r\n")
    for l in serial_log:
        f.write(l + '\n')
    f.close()

    sys.exit(0)


def log(logtype, message, result=None):
    if logtype == "info":
        ...
        output_log.append(f'INFO: {message}')
        print(f'INFO: {message}')
    elif logtype == "test":
        s = f'TEST: {message:20s}{result}'
        output_log.append(s)

        if result == "OK":
            print(BRIGHTGREEN + s + ENDC)
        if result == "FAIL":
            print(BRIGHTRED + s + ENDC)
            finish("FAIL") # Exit early 
    elif logtype == "debug":
        ...
        serial_log.append(message)
        #print(message)

def ProcessLines(line):
    log("debug", line)
    if line.startswith("Info:"):
        log("info", line[5:])

    if line.startswith("Test:"):
        if 'pass' in line.lower():
            log("test", line[5:].split('|')[0], "OK")
        if 'failed' in line.lower():
            log("test", line[5:].split('|')[0], "FAIL")
        if 'started' in line.lower():
            log("info", line[5:])
    #if "Test:" in line and "Pass" in line:
        #print(line)

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
                batt_values.append(value)
            else:
                rails_voltage[rail] = voltage

        except:
            ...

    # Compute ADC results on PC 
    if "Test:ADC, Finish" in line:
        for i in range(6):
            ch_y = [Vchg(int(x['ADC']))*2 for x in adc_calib if x['CH'] == str(i)]
            ch_x = [(int(x['DAC']) * 3.3 / 0x1000) for x in adc_calib if x['CH'] == str(i)]
        
            d = [abs((x-y)/y) for x,y in zip(ch_x,ch_y) if y != 0 and x != 0]
            if statistics.mean(d) > 0.2: # average error of 20% over full range
                log("test", f"ADC CH{i}", "FAIL")
            else:
                log("test", f"ADC CH{i}", "OK")

            log("debug", f" - ADC CH{i} mean = {statistics.mean(d):.2f}")

        rails = {'VREF':3.3, '3V3':3.3, '1V35':1.35, '2V5':2.5, '1V1':1.1}

        for rail,v in rails.items():
            v_e = (rails_voltage[rail] - v) / v

            if abs(v_e) > 0.25:
                log("test", f"ADC {rail}", "FAIL")
            else:
                log("test", f"ADC {rail}", "OK")

    # Battery test?
    if "Test:BATT, Finish" in line:
        #print(batt_values)

        # When we connect a battery, the charger sees it and then starts charging.
        # We can monitor the battery voltage to detect that the charge voltage is applied

        # Ignore first values, check mean of first 5 values
        batt_connect = statistics.mean(batt_values[1:6])
        batt_charge = statistics.mean(batt_values[8:12])

        if (batt_charge - batt_connect) > 1000:
            log("test", f"BATT CHARGE", "OK")
        else:
            log("test", f"BATT CHARGE", "FAIL")



# Load test-bitstream over JTAG
print("-- Loading test bitstream into SRAM..")
#test_bitstream = '../hw/build/orangecrab/gateware/orangecrab.bit'
test_bitstream = '../prebuilt/orangecrab-test-85F.bit'
cmd = subprocess.Popen(["ecpprog", "-S", test_bitstream],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
(cmd_stdout, cmd_stderr) = cmd.communicate()

#print(cmd_stdout)
#print(cmd_stderr)
#b'IDCODE: 0x41111043 (LFE5U-25)\nECP5 Status Register: 0x00200100\nECP5 Status Register: 0x00200e10\nECP5 Status Register: 0x00200100\n'
#b'init..\nreset..\nprogramming..\nBye.\n'

# check results of programming
if "IDCODE: 0x41113043" in cmd_stdout.decode('ascii'):
    print("JTAG:LFE5U-85 Detected")
    #if "ECP5 Status Register: 0x00200100" in cmd_stdout.decode('ascii'):
    #    print("JTAG:Load Sucessful")
    #else:
    #    print("JTAG: Load Error")
else:
    print("JTAG: Load Error")
    finish("FAIL")


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
            except(SystemExit):
                raise
            except:
                print('--- Device Disconnect ---')
                print(" Error:", sys.exc_info()[0])
                try:
                    ser.close()
                except:
                    ...
                ...
            
    sleep(0.2)




# Load bootloader
# display info while loading the bootloader
print("-- Loading Bootloader into FLASH..")
bootloader = '../prebuilt/foboot-v3.1-orangecrab-r0.2-25F.bit'
execute(["ecpprog", bootloader])

# Load program that monitors button, and then reboots into bootloader
test_bitstream = '../prebuilt/orangecrab-reboot-25F.bit'
cmd = subprocess.Popen(["ecpprog", "-S", test_bitstream],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
(cmd_stdout, cmd_stderr) = cmd.communicate()

# check results of programming
if "IDCODE: 0x41111043" in cmd_stdout.decode('ascii'):
    print("JTAG: Load Complete")
else:
    print("JTAG: Load Error")
    finish("FAIL")

print("INFO: Please press `btn0` on DUT")

while(True):
    # check for DFU device attach?
    cmd = subprocess.Popen(["dfu-util","-l"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (cmd_stdout, cmd_stderr) = cmd.communicate()

    #print(cmd_stdout)
    sleep(0.2)
    if "OrangeCrab r0.2 DFU Bootloader" in cmd_stdout.decode('ascii'):
        log('test', "DFU Detect", "OK")
        break


# load quick demo program, to blink the LED
dfu_app  = '../prebuilt/blink_fw.dfu'
cmd = subprocess.Popen(["dfu-util","-D", dfu_app],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
(cmd_stdout, cmd_stderr) = cmd.communicate()

#print(cmd_stdout)
if 'Download done.' and 'status(0) = No error condition is present' in cmd_stdout.decode('ascii'):
    log('test', "DFU Download", "OK")
else:
    log('test', "DFU Download", "FAIL")


finish("PASS")