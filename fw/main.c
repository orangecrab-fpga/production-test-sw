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
 	printf("Info: firmware build date="__DATE__ " " __TIME__ " \n\n");

 	printf("Info: Migen git sha1="MIGEN_GIT_SHA1"\n");
 	printf("Info: LiteX git sha1="LITEX_GIT_SHA1"\n");
 	printf("\n");

	/* Init Memory */
	int sdr_ok = sdrinit();
	

	



	return 0;
}
