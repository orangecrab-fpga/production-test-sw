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

#include <i2c.h>

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
	i2c_reset();

	char data[2] = {0x00, 0b00001010};
	bool ret = i2c_write(0b1001000, 2, data, 2);
	printf("Write i2c: Reset. %u\n", ret);

	/* Wait for it to reset */
	msleep(10);

	data[0] = 0;
	data[1] = 0;
	ret = i2c_read(0b1001000, 2, data, 2, true);
	printf("Read i2c: 0x%02x%02x %d\n", data[0], data[1], ret);

	if(((data[0] << 2 | data[1] >> 6) & 0b111111) == 0b001100){
		printf("Correct ID for DAC53608 (0b001100)\n");
	}



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
