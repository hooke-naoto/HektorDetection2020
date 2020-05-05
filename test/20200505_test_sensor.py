import RPi.GPIO as GPIO
import time

SENSOR = 14
LED = 15

GPIO.setmode(GPIO.BCM)

GPIO.setup(SENSOR, GPIO.IN)

GPIO.setup(LED, GPIO.OUT)
GPIO.output(LED, GPIO.LOW)

try:
    while True:
        if GPIO.input(SENSOR) == GPIO.HIGH:
            print(str(GPIO.input(SENSOR)) + " ... detected!")
            GPIO.output(LED, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED, GPIO.LOW)
        else:
            print(GPIO.input(SENSOR))
            time.sleep(0.5)
except KeyboardInterrupt:
    print("---- Keyboard Interrupt ----")
finally:
    GPIO.cleanup()
