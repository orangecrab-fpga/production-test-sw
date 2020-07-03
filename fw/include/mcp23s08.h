// Copyright 2020 Gregory Davill <greg.davill@gmail.com> 
#ifndef MCP23S08_H__
#define MCP23S08_H__

#include <stdbool.h>
#include <stdint.h>


void mcp23s08_write(uint8_t reg, uint8_t data);
void mcp23s08_read(uint8_t reg, uint8_t* data);

#endif