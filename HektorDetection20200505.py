# coding: utf-8

#### Import #### START
import io
import os
import datetime
import time
import random
import requests    # for LINE
import RPi.GPIO as GPIO    # for Sensor and LED
#### Import #### END

#### GPIO: pin-assignment, setup #### START
GPIO.setwarnings(False)    # To avoid used pin before.
GPIO.setmode(GPIO.BCM)
SENSOR = 14
GPIO.setup(SENSOR, GPIO.IN)
LED = 15
GPIO.setup(LED, GPIO.OUT)
GPIO.output(LED, GPIO.LOW)
#### GPIO: pin-assignment, setup #### END

#### Google Cloud: import client libraries, instantiates a client #### START
from google.cloud import vision
from google.cloud.vision import types
client = vision.ImageAnnotatorClient()
#### Google Cloud: import client libraries, instantiates a client #### END

#### LINE #### START
def send_line(message, fname):
    url = "https://notify-api.line.me/api/notify"
    token = "XftPxzeo7TL4JzxaKsu1KurQd0T1g5tOM392ePLKVal"
    headers = {"Authorization": "Bearer " + token}
    message = "Hektor was detected!" if message == "" else message
    payload = {"message": message}
    files = {"imageFile": open(fname, "rb")}
    r = requests.post(url, headers = headers, params=payload, files=files)
    print("LINE sent: " + r.text)
#### LINE #### END

#### Processing #### START

try:
    Counter = 0
    
    while True:
        
        if GPIO.input(SENSOR) == GPIO.HIGH:
            print("[if GPIO.input(SENSOR) == GPIO.HIGH:]")
            Counter += 1
            GPIO.output(LED, GPIO.HIGH)
            time.sleep(0.4)
            GPIO.output(LED, GPIO.LOW)
            time.sleep(0.1)
            
            if Counter > 4:
                print("[if Counter > 4:]")
                Counter = 0    # Counter reset
                
                ## Date/Time/Folder update ## START
                print("[## Date/Time/Folder update ## START]")
                from datetime import datetime
                dir_image = '/home/pi/programs/HektorDetection2020/photo/'
                now = datetime.now()
                dir_name = now.strftime('%Y%m%d')
                dir_path = dir_image + dir_name + '/'
                file_name = now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.jpg'
                file_path = dir_path + file_name
                if os.path.exists(dir_path) == False:
                    os.mkdir(dir_path)
                ## Date/Time/Folder update ## END
                
                ## Image grabbing ## START
                print("[## Image grabbing ## START]")
                os.system('sudo raspistill -w 640 -h 480 -rot 180 -t 1 -o ' + file_path)
                ## Image grabbing ## END
                
                ## Google: annotating, loading into memory ## START
                print("[## Google: annotating, loading into memory ## START]")
                image_file_to_annotate = os.path.abspath(file_path)
                with io.open(image_file_to_annotate, 'rb') as image_file:
                    content = image_file.read()
                image = types.Image(content=content)
                ## Google: annotating, loading into memory ## END

                ## Google: label detection ## START
                print("[## Google: label detection ## START]")
                response = client.label_detection(image=image)
                labels = response.label_annotations
                print('Labels [START]')
                for label in labels:
                    print(label.description)
                print('Labels [END]')
                ## Google: label detection ## END

                ## Hektor Detection ## START
                print("[## Hektor Detection ## START]")
                HektorDetection = 0
                for label in labels:
                    if 'cat' in label.description:
                        HektorDetection += 1
                ## Hektor Detection ## END
                
                ## Actions ## START
                print("[## Actions ## START]")
                if HektorDetection > 0:
                    
                    print ('Hektor was detected!')
                    file_path_revised = file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg'
                    os.rename(file_path, file_path_revised)
                    
                    # Play sound
                    sound_dir = "/home/pi/programs/HektorDetection2020/sound/"
                    if random.randint(0, 1) == 0:
                        os.system("aplay " + sound_dir + "KoraHektorDame.wav")
                    else:
                        os.system("aplay " + sound_dir + "RingMouse.wav")
                        
                    # Send LINE message
                    send_line("Hektor was detected!", file_path_revised)
                    
                else:
                    
                    print ('Hektor was not detected...')
                    os.remove(file_path)
                    
                ## Action ## END

except KeyboardInterrupt:
    print("[except KeyboardInterrupt:]")
    
finally:
    GPIO.cleanup()
    
#### Processing #### END
