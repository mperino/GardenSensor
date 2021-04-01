#========================================================
# Import libraries

import time
import board
import adafruit_dht
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
from adafruit_seesaw.seesaw import Seesaw
print("library loaded")
#========================================================
# setup variables for temp sensor
interval_sleep = 2
deep_sleep = 600
retries = 4
samples = 3
dhtDevice = adafruit_dht.DHT22(board.GP7)
#========================================================
# setup for soil sensor on pins 1 & 2
i2c = busio.I2C(scl=board.GP1, sda=board.GP0)
ss = Seesaw(i2c, addr=0x36)

#========================================================
# check if we have a WiFi SSID and password:
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
#========================================================
#setup variables for WiFi board (SID and password in secrets.py)
esp32_cs = DigitalInOut(board.GP13)
esp32_ready = DigitalInOut(board.GP14)
esp32_reset = DigitalInOut(board.GP15)
spi = busio.SPI(board.GP10, board.GP11, board.GP12)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets)

#========================================================
# Functions

def avg_temp(interval_sleep,samples):
    count = 0
    total = 0
    while count < samples:
        try:
            total = total + dhtDevice.temperature
            time.sleep(interval_sleep)
            count += 1
        except:
            print("Retrying DHT22.. Normal to see these")
            time.sleep(interval_sleep)
    avtemp = total / samples
    tempf = avtemp * 1.8 + 32
    return (round(tempf,1))

def avg_humid(interval_sleep,samples):
    count = 0
    total = 0
    while count < samples:
        try:
            total = total + dhtDevice.humidity
            time.sleep(interval_sleep)
            count += 1
        except:
            print("Retrying DHT22.. Normal to see these")
    avg = total / samples
    return (round(avg,1))

def avg_soil(interval_sleep, samples):
    print("Testing Soil.  Takes 6+ seconds (or sleep_timer x samples)")
    count = 0
    total = 0
    while count < samples:
        total = total + ss.moisture_read()
        time.sleep(interval_sleep)
        count += 1
    soil = total / samples
    return (round(soil, 1))

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

# ========================================================
# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

#========================================================
#Main Code loops endlessley
while True:
    response = None
    try:
        print("Posting Temp F")
#        print("avg temp:{}\n".format(avg_temp(interval_sleep,samples)))
        post2feed("temp", avg_temp(interval_sleep,samples))
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
    try:
        print("Posting Soil Moisture")
#        print("avg Soil Moisture:{}\n".format(avg_soil(interval_sleep,samples)))
        post2feed("soil", avg_soil(interval_sleep,samples))
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(deep_sleep)