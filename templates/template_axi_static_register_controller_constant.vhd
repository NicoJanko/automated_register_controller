library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package axi_static_register_controller_constant is

    -- Registers parameters : 
    constant REGISTER_SIZE_BYTES : natural := 4;
    constant ADDRESS_SIZE_BYTES  : natural := 2;
    constant REG_ADDR_WIDTH      : natural := ADDRESS_SIZE_BYTES * 8;
    constant C_S_AXI_DATA_WIDTH  : natural := 32;    
    constant C_S_AXI_STRB_WIDTH  : natural := C_S_AXI_DATA_WIDTH / 8;
    constant C_S_AXI_ADDR_WIDTH  : natural := 32;
    constant ADDR_LSB            : natural := (C_S_AXI_DATA_WIDTH / 32) + 1;
    constant OPT_MEM_ADDR_BITS   : natural := 16 - ADDR_LSB - 1;
    

    -- Address list : 
    -- c: write register adrr with offset
    

    -- Reg default value : 
    -- c: write register default value in bit
    
    






end package;
