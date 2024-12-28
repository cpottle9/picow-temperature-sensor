#
# Class to read temperature from mcp9808
#
# Uses all default settings
#

# Reports errors by exceptions


import machine
from micropython import const
from time import sleep_ms

class MCP9808 :
    
    __MCP9808_DEFAULT_ADDRESS = const(0x18)
    __MCP9808_REG_CONFIG = const(0x01)
    __MCP9808_REG__TEMP = const(0x05)
    __MCP9808_REG_MANUFACTURER_ID = const(0x06)
    __MCP9808_REG_DEVICE_ID = const(0x07)
    
    __MCP9808_MANUFACTURER_ID = const(0x0054)
    __MCP9808_DEVICE_ID = const(0x0400)

    def reg_read16(self, reg_index) :
        data = self.i2c.readfrom_mem(self.address, reg_index, 2)
        return data[0] * 256 + data[1]
    
    def reg_write16(self, reg_index, value) :
        data = bytearray(2)
        data[0] = (value >> 8) & 0x00FF
        data[1] = value & 0x00FF
        self.i2c.writeto_mem(self.address, reg_index, data)

    def reg_write8(self, reg_index, value) :
        data = bytearray(1)
        data[0] = value
        self.i2c.writeto_mem(self.address, reg_index, data)
        
    def __init__(self, i2c, device_address=__MCP9808_DEFAULT_ADDRESS) :
        self.i2c=i2c
        device_found = False
        
        # Scan for all devices on the I2C
        devices=self.i2c.scan()
        for device in devices :
            if device == device_address :
                device_found = True
                break

        # Exit if specified device is not found
        assert device_found == True, "Device not found"
            
        self.address=device_address
        
        # Verify manufacturer ID and device ID
        manufacturer_id = self.reg_read16(__MCP9808_REG_MANUFACTURER_ID)
        assert manufacturer_id == __MCP9808_MANUFACTURER_ID, "Incorrect Manufacturer ID"
            
        device_id = self.reg_read16(__MCP9808_REG_DEVICE_ID)
        assert device_id == __MCP9808_DEVICE_ID, "Incorrect Device ID"
        self.set_shutdown()
        
    def temp_convert(self, raw_temp) :
        # Internal function to convert temperature given by the sensor
        
        # Clear flags from the value
        temp = raw_temp & 0x1FFF
        if (temp & 0x1000) == 0x1000 :
            temp = temp & 0x0FFF
            return (temp / 16.0) - 256
        return temp / 16.0  

    def raw_temperature(self) :
        self.clr_shutdown()
        # Sample conversion takes 250 ms
        # add a little to be safe
        sleep_ms(300)
        temp_raw = self.reg_read16(__MCP9808_REG__TEMP)
        self.set_shutdown()
        return temp_raw
    
    def temperature(self) :
        raw_temp = self.raw_temperature()
        return self.temp_convert(raw_temp)
    
    def set_shutdown(self) :
        config = self.reg_read16(__MCP9808_REG_CONFIG)
        config = config | 0x0100
        self.reg_write16(__MCP9808_REG_CONFIG, config)
        
    def clr_shutdown(self) :
        config = self.reg_read16(__MCP9808_REG_CONFIG)
        config = config & (~0x0100)
        self.reg_write16(__MCP9808_REG_CONFIG, config)
        
