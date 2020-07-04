include ../include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

ifeq ($(CPU),blackparrot)
BP_LIBS =  -L$(BP_LITEX_SOFTWARE)
BP_FLAGS = -lgcc
endif

CFLAGS += -I$(FW_DIRECTORY)/include

OBJECTS = isr.o			\
		sleep.o         \
		flash-spi.o     \
		dac53608.o      \
		mcp23s08.o      \
		asense.o        \
	    main.o


all: oc-fw.bin
	$(PYTHON) -m litex.soc.software.memusage oc-fw.elf $(CURDIR)/../include/generated/regions.ld $(TRIPLE)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@
ifneq ($(OS),Windows_NT)
	chmod -x $@
endif
ifeq ($(CPUENDIANNESS),little)
	$(PYTHON) -m litex.soc.software.mkmscimg $@ --little
else
	$(PYTHON) -m litex.soc.software.mkmscimg $@
endif

oc-fw.elf: ../libbase/crt0.o \
	../libcompiler_rt/libcompiler_rt.a \
	../libbase/libbase-nofloat.a \
	../liblitedram/liblitedram.a \
	../liblitespi/liblitespi.a \
	$(OBJECTS)
	$(LD) $(LDFLAGS) -L$(BUILDINC_DIRECTORY)/generated -T $(FW_DIRECTORY)/linker.ld -N -o $@ \
		../libbase/crt0.o \
		$(OBJECTS) \
		-L../libcompiler_rt \
		-L../liblitedram \
		-L../libbase \
		-L../liblitespi \
		-lcompiler_rt -llitedram -llitespi -lbase-nofloat 
		
ifneq ($(OS),Windows_NT)
	chmod -x $@
endif

# pull in dependency info for *existing* .o files
-include $(OBJECTS:.o=.d)

%.o: $(FW_DIRECTORY)/%.c
	$(compile)

%.o: $(FW_DIRECTORY)/%.S
	$(assemble)


clean:
	$(RM) $(OBJECTS) oc-fw.elf oc-fw.bin .*~ *~

.PHONY: all clean
