// Copyright 2020 Gregory Davill <greg.davill@gmail.com>
#include <asense.h>
#include <generated/csr.h>

uint32_t adc_read_channel(uint8_t chan)
{
    /* Configure mux and start conversion */
    asense_control_write(((chan) << CSR_ASENSE_CONTROL_CHAN_OFFSET) |
            ( 1 << CSR_ASENSE_CONTROL_START_OFFSET));

    /* Wait until conversion complete */
    while(asense_status_read() != 1);

    /* Return result */
	return asense_result_read();
}