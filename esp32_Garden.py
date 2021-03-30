# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_apds9960.apds9960
import adafruit_bmp280
import adafruit_sht31d

print("Setting up Wifi.")

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.D10)
esp32_ready = DigitalInOut(board.D9)
esp32_reset = DigitalInOut(board.D6)


spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
"""Use below for Most Boards"""
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.1
)  # Uncomment for Most Boards
"""Uncomment below for ItsyBitsy M4"""
# status_light = dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.2)
# Uncomment below for an externally defined RGB LED
# import adafruit_rgbled
# from adafruit_esp32spi import PWMOut
# RED_LED = PWMOut.PWMOut(esp, 26)
# GREEN_LED = PWMOut.PWMOut(esp, 27)
# BLUE_LED = PWMOut.PWMOut(esp, 25)
# status_light = adafruit_rgbled.RGBLED(RED_LED, BLUE_LED, GREEN_LED)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

print("Setting up Sensors")
i2c = board.I2C()
apds9960 = adafruit_apds9960.apds9960.APDS9960(i2c)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
sht31d = adafruit_sht31d.SHT31D(i2c)
# settings for proximity and light sensor
apds9960.enable_proximity = False
apds9960.enable_color = True
# interval and samples in seconds
interval_sleep = 10
samples = 3
deep_sleep = 600
def sample_and_avg(interval_sleep,samples):
    count = 0
    temptotal = 0
    pressuretotal =0
    humiditytotal = 0
    while count < samples:
        temptotal = temptotal + bmp280.temperature
        pressuretotal = pressuretotal + bmp280.pressure
        humiditytotal = humiditytotal + sht31d.relative_humidity
        time.sleep(interval_sleep)
        count += 1
    avtemp = temptotal / samples
    avpress = pressuretotal / samples
    avhumidity = humiditytotal / samples
    return (round(avtemp,1), round(avpress,1), round(avhumidity,1))


#counter = sample_and_avg(interval_sleep,samples)
counter = 0
print("Average Temp:{}, Average Pressure:{}, Average Humidity:{}".format(*sample_and_avg(interval_sleep,samples)))

while True:
    try:
        print("Posting data...", end="")
        data = counter
        feed = "test-garden"
        payload = {"value": data}
        response = wifi.post(
            "https://io.adafruit.com/api/v2/"
            + secrets["aio_username"]
            + "/feeds/"
            + feed
            + "/data",
            json=payload,
            headers={"X-AIO-KEY": secrets["aio_key"]},
        )
        print(response.json())
        response.close()
        counter = counter + 1
        print("OK")
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    response = None
    time.sleep(15)
