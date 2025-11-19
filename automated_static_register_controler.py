import pandas as pd
from collections import defaultdict
import argparse
from icecream import ic
import os

class Field:
    def __init__(self,
                reg_name:str,
                offset:str,
                name:str,
                bit_high:int,
                bit_low:int,
                access:str,
                reset:int,
                fifo:bool,
                desc: str
                ):
        self.reg_name = reg_name
        self.offset = offset
        self.name = name
        self.bit_high = bit_high
        self.bit_low = bit_low
        self.access = access
        self.reset = reset
        self.fifo = fifo
        self.desc = desc
    
    @property
    def width(self):
        return self.bit_high - self.bit_low + 1
    
class Register:
    def __init__(self,name :str, offset:str, access:str):
        self.name = name + "_" + access
        self.access = access
        self.offset = offset
        self.fields = []
    
    def add_field(self, field: Field):
        self.fields.append(field)
    
    @property
    def reset_value(self):
        value = 0
        for field in self.fields:
            mask = ((1 << field.width) - 1) << field.bit_low
            value = value | ((field.reset << field.bit_low) & mask)
        return value
    
    @property
    def fifo(self):
        any_fifo = False
        for field in self.fields:
            any_fifo = any_fifo | field.fifo
        return any_fifo
    
class RegisterController:
    def __init__(self,
                name: str,
                register_size_byte: int,
                addr_size_byte: int,
                reg_addr_widht: str,
                s_axi_data_width: int,
                s_axi_strb_width: str,
                s_axi_addr_widht: int,
                addr_lsb: str,
                opt_mem_addr_bits: str
                ):
        pass


def load_registers_from_excel(path,sheet="registers"):
    reg_df = pd.read_excel(path, sheet_name=sheet)
    regs = {}

    for _, row in reg_df.iterrows():
        #define the register first
        reg_name = str(row["register_name"])
        offset = str(row["adress_offset"])
        access = str(row["access"])
        reg_key = (reg_name, offset)
        

        if reg_key not in regs:
            regs[reg_key] = Register(reg_name, offset, access)

        #need fields for the default value and for the C header
        field = Field(
            reg_name = reg_name,
            offset = offset,
            name = str(row["field_name"]),
            bit_high = row["bit_high"],
            bit_low = row["bit_low"],
            access = str(row["access"]),
            reset = row["default_value"],
            fifo = bool(row["fifo"]),
            desc = row["description"]
        )

        regs[reg_key].add_field(field)

        regs_list = list(regs.values())
        regs_list.sort(key = lambda x: x.offset)

    return regs_list
    


def write_constant(regs_list:list):
    template_file = "templates/template_axi_static_register_controller.vhd"
    ip_file = "axi_static_register_controller/axi_register_controller_constant.vhd"
    with open(template_file, "r") as template, open(ip_file,"w") as file:
        for line in template:
            #write addr offset
            
            file.write(line)
            strip = line.strip()
            match strip:
                case "-- c: write register adrr with offset":
                    for reg in regs_list:
                        constant_addr = f'    constant REGISTER_{reg.name}_ADDR   : std_logic_vector(REG_ADDR_WIDTH -1 downto 0) := {reg.offset};\n'
                        file.write(constant_addr)
                
                case "-- c: write register default value in bit":
                    for reg in regs_list:
                        constant_default_value = f'    constant REGISTER_{reg.name}_DEFAULT: std_logic_vector(C_S_AXI_DATA_WIDTH -1 downto 0) := {f"\"{reg.reset_value:032b}\""};\n'
                        file.write(constant_default_value)
    return

def write_controller(regs_list:list):
    #check if the fifo process is needed
    template_file = "templates/template_axi_static_register_controller.vhd"
    ip_file = "axi_static_register_controller/axi_register_controller.vhd"
    any_fifo = False
    for reg in regs_list:
        any_fifo = any_fifo | reg.fifo

    with open(template_file, "r") as template, open(ip_file,"w") as file:
        for line in template:
            file.write(line)
            strip = line.strip()
            match strip:


                case "-- c: write read register":
                    for reg in regs_list:
                        if reg.access == 'R':
                            new_line = f'    axi_register_{reg.name.lower()}   : in std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);\n'
                            file.write(new_line)

                            if reg.fifo:
                                new_line = f'''    axi_register_{reg.name.lower()}_fifo_read: out std_logic;
    axi_register_{reg.name.lower()}_fifo_empty: in std_logic;\n'''
                                file.write(new_line)


                case "-- c: write write/read register":
                    for reg in regs_list:
                        if reg.access == 'WR':
                                new_line = f'    axi_register_{reg.name.lower()}   : in std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);\n'
                                file.write(new_line)
                                if reg.fifo:
                                    new_line = f'''    axi_register_{reg.name.lower()}_fifo_read: out std_logic;
    axi_register_{reg.name.lower()}_fifo_empty: in std_logic;\n'''
                                    file.write(new_line)


                case "-- c: write internal buffer":
                    for reg in regs_list:
                        new_line = f'  signal register_{reg.name.lower()}_q                        : std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);\n'
                        file.write(new_line)


                case "-- c: write internal signals":
                    for reg in regs_list:
                        new_line = f'  signal register_{reg.name.lower()}_internal                        : std_logic_vector(31 downto 0);\n'
                        file.write(new_line)


                case "-- c: write internal fifo signals":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'''  signal fifo_{reg.name.lower()}_read                        : std_logic := '0';
  signal fifo_{reg.name.lower()}_empty                     :std_logic;\n'''
                            file.write(new_line)


                case "-- c: write read register assignement":
                    for reg in regs_list:
                        if reg.access == 'R':
                            new_line = f"  register_{reg.name.lower()}_internal                   <= axi_register_{reg.name.lower()};\n"
                            file.write(new_line)
                        if reg.fifo:
                            new_line = f'''  fifo_{reg.name.lower()}_empty                            <= axi_register_{reg.name.lower()}_fifo_empty;
  axi_register_{reg.name.lower()}_fifo_read              <= fifo_{reg.name.lower()}_read;\n'''
                            file.write(new_line)


                case "-- c: write internal buffer assignement":
                    for reg in regs_list:
                        if reg.access == 'WR':
                            new_line = f'  axi_register_{reg.name.lower()}                   <= register_{reg.name.lower()}_internal;\n'
                            file.write(new_line)


                case "-- c: write write/read register buffer decoding":
                    for reg in regs_list:
                        if reg.access == 'WR':
                            new_line = f'  register_{reg.name.lower()}_internal                   <= register_{reg.name.lower()}_q(31 downto 0);\n'
                            file.write(new_line)


                case "-- c: write default value assignement":
                    for reg in regs_list:
                        new_line = f'       register_{reg.name.lower()}_q                        <= REGISTER_{reg.name}_DEFAULT;\n'
                        file.write(new_line)


                case "-- c: write write logic":
                    for reg in regs_list:
                        new_line = f'''
        when REGISTER_{reg.name}_ADDR(ADDR_LSB + OPT_MEM_ADDR_BITS downto ADDR_LSB) => 
            for byte_index in 0 to C_S_AXI_STRB_WIDTH - 1 loop
              if(S_AXI_WSTRB(byte_index)='1') then
                register_{reg.name.lower()}_q((byte_index * 8) + 7 downto byte_index * 8) <= S_AXI_WDATA((byte_index * 8) + 7 downto byte_index * 8);
              end if;
            end loop;\n
'''
                        file.write(new_line)

                case "-- c: internal buff in process & read addr":
                    for reg in regs_list:
                        new_line = f'                  register_{reg.name.lower()}_internal,\n'
                        file.write(new_line)


                case "-- c: write read logic":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'''
    when REGISTER_{reg.name}_ADDR(ADDR_LSB + OPT_MEM_ADDR_BITS downto ADDR_LSB) =>
        axi_rdata_s <= register_{reg.name.lower()}_internal;
        if (fifo_{reg.name.lower()}_empty = '0') then
          rresp_s     <= '1';
        end if;\n
'''
                            file.write(new_line)
                        else:
                            new_line = f'''
    when REGISTER_{reg.name}_ADDR(ADDR_LSB + OPT_MEM_ADDR_BITS downto ADDR_LSB) =>
        axi_rdata_s <= register_{reg.name.lower()}_internal;\n
        '''
                            file.write(new_line)


                case "-- c: if fifo write fifo read logic":
                    if not any_fifo:
                        file.write("end rtl;\n")
                        break
                    else:
                        print("fifo logic")
                        
                case "-- c: write fifo rst":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'             fifo_{reg.name.lower()}_read <= \'0\';\n'
                            file.write(new_line)


                case "-- c: write fifo read logic":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'             fifo_{reg.name.lower()}_read <= \'0\';\n'
                            file.write(new_line)
                
                case "-- c: write fifo read reg addr":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'''
                when REGISTER_{reg.name}_ADDR(ADDR_LSB + OPT_MEM_ADDR_BITS downto ADDR_LSB) =>
                    if (fifo_{reg.name.lower()}_empty = '0') then
                      fifo_{reg.name.lower()}_read <= '1';  -- one-cycle pulse
                    end if;\n
'''
                            file.write(new_line)

                case "-- c: write the default":
                    for reg in regs_list:
                        if reg.fifo:
                            new_line = f'                       fifo_{reg.name.lower()}_read <= \'0\';\n'
                            file.write(new_line)
                
    return

def main():
    parser = argparse.ArgumentParser(description="Automate the building of a axi_static_register_controller module from an excel summary file")
    parser.add_argument("-f", "--file", type=str, required=True, help="Excel file to build the module from")
    args = parser.parse_args()

    regs_list = load_registers_from_excel(args.file)
    if len(regs_list) > 0:
        print(f"{len(regs_list)} in the file")
        for reg in regs_list:
            print(f"{reg.name} : {reg.offset} ; {reg.reset_value}")
    os.makedirs("axi_static_register_controller",exist_ok=True)
    print(regs_list)
    write_constant(regs_list)
    write_controller(regs_list)

    return


if __name__ == "__main__":
    main()


    
