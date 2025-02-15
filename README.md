# MQTT client on Raspberry PI PICO W

This is a simple MQTT client running on a Raspberry PI PICO W.
It periodically reads temperature from an [mcp9808](https://www.adafruit.com/product/1782) sensor and publishes the reading to an MQTT server.

It is intended to run from battery.
My hardware setup has it running from 2 AA alkaline batteries.
Depending on the battery brand used it runs 1 or 2 weeks.
I'd like to do better and am working to reduce power further.
I use this as part of my home automation system.

I am trying many different techniques to reduce power usage.
I am measuring power using an FNIRSI FNB58 USB tester.
When my code is asleep it consumes about 7.8 milliamps.

This compares to normal micropython at about 17 milliamps.
Lightsleep in version 1.23.0 consumes 1.6 milliamps.
(Note that lightsleep in 1.24.1 has some bugs).
But it has much more hardware turned off.

I am sharing this to provide a simple example using the code in my repo [RP2-PowerControl](https://github.com/cpottle9/RP2-PowerControl).
Go look at that repo for more information.
It is an alternative to using machine.lightsleep() plus other capabilities.

I am a novice python coder. I know this code could be **better** but I think there is value sharing it as is.

This application runs unattended. I've tried to make it as robust as I can.
I make use of the RP2040 watchdog timer to detect when the code might get stuck and restart micropython to recover.

To use this application you will need the files power_ctrl_abstract.py and power_ctrl_2040.py from my repo RP2-PowerControl.
Also, you will need to modify the file secrets.py to include your WIFI and MQTT info.

