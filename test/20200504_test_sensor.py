import RPi.GPIO as GPIO
import time

PIN = 14

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN)

try:
    print ('-----Start-----')
    n = 1
    while True:
        if GPIO.input(PIN) == GPIO.HIGH:
            print("{}".format(n) + " times detected!")
            n += 1
            time.sleep(2)
        else:
            print(GPIO.input(PIN))
            time.sleep(2)
except KeyboardInterrupt:
    print("Cancel")
finally:
    GPIO.cleanup()
    print("-----end-----")