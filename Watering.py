import RPi.GPIO as GPIO
import time 
import Adafruit_ADS1x15 
import math
adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)
#adc = Adafruit_ADS1x15.ADS1115()

GAIN = 1
PIN = 7

def setup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIN, GPIO.OUT)
    GPIO.output(PIN, GPIO.HIGH)
    time.sleep(0.1)

values = [0]*100

def loop():
    while True:
        for i in range(100):
            values[i]=adc.read_adc(0,gain=GAIN)
        print(max(values))
		
        if (max(values))>21400: #when sensor reads above 21,400 soil is dry so pump is turned on
            GPIO.output(PIN, GPIO.LOW) # Var PIN(pin number 7) is the GPIO pin for relay which flicks on and off the pump 
            print("Pump is on") 
            print(PIN)
            time.sleep(0.1)
        else:
            GPIO.output(PIN,GPIO.HIGH) #when sensors reads below 21,400, soil is saturated so pump is turned off
            print("Pump is off")
            print(PIN)
            time.sleep(0.1)
			
def destroy():
    GPIO.output(PIN, GPIO.HIGH)
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop()
    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        destroy()
