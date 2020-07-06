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
$ time python OrangeCrab-tests.py 
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
INFO: Hello from OrangeCrab! o/ 
INFO: build_date Jul  6 2020 12:02:02
INFO: test-repo 237ea00
INFO: migen b1b2b29
INFO: litex 1e605fb2
INFO: SPI-FLASH-ID=ef 17 ef 40 18 
INFO: SPI-FLASH-UUID=e4 69 30 d3 1b 23 3b 26 
TEST: SPI-FLASH           OK
TEST: DDR3                OK
TEST: I2C                 OK
TEST: GPIO                OK
TEST: ADC CH0             OK
TEST: ADC CH1             OK
TEST: ADC CH2             OK
TEST: ADC CH3             OK
TEST: ADC CH4             OK
TEST: ADC CH5             OK
TEST: ADC VREF            OK
TEST: ADC 3V3             OK
TEST: ADC 1V35            OK
TEST: ADC 2V5             OK
TEST: ADC 1V1             OK
INFO: Please press `btn0` on DUT
TEST: DFU Detect          OK
TEST: DFU Download        OK

real	0m19.529s
user	0m1.272s
sys	0m1.544s

```