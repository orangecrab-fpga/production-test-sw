// Copyright 2020 Gregory Davill <greg.davill@gmail.com> 
#include <mcp23s08.h>
#include <generated/csr.h>


void mcp23s08_write(uint8_t reg, uint8_t data){
    /* Ensure SPI is IDLE */
    while(spi_status_read() == 0);

    /* Select CS for the mcp23s08 */
    spi_cs_write(1);

    /* Load control byte into shift register */
    uint8_t ctrl = 0b01000000;
    spi_mosi_write((ctrl << 16) | (reg << 8) | data);

    /* Transmit 24 bits */
    spi_control_write((24 << CSR_SPI_CONTROL_LENGTH_OFFSET) | (1 << CSR_SPI_CONTROL_START_OFFSET));

    /* Wait until SPI is IDLE */
    while(spi_status_read() == 0);

    /* release CS for the mcp23s08 */
    spi_cs_write(0);
}



void mcp23s08_read(uint8_t reg, uint8_t* data){
    /* Ensure SPI is IDLE */
    while(spi_status_read() == 0);

    /* Select CS for the mcp23s08 */
    spi_cs_write(1);

    /* Load control byte into shift register */
    uint8_t ctrl = 0b01000001;
    spi_mosi_write((ctrl << 16) | (reg << 8));

    /* Transmit 24 bits */
    spi_control_write((24 << CSR_SPI_CONTROL_LENGTH_OFFSET) | (1 << CSR_SPI_CONTROL_START_OFFSET));

    /* Wait until SPI is IDLE */
    while(spi_status_read() == 0);

    *data = spi_miso_read() & 0xFF;

    /* release CS for the mcp23s08 */
    spi_cs_write(0);
}
