/* This file is part of OrangeCrab-test
 *
 * Copyright 2020 Gregory Davill <greg.davill@gmail.com> 
 */

#include <generated/csr.h>
#include <irq.h>
#include <uart.h>

void isr(void);
void isr(void)
{
	unsigned int irqs;
	
	irqs = irq_pending() & irq_getmask();
	
	if(irqs & (1 << UART_INTERRUPT))
		uart_isr();
}
