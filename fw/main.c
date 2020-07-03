/* This file is part of OrangeCrab-test
 *
 * Copyright 2020 Gregory Davill <greg.davill@gmail.com> 
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


	/* Read/write/read to validate that SPI io expander is present */
	uint8_t io_data = 0;
	mcp23s08_read(6, &io_data);
	printf("Read: %02x - ", io_data);

	io_data ^= 0xAA;
	mcp23s08_write(6, io_data);
	printf("Write: %02x - ", io_data);
	
	io_data = 0;
	mcp23s08_read(6, &io_data);
	printf("Read: %02x\n", io_data);



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
