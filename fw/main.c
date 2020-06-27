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

#include <sleep.h>
#include <flash-spi.h>


void print_buffer(uint8_t* ptr, uint8_t len){
	for(int i = 0; i < len; i++){
		printf("%s\"0x%02x\"",i > 0 ? "," : 0, ptr[i]);
	}
}

int main(int i, char **c)
{	

	rgb_config_write(0);
	rgb_r_write(250);
	rgb_g_write(0);
	rgb_b_write(0);
	rgb_div_m_write(100000);

	irq_setmask(0);
	irq_setie(1);

	uart_init();

	printf("\n");

	printf("Hello from OrangeCrab! o/ \n");
 	printf("{\"firmware build date\":\""__DATE__ "\", \"firmware build time\": \"" __TIME__ "\"}\n");

 	printf("{\"migen sha1\":\""MIGEN_GIT_SHA1"\"}\n");
 	printf("{\"litex sha1\":\""LITEX_GIT_SHA1"\"}\n");

	/* Init Memory */
	int sdr_ok = sdrinit();

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


	return 0;
}
