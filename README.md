# OrangeCrab Test Software
This repository contains the software, firmware and gateware run on the OrangeCrab.

Software and gateware both utilise python, and the firmware is C

---
## Hardware ##
* OrangeCrab: [OrangeCrab Repo](https://github.com/gregdavill/OrangeCrab)
* OrangeCrab Test Fixture: [OranegCrab-test](https://github.com/mwelling/orangecrab-test)

## Usage ##

Current status: developing tests and workflow


To create the bitstream for the OrangeCrab run the following, the `--update-firmware` flag enables skipping synthesis and just patching BRAM contents with update firmware 
```
cd hw
python3 OrangeCrab-bitstream.py [--update-firmware]
ecpprog -S build/orangecrab/gateware/orangecrab.bit
```
