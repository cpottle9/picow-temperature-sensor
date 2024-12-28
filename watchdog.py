#
# Wrapper for the standard watchdog timer with
# added behavior to disable and re-enable the watchdog timer.
#
# I need this because I want the watchdog disabled during light sleeps.
#

from micropython import const
from machine import mem32, WDT

import scratch

class WATCHDOG :

    WDT_BASE = const(0x40058000)

    WDT_CTRL   = const(WDT_BASE + 0x00)
    WDT_REASON = const(WDT_BASE + 0x08)
    
    #
    # Bitmasks in CTRL register to enable/disable the watchdog time
    #
    
    WDT_CTRL_ENABLE_MASK = const(0b0100_0000_0000_0000_0000_0000_0000_0000)
    WDT_REASON_MASK      = const(0b0000_0000_0000_0000_0000_0000_0000_0001)

    def __init__(self, timeout_ms) :
        self.__wdt = WDT(timeout=timeout_ms)
        self.disable()

    def feed(self, feeder_index) :
        self.__wdt.feed()
        scratch.set_scratch(scratch.FEEDER_SCRATCH_INDEX, feeder_index)

    def enable(self) :
        # Feed the timer before enabling to ensure the app gets a full timeout.
        self.feed(0)
        mem32[WDT_CTRL] |= WDT_CTRL_ENABLE_MASK
                
    def disable(self) :
        mem32[WDT_CTRL] &= ~WDT_CTRL_ENABLE_MASK

    #
    # Specifically did the reboot happen because
    # the watchdog expired?
    # 
    def caused_reboot(self) :
        reason = mem32[WDT_REASON]
        return (reason & WDT_REASON_MASK) != 0

