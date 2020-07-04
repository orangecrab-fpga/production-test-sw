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

#include <sleep.h>
#include <flash-spi.h>


void print_buffer(uint8_t* ptr, uint8_t len){
	for(int i = 0; i < len; i++){
		printf("%s0x%02x\"",i > 0 ? ",\"" : "\"", ptr[i]);
	}
}

void test_fail(const char* str){
	printf("Test Fail %s :(\n", str);

	while(1);
}

int main(int i, char **c)
{
	/* Setup IRQ, needed for UART */
	irq_setmask(0);
	irq_setie(1);
	uart_init();


	printf("\n");

	printf("Hello from OrangeCrab! o/ \n");
	printf("{\"firmware build date\":\""__DATE__ "\", \"firmware build time\": \"" __TIME__ "\"}\n");

	printf("{\"migen sha1\":\""MIGEN_GIT_SHA1"\"}\n");
	printf("{\"litex sha1\":\""LITEX_GIT_SHA1"\"}\n");


	//msleep(100);

	/* Init Memory */
	int sdr_ok = sdrinit();
	if(sdr_ok == 0){
		test_fail("DDR3 Init failure");
	}

	//self_reset_out_write(0xAA550001);

	/* Check for SPI FLASH */
	spiInit();
	unsigned char buf[8] = {0};
	spiId(buf);

	printf("{\"spi id\":[");
	print_buffer(buf, 5);
	printf("]}\n");

	// Check Flash UUID
	spi_read_uuid(buf);
	printf("{\"spi uuid\":[");
	print_buffer(buf, 8);
	printf("]}\n");

	/* Configure I2C, read ID code from DAC */
	dac_reset();
	dac_read_id();

	/* Release I/O control over DAC */
	/* ~CLR=1 to avoid forcing DAC clear */
	/* ~LDAC=0 for async output mode */
	gpio_oe_write(1 << CSR_GPIO_OUT_DAC_CLR_OFFSET | 1 << CSR_GPIO_OUT_DAC_LDAC_OFFSET);
	gpio_out_write(1 << CSR_GPIO_OUT_DAC_CLR_OFFSET | 0 << CSR_GPIO_OUT_DAC_LDAC_OFFSET);



	printf("GPIO test started\n");
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
			printf("%X : %X \n", io_data, gpio_synd);
			if (io_data != gpio_synd)
				test_fail("GPIO Test Failure");

			/* rotate the bits */
			io_data = (io_data << 1) & 0x3f;
			if (j%2) io_data |= 1;
		}
	}
	printf("\nGPIO test passed\n");

	/* ramp up counts to DAC outputs */
	for(int i = 0; i < 6; i++) {
		for(int j = 0; j < 0x0fff; j+=0x100) {
			printf("DAC%d: %d, ",i, j);
			dac_write_channel(i, j);

			msleep(2);

			/* Perform ADC measurement */
			while(asense_status_read() != 1);
			asense_control_write(((1 + i) << CSR_ASENSE_CONTROL_CHAN_OFFSET) |
				 ( 1 << CSR_ASENSE_CONTROL_START_OFFSET));

			while(asense_status_read() != 1);

			printf("ADC: %d\n", asense_result_read());


		}
	}
	printf("\n");

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

	/*  */

	return 0;
}
