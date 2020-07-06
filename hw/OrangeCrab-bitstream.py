#!/usr/bin/env python3

# This file is Copyright (c) Greg Davill <greg.davill@gmail.com>
# License: BSD


# This variable defines all the external programs that this module
# relies on.  lxbuildenv reads this variable in order to ensure
# the build will finish without exiting due to missing third-party
# programs.
LX_DEPENDENCIES = ["riscv", "nextpnr-ecp5", "yosys"]

# Import lxbuildenv to integrate the deps/ directory
import lxbuildenv



import sys
import os
import shutil
import argparse
import subprocess

import inspect

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import orangecrab
#from litex_boards.targets.orangecrab import _CRG

from litex.build.lattice.trellis import trellis_args, trellis_argdict

from litex.build.generic_platform import IOStandard, Subsignal, Pins, Misc

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import MT41K64M16, MT41K128M16, MT41K256M16
from litedram.phy import ECP5DDRPHY

from litex.soc.cores.spi import SPIMaster
from litex.soc.cores.bitbang import I2CMaster

from litex.soc.doc import generate_docs


from migen.genlib.cdc import MultiReg

import valentyusb

from rtl.rgb import RGB
from rtl.analog import AnalogSense
from litex.soc.cores import spi_flash
from litex.soc.cores.gpio import GPIOTristate, GPIOOut, GPIOIn

# Small hack to add Pull-up to the RGB-LED I/O pins, for detecting shorts
rgb_led_io = [
    ("rgb_led_io", 0,
        Subsignal("r", Pins("K4"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),
        Subsignal("g", Pins("M3"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),
        Subsignal("b", Pins("J3"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),
    )
]

# connect all remaninig GPIO pins out
extras = [
    ("gpio", 0, Pins("GPIO:1 GPIO:5 GPIO:6 GPIO:9 GPIO:10 GPIO:11 GPIO:12 GPIO:13  GPIO:18 GPIO:19 GPIO:20 GPIO:21"), 
        IOStandard("LVCMOS33"), Misc("PULLMODE=DOWN")),
    ("i2c", 0,
        Subsignal("sda", Pins("GPIO:2"), IOStandard("LVCMOS33")),
        Subsignal("scl", Pins("GPIO:3"), IOStandard("LVCMOS33"))
    ),
    ("spi",0,
        Subsignal("miso", Pins("GPIO:14"), IOStandard("LVCMOS33")),
        Subsignal("mosi", Pins("GPIO:16"), IOStandard("LVCMOS33")),
        Subsignal("clk",  Pins("GPIO:15"), IOStandard("LVCMOS33")),
        Subsignal("cs_n", Pins("GPIO:0"), IOStandard("LVCMOS33"))
    ),
    ("ldac", 0, Pins("GPIO:1"), IOStandard("LVCMOS33")),
    ("clrdac", 0, Pins("GPIO:5"), IOStandard("LVCMOS33")),
    ("analog", 0,
        Subsignal("mux", Pins("F4 F3 F2 H1")),
        Subsignal("enable", Pins("F1")),
        Subsignal("ctrl", Pins("G1")),
        Subsignal("sense_p", Pins("H3"), IOStandard("LVCMOS33D")),
        Subsignal("sense_n", Pins("G3")),
        IOStandard("LVCMOS33")
    )
]


class GPIOTristateCustom(Module, AutoCSR):
    def __init__(self, pads):
        nbits     = len(pads)
        fields=[
                CSRField(str("dac_ldac"), 1, 1  ,description="Load Dac, Active LOW"),
                CSRField(str("dac_clr"),  1, 5  ,description="Clear Dac, Actiwe LOW"),
                CSRField(str("io6"), 1, 6  ,description="Control for I/O pin 6"),
                CSRField(str("io9"), 1, 9  ,description="Control for I/O pin 9"),
                CSRField(str("io10"), 1, 10,description="Control for I/O pin 10"),
                CSRField(str("io11"), 1, 11,description="Control for I/O pin 11"),
                CSRField(str("io12"), 1, 12,description="Control for I/O pin 12"),
                CSRField(str("io13"), 1, 13,description="Control for I/O pin 13"),
                CSRField(str("io18"), 1, 18,description="Control for I/O pin 18"),
                CSRField(str("io19"), 1, 19,description="Control for I/O pin 19"),
                CSRField(str("io20"), 1, 20,description="Control for I/O pin 10"),
                CSRField(str("io21"), 1, 21,description="Control for I/O pin 21"),
            ]

        self._oe  = CSRStorage(nbits, description="""GPIO Tristate(s) Control.
        Write ``1`` enable output driver""", fields=fields)
        self._in  = CSRStatus(nbits,  description="""GPIO Input(s) Status.
        Input value of IO pad as read by the FPGA""", fields=fields)
        self._out = CSRStorage(nbits, description="""GPIO Ouptut(s) Control.
        Value loaded into the output driver""", fields=fields)

        # # #

        _pads = Signal(nbits)
        self.comb += _pads.eq(pads)

        for i,f in enumerate(fields):
            t = TSTriple()
            self.specials += t.get_tristate(_pads[i])
            self.comb += t.oe.eq(self._oe.storage[f.offset])
            self.comb += t.o.eq(self._out.storage[f.offset])
            self.specials += MultiReg(t.i, self._in.status[f.offset])



# CRG ---------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq, with_usb_pll=False):
        self.clock_domains.cd_init     = ClockDomain()
        self.clock_domains.cd_por      = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys      = ClockDomain()
        self.clock_domains.cd_sys2x    = ClockDomain()
        self.clock_domains.cd_sys2x_i  = ClockDomain()


        # # #

        self.stop = Signal()
        self.reset = Signal()

        
        # Use OSCG for generating por clocks.
        osc_g = Signal()
        self.specials += Instance("OSCG",
            p_DIV=6, # 38MHz
            o_OSC=osc_g
        )

        # Clk
        clk48 = platform.request("clk48")
        por_done  = Signal()

        # Power on reset 10ms.
        por_count = Signal(24, reset=int(48e6 * 50e-3))
        self.comb += self.cd_por.clk.eq(clk48)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        sys2x_clk_ecsout = Signal()
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(clk48, 48e6)
        pll.create_clkout(self.cd_sys2x_i, 2*sys_clk_freq)
        pll.create_clkout(self.cd_init, 24e6)
        self.specials += [
            Instance("ECLKBRIDGECS",
                i_CLK0   = self.cd_sys2x_i.clk,
                i_SEL    = 0,
                o_ECSOUT = sys2x_clk_ecsout),
            Instance("ECLKSYNCB",
                i_ECLKI = sys2x_clk_ecsout,
                i_STOP  = self.stop,
                o_ECLKO = self.cd_sys2x.clk),
            Instance("CLKDIVF",
                p_DIV     = "2.0",
                i_ALIGNWD = 0,
                i_CLKI    = self.cd_sys2x.clk,
                i_RST     = self.reset,
                o_CDIVX   = self.cd_sys.clk),
            AsyncResetSynchronizer(self.cd_init,  ~por_done | ~pll.locked),
            AsyncResetSynchronizer(self.cd_sys,   ~por_done | ~pll.locked | self.reset),
            AsyncResetSynchronizer(self.cd_sys2x, ~por_done | ~pll.locked | self.reset),
            AsyncResetSynchronizer(self.cd_sys2x_i, ~por_done | ~pll.locked | self.reset),
        ]

        # USB PLL
        if with_usb_pll:
            self.clock_domains.cd_usb_12 = ClockDomain()
            self.clock_domains.cd_usb_48 = ClockDomain()
            usb_pll = ECP5PLL()
            self.submodules += usb_pll
            usb_pll.register_clkin(clk48, 48e6)
            usb_pll.create_clkout(self.cd_usb_48, 48e6)
            usb_pll.create_clkout(self.cd_usb_12, 12e6)
            self.specials += [
                AsyncResetSynchronizer(self.cd_usb_48,  ~por_done | ~usb_pll.locked),
                AsyncResetSynchronizer(self.cd_usb_12,  ~por_done | ~usb_pll.locked)
            ]



# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    csr_map = {
        "ctrl":           0,  # provided by default (optional)
        "crg":            1,  # user
        "identifier_mem": 4,  # provided by default (optional)
        "timer0":         5,  # provided by default (optional)
       
        "gpio_led":       10,
        "gpio":           11,
        "self_reset":     12,
        "version":        14,
        "lxspi":          15,
        "button":         17,
        "spi":            18,
        "i2c":            19,
        "asense":         20,
    }
    csr_map.update(SoCCore.csr_map)

    mem_map = {
        "rom":      0x00000000,  # (default shadow @0x80000000)
        "sram":     0x10000000,  # (default shadow @0xa0000000)
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
        "main_ram": 0x40000000,  # (default shadow @0xc0000000)
        "csr":      0xe0000000,  # (default shadow @0xe0000000)
    }
    mem_map.update(SoCCore.mem_map)

    interrupt_map = {
        "timer0": 2,
        "usb": 3,
    }
    interrupt_map.update(SoCCore.interrupt_map)

    def __init__(self, sys_clk_freq=int(48e6), toolchain="trellis", **kwargs):
        # Board Revision ---------------------------------------------------------------------------
        revision = kwargs.get("revision", "0.2")
        device = kwargs.get("device", "25F")

        platform = orangecrab.Platform(revision=revision, device=device ,toolchain=toolchain)

        # Serial -----------------------------------------------------------------------------------
        #platform.add_extension(orangecrab.feather_serial)


        # USB hardware Abstract Control Model.
        kwargs['uart_name']="usb_acm"

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq, csr_data_width=32, **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = crg = CRG(platform, sys_clk_freq, with_usb_pll=True)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        #if 0:
        if not self.integrated_main_ram_size:
            available_sdram_modules = {
                'MT41K64M16': MT41K64M16,
                'MT41K128M16': MT41K128M16,
                'MT41K256M16': MT41K256M16
            }
            sdram_module = available_sdram_modules.get(
                kwargs.get("sdram_device", "MT41K64M16"))

            ddr_pads = platform.request("ddram")
            self.submodules.ddrphy = ECP5DDRPHY(
                ddr_pads,
                sys_clk_freq=sys_clk_freq)
            self.add_csr("ddrphy")
            self.add_constant("ECP5DDRPHY")
            self.comb += crg.stop.eq(self.ddrphy.init.stop)
            self.comb += crg.reset.eq(self.ddrphy.init.reset)
            self.add_sdram("sdram",
                phy                     = self.ddrphy,
                module                  = sdram_module(sys_clk_freq, "1:2"),
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x40000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = True
            )

            self.comb += ddr_pads.vccio.eq(1)
            self.comb += ddr_pads.gnd.eq(0)

        # Add extra pin definitions
        platform.add_extension(extras)

        # RGB LED
        platform.add_extension(rgb_led_io)
        led = platform.request("rgb_led_io", 0)

        self.submodules.gpio_led = GPIOTristate(Cat(led.r,led.g,led.b))
        self.submodules.gpio = GPIOTristateCustom(platform.request("gpio", 0))

        # SPI
        self.submodules.spi = SPIMaster(platform.request("spi"), 24, sys_clk_freq, int(4e6))

        # i2c
        self.submodules.i2c = I2CMaster(platform.request("i2c"))

        # Controllable Self Reset
        reset_code = Signal(32, reset=0)
        self.submodules.self_reset = GPIOOut(reset_code)
        self.comb += platform.request("rst_n").eq(reset_code != 0xAA550001)

        self.submodules.button = GPIOIn(platform.request("usr_btn"))
        
        # Analog Mux
        self.submodules.asense = AnalogSense(platform.request("analog"))
        
        # The litex SPI module supports memory-mapped reads, as well as a bit-banged mode
        # for doing writes.
        spi_pads = platform.request("spiflash4x")
        self.submodules.lxspi = spi_flash.SpiFlashDualQuad(spi_pads, dummy=6, endianness="little")
        self.lxspi.add_clk_primitive(platform.device)
        self.register_mem("spiflash", self.mem_map["spiflash"], self.lxspi.bus, size=16*1024*1024)

        # Add GIT repo to the firmware
        git_rev_cmd = subprocess.Popen(["git", "rev-parse", "--short", "HEAD"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
        (git_stdout, _) = git_rev_cmd.communicate()
        self.add_constant('REPO_GIT_SHA1',git_stdout.decode('ascii').strip('\n'))



    # This function will build our software and create a oc-fw.init file that can be patched directly into blockram in the FPGA
    def PackageFirmware(self, builder):  
        self.finalize()

        os.makedirs(builder.output_dir, exist_ok=True)

        src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fw"))
        builder.add_software_package("fw", src_dir)

        builder._prepare_rom_software()
        builder._generate_includes()
        builder._generate_rom_software(compile_bios=False)

        firmware_file = os.path.join(builder.output_dir, "software", "fw","oc-fw.bin")
        firmware_data = get_mem_data(firmware_file, self.cpu.endianness)
        self.initialize_rom(firmware_data)

        # lock out compiling firmware during build steps
        builder.compile_software = False


def CreateFirmwareInit(init, output_file):
    content = ""
    for d in init:
        content += "{:08x}\n".format(d)
    with open(output_file, "w") as o:
        o.write(content)    


# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on OrangeCrab")
    parser.add_argument("--gateware-toolchain", dest="toolchain", default="trellis",
        help="gateware toolchain to use, trellis (default) or diamond")
    builder_args(parser)
    soc_sdram_args(parser)
    trellis_args(parser)
    parser.add_argument("--sys-clk-freq", default=48e6,
                        help="system clock frequency (default=48MHz)")
    parser.add_argument("--revision", default="0.2",
                        help="Board Revision {0.1, 0.2} (default=0.2)")
    parser.add_argument("--device", default="25F",
                        help="ECP5 device (default=25F)")
    parser.add_argument("--sdram-device", default="MT41K64M16",
                        help="ECP5 device (default=MT41K64M16)")
    parser.add_argument(
        "--update-firmware", default=False, action='store_true',
        help="compile firmware and update existing gateware"
    )
    args = parser.parse_args()

    soc = BaseSoC(toolchain=args.toolchain, sys_clk_freq=int(float(args.sys_clk_freq)),**argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    


    # Build firmware
    soc.PackageFirmware(builder)
    #generate_docs(soc, "build/documentation/", project_name="OrangeCrab Test SoC", author="Greg Davill")
        
    # Check if we have the correct files
    firmware_file = os.path.join(builder.output_dir, "software", "fw", "oc-fw.bin")
    firmware_data = get_mem_data(firmware_file, soc.cpu.endianness)
    firmware_init = os.path.join(builder.output_dir, "software", "fw", "oc-fw.init")
    CreateFirmwareInit(firmware_data, firmware_init)
    
    rand_rom = os.path.join(builder.output_dir, "gateware", "rand.data")

    

    # If we don't have a random file, create one, and recompile gateware
    if (os.path.exists(rand_rom) == False) or (args.update_firmware == False):
        os.makedirs(os.path.join(builder.output_dir,'gateware'), exist_ok=True)
        os.makedirs(os.path.join(builder.output_dir,'software'), exist_ok=True)

        os.system(f"ecpbram  --generate {rand_rom} --seed {0} --width {32} --depth {soc.integrated_rom_size}")

        # patch random file into BRAM
        data = []
        with open(rand_rom, 'r') as inp:
            for d in inp.readlines():
                data += [int(d, 16)]
        soc.initialize_rom(data)

        # Build gateware
        builder_kargs = trellis_argdict(args) if args.toolchain == "trellis" else {}
        vns = builder.build(**builder_kargs)
        soc.do_exit(vns)   
    

    input_config = os.path.join(builder.output_dir, "gateware", f"{soc.platform.name}.config")
    output_config = os.path.join(builder.output_dir, "gateware", f"{soc.platform.name}_patched.config")

    # Insert Firmware into Gateware
    os.system(f"ecpbram  --input {input_config} --output {output_config} --from {rand_rom} --to {firmware_init}")


    # create compressed config (ECP5 specific)
    output_bitstream = os.path.join(builder.gateware_dir, f"{soc.platform.name}.bit")
    #os.system(f"ecppack --freq 38.8 --spimode qspi --compress --input {output_config} --bit {output_bitstream}")
    os.system(f"ecppack --freq 38.8 --compress --input {output_config} --bit {output_bitstream}")

    dfu_file = os.path.join(builder.gateware_dir, f"{soc.platform.name}.dfu")
    shutil.copyfile(output_bitstream, dfu_file)
    os.system(f"dfu-suffix -v 1209 -p 5bf0 -a {dfu_file}")


def argdict(args):
    r = soc_sdram_argdict(args)
    for a in ["device", "revision", "sdram_device"]:
        arg = getattr(args, a, None)
        if arg is not None:
            r[a] = arg
    return r

if __name__ == "__main__":
    main()
