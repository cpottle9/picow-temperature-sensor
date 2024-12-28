#
# Provide access to RP2040 watchdog scratchpad registers
# SCRATCH0-3
#
# The bootrom uses SCRATCH4-7
#
# I beleive these are unused by Raspberry PI PICO micropython.
#
# Note: Each register can hold 32 bits.
#
# Values in the scratch register will persist over a
# machine.reset()
#
# On power up the scratch registers are 0.

from machine import mem32
from micropython import const

RESTART_SCRATCH_INDEX = const(0)
VSYS_SCRATCH_INDEX    = const(1)
TEMP_SCRATCH_INDEX    = const(2)
FEEDER_SCRATCH_INDEX  = const(3)

scratch_base=const(0x40058000+0x0c)
    
def get_scratch(index) :
    if index < 0 or index > 3:
        raise IndexError("index must be 0<=index<=3")
    return mem32[scratch_base+index*4]

def set_scratch(index,value) :
    if index < 0 or index > 3:
        raise IndexError("index must be 0<=index<=3")
    mem32[scratch_base+index*4]=value

def dump_scratch() :
    string = ''
    for index in range(0, 3) :
        word = get_scratch(index)
        string = '%s%08x ' % (string, word)
    return string
    
        
