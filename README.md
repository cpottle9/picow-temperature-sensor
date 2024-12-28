# MQTT client on Raspberry PI PICO W

This is a simple MQTT client running on a Raspberry PI PICO W.
It periodically reads temperature from an [mcp9808](https://www.adafruit.com/product/1782) sensor and publishes the reading to an MQTT server.

It is intended to run from battery.
My hardware setup has it running from 2 AA alkaline batteries.
Depending on the battery brand used it runs 2 to 4 weeks.
I'd like to do better and am working to reduce power further.
I use this as part of my home automation system.

I am trying many different techniques to reduce power usage.
I have not measured the actual power reduction for each.
I ordered a precision USB power meter. Once I have it I can measure the changes and report my findings here.

I am sharing this to provide a simple example using the code in my repo [RP2-PowerControl](https://github.com/cpottle9/RP2-PowerControl).
Go look at that repo for more information.
It is an alternative to using machine.lightsleep() plus other capabilities.
I am a novice python coder. I know this code could be **better** but I think there is value sharing it as is.

This application runs unattended. I've tried to make it as robust as I can.
I make use of the RP2040 watchdog timer to detect when the code might get stuck and restart micropython to recover.
