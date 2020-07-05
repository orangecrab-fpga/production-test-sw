# OrangeCrab Test Software
This repository contains the software, firmware and gateware run on the OrangeCrab.

Software and gateware both utilise python, and the firmware is C

---
## Hardware ##
* OrangeCrab: [OrangeCrab Repo](https://github.com/gregdavill/OrangeCrab)
* OrangeCrab Test Fixture: [OranegCrab-test](https://github.com/mwelling/orangecrab-test)

## Usage ##

Current status: developing tests and workflow


To create the bitstream for the OrangeCrab run the following, use `--update-firmware` flag when updating changes in firmware only.
```
cd hw
python3 OrangeCrab-bitstream.py [--update-firmware]
```

To load and run through the tests execute
```
cd sw
python3 OrangeCrab-tests.py
```


## Example test output ##
```
-- Loading Bootloader into FLASH..
init..
IDCODE: 0x41111043 (LFE5U-25)
ECP5 Status Register: 0x00200100
reset..
flash ID: 0xEF 0x40 0x18 0x00
file size: 234223
erase 64kB sector at 0x000000..
erase 64kB sector at 0x010000..
erase 64kB sector at 0x020000..
erase 64kB sector at 0x030000..
programming..  234223/234223
verify..       234223/234223  VERIFY OK
Bye.
JTAG:LFE5U-25 Detected
JTAG:Load Sucessful
-- Wait for USB device..
-- Found OrangeCrab CDC [1209:5bf2 - Serial:None] ---
Info:Hello from OrangeCrab! o/ 
Info:build_date Jul  5 2020 21:22:39
Info:test-repo da728ee
Info:migen b1b2b29
Info:litex 1e605fb2
Test:DDR3 Pass
Info:SPI-FLASH-ID=ef 17 ef 40 18 
Info:SPI-FLASH-UUID=e4 69 30 d3 1b 23 3b 26 
Test:SPI-FLASH, Passed
Test:I2C, Pass
Test:GPIO, Pass
Test:ADC, CH0 OK
Test:ADC, CH1 OK
Test:ADC, CH2 OK
Test:ADC, CH3 OK
Test:ADC, CH4 OK
Test:ADC, CH5 OK
Test:ADC-RAIL, VREF OK
Test:ADC-RAIL, 3V3 OK
Test:ADC-RAIL, 1V35 OK
Test:ADC-RAIL, 2V5 OK
Test:ADC-RAIL, 1V1 OK
```