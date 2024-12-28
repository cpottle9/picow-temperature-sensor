#
# Exploring PICO low power capabilities using
# die temperature ADC instead of external I2C temperature
#
from machine import Pin, ADC, reset, freq, mem32

# Set system clock to lowest value that works
# Below 64 MHZ wifi does not seem to work.

FREQ_HIGH = const(64*1000*1000)
freq(FREQ_HIGH)

from time import sleep_ms
from micropython import const
from network import WLAN, STA_IF

import rp2

from umqttsimple import MQTTClient
import scratch
from watchdog import WATCHDOG
from mcp9808 import MCP9808
from sys import exit
from math import fabs

from secrets import COUNTRY, WIFI_SSID, WIFI_PASSWORD, MQTT_IPADDR, CLIENT_ID, MQTT_USERID, MQTT_PASSWORD

from power_ctrl_2040 import PowerCtrl
pwr = PowerCtrl()

# Restore power control to initial state. Makes testing from REPL or thonny easier.
pwr.restore()

# Roughly the same as light sleep
pwr.disable_while_sleeping_all_but(
    # TIMER is required so time.sleep_ms will work
    pwr.EN1_CLK_SYS_TIMER,
    # USB enabled so I can debug from REPL or thonny
    pwr.EN1_CLK_USB_USBCTRL,
    pwr.EN1_CLK_SYS_USBCTRL,
    pwr.EN0_CLK_SYS_PLL_USB
    # everything else is disabled while sleeping.
)

# MCP9808 temperature sensor connected to I2C0
# cyw43 (WIFI chip) needs DMA and PIO1
# ADC needed to read system voltage

pwr.disable_while_awake(
    pwr.EN0_CLK_SYS_SRAM3,
    pwr.EN0_CLK_SYS_SRAM2,
    pwr.EN0_CLK_SYS_SPI0,
    pwr.EN0_CLK_PERI_SPI0,
    pwr.EN0_CLK_SYS_SPI1,
    pwr.EN0_CLK_PERI_SPI1,
    pwr.EN0_CLK_SYS_PWM,
    pwr.EN0_CLK_SYS_JTAG,
    pwr.EN0_CLK_SYS_PIO0,
    pwr.EN0_CLK_SYS_I2C1,
    pwr.EN1_CLK_SYS_UART0,
    pwr.EN1_CLK_PERI_UART0,
    pwr.EN1_CLK_SYS_UART1,
    pwr.EN1_CLK_PERI_UART1,
    pwr.EN1_CLK_SYS_TBMAN
)
try :
    # Try PICO_W pin first, this will power up the cyw43 wifi chip
    usb_present=Pin("WL_GPIO2").value()
    # So, power it down after
    rp2.country(COUNTRY)
    WLAN(STA_IF).deinit()
except ValueError :
    usb_present=Pin("GPIO24").value()

print('usb_present: ' , usb_present)

if not usb_present :
    # no USB so disable them too.
    pwr.disable_while_sleeping(
        pwr.EN1_CLK_USB_USBCTRL,
        pwr.EN1_CLK_SYS_USBCTRL,
        pwr.EN0_CLK_SYS_PLL_USB
    )
    pwr.disable_while_awake(
        pwr.EN1_CLK_USB_USBCTRL,
        pwr.EN1_CLK_SYS_USBCTRL,
        pwr.EN0_CLK_SYS_PLL_USB
    )
    # power down USB dual ported SRAM
    __SYSCFG_BASE = const(0x40004000)
    __MEMORYPOWERDOWN = const(__SYSCFG_BASE+0x18)
    __MEMORYPOWERDOWN_USB   = const(0x40)
    mem32[__MEMORYPOWERDOWN] |= __MEMORYPOWERDOWN_USB

#print(pwr)

wlan = None

last_feeder = 0
wdt = WATCHDOG(8388) # Note: My watchdog class disables watchdog in __init__

# Experiment, keep PIO1 and DMA turned off while wifi is not active.

def connectWifi() :
    pwr.enable_while_awake(pwr.EN0_CLK_SYS_DMA, pwr.EN0_CLK_SYS_PIO1)
    global wlan
    wdt.feed(0xff00)
    rp2.country(COUNTRY)
    wlan = WLAN(STA_IF)
    wdt.feed(0xff01)

    # Aggressive power saving mode. Will reduce throughput.
    wlan.config(pm = 0xa11c81) 
    
    wdt.feed(0xff02)
    wlan.active(True)
    wdt.feed(0xff03)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    wdt.feed(0xff04)
    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        print('wlan status: ', wlan.status())
        max_wait -= 1
        wdt.feed(0xff10)
        sleep_ms(1000)
        
    wdt.feed(0xff20)
        
    print('wlan status: ', wlan.status())
    # Handle connection error
    if wlan.status() != 3:
        my_fail('Wifi connect failed', 2)
    else:
        return wlan.ifconfig()

def disconnectWiFi() :
    global wlan
    wlan.disconnect()
    wlan.active(False)
    wlan.deinit()
    wlan = None
    pwr.disable_while_awake(pwr.EN0_CLK_SYS_DMA,pwr.EN0_CLK_SYS_PIO1)

def my_fail(reason, cause) :
    global wdt
    wdt.disable()
    print('Reason: ', reason)
    #
    # Scratch register 7 contains fail data since last
    # Power cycle.
    # Bits 0 to 23 are a mask. Each bit position corresponds
    # to a number of flashes requested.
    #
    # Bits 24 to 30 are a count of the total number of fails
    # since the last power up.
    # Value will be 0 to 127 and will wrap-around.
    #
    # Bit 31 not used to avoid sign issues.
    #
    scratch_value = scratch.get_scratch(scratch.RESTART_SCRATCH_INDEX)
    error_mask = scratch_value & 0x0ffffff
    error_count = (scratch_value >> 24) &0x0ff
    error_count += 1
    error_count &= 0x7f
    error_mask |= (1<<cause) & 0x0ffffff
    scratch_value = (error_count << 24) | error_mask

    scratch.set_scratch(scratch.RESTART_SCRATCH_INDEX, scratch_value)
    # Removed led flash. Rely on publishing errors
    raise RestartNeededException


def convert_vsys(raw) :
   conversion_factor = 3 * 3.3 / 65535
   return "%.2f" % (raw *conversion_factor)

#
# Call only when wifi is inactive
#

def get_vsys_raw():
   try:
      # Make sure pin 25 is high.
      Pin(25, mode=Pin.OUT, pull=Pin.PULL_DOWN).high()
      
      # Reconfigure pin 29 as an input.
      Pin(29, Pin.IN)
      
      vsys = ADC(29)
      return vsys.read_u16()
   
   finally:
      # Restore the pin state and possibly reactivate WLAN
      Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)

i2c = machine.I2C(0,sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
mcp9808 = MCP9808(i2c)

def get_temp_raw() :
    return mcp9808.raw_temperature()

def convert_temp_raw(raw) :
    return "%.1f" % (mcp9808.temp_convert(raw))


class RestartNeededException(Exception) :
    # Raised when application code fails
    pass

if wdt.caused_reboot() :
    try :
        last_feeder = scratch.get_scratch(scratch.FEEDER_SCRATCH_INDEX)

        my_fail("Watchdog restart", 0)
        # Exception  in my_fail will be caught by the except.
        
    except :
        # continue execution but sleep for a bit 
        sleep_ms(60000)
        pass

topic_pub = 'sensors/home/PicoW/P/C2/temperature_C'
topic_vsys_pub = 'sensors/home/PicoW/P/C2/vsys'
topic_last_error_pub = 'sensors/home/PicoW/P/C2/last_error'
topic_feeder_pub = 'sensors/home/PicoW/P/C2/feeder'

def mqtt_connect() :
    try :
        client = MQTTClient(CLIENT_ID, MQTT_IPADDR, user=MQTT_USERID, password=MQTT_PASSWORD, keepalive=60)
        client.connect()
        return client
    except :
        my_fail('Mqtt connect failed', 3)
    return client

def publish(temp_raw, vsys_raw) :
    try :
        temp_data = convert_temp_raw(temp_raw)
        client.publish(topic_pub, msg=temp_data)
        if vsys_raw != 0 :
            vsys_data = convert_vsys(vsys_raw)
            client.publish(topic_vsys_pub, msg=vsys_data)
        last_error = scratch.get_scratch(scratch.RESTART_SCRATCH_INDEX)
        if last_error != 0 :
            client.publish(topic_last_error_pub, msg=hex(last_error))
        feeder_index = scratch.get_scratch(scratch.FEEDER_SCRATCH_INDEX)
        if last_feeder != 0 :
            client.publish(topic_feeder_pub, msg=hex(last_feeder))
    except: 
        my_fail('Mqtt publish failed', 4)

        
MINUTE_MS = const(60000 - 300) # one minute less the time get_temp_raw() takes

try :
    # Use raw temperature from scratch as long as it is not 0
    temp_raw = scratch.get_scratch(scratch.TEMP_SCRATCH_INDEX)
    if temp_raw == 0 :
        temp_raw = get_temp_raw()

    vsys_raw = scratch.get_scratch(scratch.VSYS_SCRATCH_INDEX)
        
    while True :

        wdt.enable()
        wdt.feed(2)
        wifi_connection = connectWifi()
        wdt.feed(3)
        client = mqtt_connect()
        wdt.feed(4)
        publish(temp_raw, vsys_raw)
        wdt.feed(5)
        sleep_ms(750)
        client.disconnect()
        wdt.feed(6)
        sleep_ms(500)
        disconnectWiFi()
        wdt.disable()
        sleep_ms(750)
        
        # Make sure always sleep_ms at least once
        sleep_ms(MINUTE_MS)
        
        # For first 5 minutes only restart if temperature delta is at least 0.2 degrees.
        # This loop uses floating point. Oh well...
        loop_count = 0
        converted_temp = float(convert_temp_raw(temp_raw))
        new_temp_raw = get_temp_raw()    
        while loop_count < 5 and fabs(float(convert_temp_raw(new_temp_raw)) - converted_temp) < 0.2:
            sleep_ms(MINUTE_MS)
            loop_count += 1
            new_temp_raw = get_temp_raw()

        # For the next 5 minutes restart on any temperature change
        # We can do string compares here which should be cheaper.
        
        loop_count = 0
        converted_temp = convert_temp_raw(temp_raw) 
        while loop_count < 5 and convert_temp_raw(new_temp_raw) == converted_temp :
            sleep_ms(MINUTE_MS)
            loop_count += 1
            new_temp_raw = get_temp_raw()
            
        vsys_raw = get_vsys_raw()
        temp_raw = new_temp_raw
        # Record temp_raw and vsys_raw in watchdog scratch memory
        scratch.set_scratch(scratch.VSYS_SCRATCH_INDEX, vsys_raw)
        scratch.set_scratch(scratch.TEMP_SCRATCH_INDEX, temp_raw) 
   
except RestartNeededException as e:
    # Mostly we get here if the MQTT server or WIFI is down.
    # Probably caused by a power outage ;-(.
    # Do sleep_ms for a minute so we don't waste battery.
    # Then reset() in case it was a bug on the PICO.
    wdt.disable()
    print('Resetting')
    print(e)
    # restore power to initial state
    pwr.restore()
    sleep_ms(60000)
    # Do full reset to cleanup and hopefully resolve issue.
    reset()

