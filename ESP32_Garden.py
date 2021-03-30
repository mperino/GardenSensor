# Main Code Contributions:
# SPDX-FileCopyrightText: 2020 Team 4160 "The Robucs" Mission Bay HighSchool
# SPDX-License-Identifier: MIT
# Some Code greatfully resued from:
# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
#========================================================
import time
#import alarm  (support is added in circutpython 6.1.0-beta-2
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_apds9960.apds9960
import adafruit_bmp280
import adafruit_sht31d

#========================================================
# Get wifi details and more from a secrets.py file  If there is no secrets file we cant join a wifi
print("Getting Wifi settings from secrets.py")
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
#========================================================
#setup pins
# we are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.D10)
esp32_ready = DigitalInOut(board.D9)
esp32_reset = DigitalInOut(board.D6)

# setup SPI and ESP for the onboard sensors
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
#enable the status LED
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.1
)
#========================================================
#Enable the Wifi
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
#========================================================
#setup sensors
print("Setting up Sensors")
i2c = board.I2C()
apds9960 = adafruit_apds9960.apds9960.APDS9960(i2c)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
sht31d = adafruit_sht31d.SHT31D(i2c)
# settings for proximity and light sensor
apds9960.enable_proximity = False
apds9960.enable_color = True
#========================================================
# Settings for sampling from sensors in seconds
interval_sleep = 10
samples = 3
deep_sleep_time = 600
#========================================================
# Functions

def avg_temp(interval_sleep,samples):
    count = 0
    total = 0
    while count < samples:
        total = total + bmp280.temperature
        time.sleep(interval_sleep)
        count += 1
    avtemp = total / samples
    tempf = avtemp * 1.8 + 32
    return (round(tempf,1))

def avg_press(interval_sleep,samples):
    count = 0
    total = 0
    while count < samples:
        total = total + bmp280.pressure
        time.sleep(interval_sleep)
        count += 1
    avg = total / samples
    return (round(avg,1))

def avg_humid(interval_sleep,samples):
    count = 0
    total = 0
    while count < samples:
        total = total + sht31d.relative_humidity
        time.sleep(interval_sleep)
        count += 1
    avg = total / samples
    return (round(avg,1))

def post2feed(feed_name,data):
    try:
        print("Posting data to feed:{}".format(feed_name))
        payload = {"value": data}
        response = wifi.post(
            "https://io.adafruit.com/api/v2/"
            + secrets["aio_username"]
            + "/feeds/"
            + feed_name
            + "/data",
            json=payload,
            headers={"X-AIO-KEY": secrets["aio_key"]},
        )
        print(response.json())
        response.close()
        print("OK")
    except (ValueError, RuntimeError) as e:
        print("Failed to get/post data to feed, resetting wifi\n", e)
        wifi.reset()


# Future Feature
# https://learn.adafruit.com/deep-sleep-with-circuitpython/alarms-and-sleep
#def deepsleep (deep_sleep_time):
#    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + deep_sleep_time)
#    # Exit the program, and then deep sleep until the alarm wakes us.
#    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

#========================================================
#Main Code loops endlessley
while True:
    try:
        print("Posting Temp F")
#        print("avg temp:{}\n".format(avg_temp(interval_sleep,samples)))
        post2feed("temp", avg_temp(interval_sleep,samples))
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    try:
        print("Posting Barometric Pressure")
#        print("avg pressure:{}\n".format(avg_press(interval_sleep, samples)))
        post2feed("pressure", avg_press(interval_sleep, samples))
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    try:
        print("Posting Humidity %")
#        print("avg Humidity:{}%\n".format(avg_humid(interval_sleep, samples)))
        post2feed("humidity", avg_humid(interval_sleep, samples))
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    response = None
    time.sleep(deep_sleep_time)
