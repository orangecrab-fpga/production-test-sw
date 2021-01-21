/* This file is part of OrangeCrab-test
 *
 * Copyright 2020 Gregory Davill <greg.davill@gmail.com> 
 * Copyright 2020 Michael Welling <mwelling@ieee.org>
 */

#include <stdlib.h>
#include <stdio.h>

#include <generated/csr.h>
#include <generated/mem.h>
#include <generated/git.h>

#include <irq.h>
#include <uart.h>

#include <dac53608.h>
#include <mcp23s08.h>
#include <asense.h>

#include <sleep.h>
#include <flash-spi.h>


void print_buffer(uint8_t* ptr, uint8_t len){
	for(int i = 0; i < len; i++){
		printf("%02x ", ptr[i]);
	}
}

void test_fail(const char* str){
	printf("%s\n", str);

	while(1);
}

int main(int i, char **c)
{
	/* Setup IRQ, needed for UART */
	irq_setmask(0);
	irq_setie(1);
	uart_init();


	printf("\n");

	printf("Info:Hello from OrangeCrab! o/ \n");
	printf("Info:build_date "__DATE__" "__TIME__ "\n");

	printf("Info:test-repo "REPO_GIT_SHA1"\n");
	printf("Info:migen "MIGEN_GIT_SHA1"\n");
	printf("Info:litex "LITEX_GIT_SHA1"\n");




	/* Check for SPI FLASH */
	printf("Test:SPI-FLASH, Start\n");

	spiInit();
	unsigned char id[8] = {0};
	unsigned char uuid[8] = {0};
	spiId(id);

	printf("Info:SPI-FLASH-ID=");
	print_buffer(id, 5);
	printf("\n");
	if(id[0] != 0xef |
	   id[1] != 0x17 |
	   id[2] != 0xef |
	   id[3] != 0x40 |
	   id[4] != 0x18 ){
		   test_fail("Test:SPI-FLASH|Fail");
	   }

	// Check Flash UUID
	spi_read_uuid(uuid);
	printf("Info:SPI-FLASH-UUID=");
	print_buffer(uuid, 8);
	printf("\n");
	
	printf("Test:SPI-FLASH|Pass\n");

	printf("Test:DDR3 Start\n");
	/* Init Memory */
	int sdr_ok = sdram_init();
	if(sdr_ok == 0){
		test_fail("Test:DDR3|Fail");
		//self_reset_out_write(0xAA550001);
	}
	printf("Test:DDR3|Pass\n");

	/* Configure I2C, read ID code from DAC */
	printf("Test:I2C, Start\n");
	dac_reset();
	if(dac_read_id() == false){
		test_fail("Test:I2C|Fail");
	}
	printf("Test:I2C|Pass\n");

	/* Release I/O control over DAC */
	/* ~CLR=1 to avoid forcing DAC clear */
	/* ~LDAC=0 for async output mode */
	gpio_oe_write(1 << CSR_GPIO_OUT_DAC_CLR_OFFSET | 1 << CSR_GPIO_OUT_DAC_LDAC_OFFSET);
	gpio_out_write(1 << CSR_GPIO_OUT_DAC_CLR_OFFSET | 0 << CSR_GPIO_OUT_DAC_LDAC_OFFSET);



	printf("Test:GPIO, Start\n");
	/*set all MCP GPIOs to output */
	uint8_t io_data = 0;
	mcp23s08_write(0, io_data);

	/* walking 1s and 0s on the MCP GPIOs */
	for(int j = 0; j < 4; j++)
	{
		io_data = (j%2) ? 0x3e : 0x01;

		for(int i = 0; i < 6; i++) {
			mcp23s08_write(0x9, io_data);
			/* read all FPGA GPIO */
			uint32_t gpio_synd = gpio_in_read();

			/* munge the appropriate bits together so they match the MCP stuffing */
			gpio_synd = ((gpio_synd >> 6) & 0x1) | ((gpio_synd >> 8) & 0x3e);

			/* print and check for match */
			//printf("%X : %X \n", io_data, gpio_synd);
			if (io_data != gpio_synd)
				test_fail("Test:GPIO|Fail");

			/* rotate the bits */
			io_data = (io_data << 1) & 0x3f;
			if (j%2) io_data |= 1;
		}
	}
	printf("\nTest:GPIO|Pass\n");

	/* Connect load to the battery connector, upto 250ms before charger detects this. */
	mcp23s08_write(0x9, 1 << 7);


	printf("Test:ADC, Start\n");
	/* ramp up counts to DAC outputs */
	for(int i = 0; i < 6; i++) {
		for(int j = 0; j < 0x0fff; j+=0x80) {
			printf("CH=%d, DAC=%d, ",i, j);
			dac_write_channel(i, j);
			/* Perform ADC measurements */
			printf("ADC=%ld\n", adc_read_channel(i+1));
		}
		/* Disable channel  once tested */
		dac_write_channel(i, 0);
	}

	printf("ADC-GND=%ld\n", adc_read_channel(0));
	printf("ADC-VREF=%ld\n", adc_read_channel(7));
	printf("ADC-3V3=%ld\n", adc_read_channel(8));
	printf("ADC-1V35=%ld\n", adc_read_channel(12));
	printf("ADC-2V5=%ld\n", adc_read_channel(13));
	printf("ADC-1V1=%ld\n", adc_read_channel(14));
	printf("ADC-VBAT=%ld\n", adc_read_channel(15));
	printf("Test:ADC, Finish\n");

	printf("Test:BATT, Start\n");
	/* Battery test */
	/* Enable current sink + Dummy Battery, takes ~20ms for charger to react */
	printf("BATT: Enable Current Sink\n");
	printf("BATT: Enable Dummy Battery\n");
	mcp23s08_write(0x9, 1 << 6 | 1 << 7);
	for(int i = 0; i < 20; i++){
		msleep(1);
		printf("ADC-VBAT=%ld\n", adc_read_channel(15));
	}

	printf("BATT: Remove Dummy Battery\n");
	/* Enable current sink */
	mcp23s08_write(0x9, 1 << 7);
	for(int i = 0; i < 20; i++){
		msleep(1);
		printf("ADC-VBAT=%ld\n", adc_read_channel(15));
	}

	/* Enable current sink */
	printf("BATT: Remove Current Sink\n");
	mcp23s08_write(0x9, 0);
	for(int i = 0; i < 20; i++){
		msleep(1);
		printf("ADC-VBAT=%ld\n", adc_read_channel(15));
	}
	printf("Test:BATT, Finish\n");

	/* Test of LED GPIO */
	uint8_t led_gpio_patterns[] = {0x0, 0x1, 0x2, 0x4, 0x7};
	for(int i = 0; i < sizeof(led_gpio_patterns); i++){
		uint8_t out_pattern = led_gpio_patterns[i];
		gpio_led_out_write(0);
		gpio_led_oe_write(out_pattern);

		msleep(1);

		uint8_t read_pattern = gpio_led_in_read();

		/* Print values */
		printf("{%01X:%01X}\n",out_pattern, read_pattern);
	}

	
	gpio_led_out_write(~2);

	printf("Test:DONE, Finish\n");
	msleep(50);
	while(1){
		msleep(10);
	}

	return 0;
}
