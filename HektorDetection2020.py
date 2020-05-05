# -*- coding: utf-8 -*-

#### Import #### START
import io
import os
import datetime
from datetime import datetime
import time
import random
import requests    # for LINE
import RPi.GPIO as GPIO    # for Sensor and LED
import psutil    # for storage management
import glob    # for storage management
#### Import #### END

#### GPIO: pin-assignment, setup #### START
GPIO.setwarnings(False)    # To avoid used pin before.
GPIO.setmode(GPIO.BCM)
SENSOR = 14
GPIO.setup(SENSOR, GPIO.IN)
#forLED# LED = 15
#forLED# GPIO.setup(LED, GPIO.OUT)
#forLED# GPIO.output(LED, GPIO.LOW)
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

#### Directory #### START
dir_image = "/home/pi/programs/HektorDetection2020/image/"
dir_sound = "/home/pi/programs/HektorDetection2020/sound/"
#### Directory #### END

#### Processing #### START

try:
    Counter = 0
    Status = ""
    StatusSensor = ""
    StatusSensorLast = ""
    
    while True:
        ID = datetime.now().strftime('%Y%m%d') + '_' + datetime.now().strftime('%H%M%S')
        Status = ID
        
        #### Storage Management #### START
        # Remove oldest 10 files and empty directories if free storage is less than 4GB.
        FreeGB = psutil.disk_usage('/').free / 1024 / 1024 / 1024
        if FreeGB < 4:
            Files = sorted(glob.glob(dir_image + "/*/*.jpg"))
            for F in Files:
                if Files.index(F) < 10:
                    os.remove(F)
                    RemoveNum = Files.index(F) + 1
            for D in glob.glob(imageDir + "/*"):
                try:
                    os.rmdir(D)
                except OSError as dummy:
                    pass
            Status = Status + " / " + str(RemoveNum) + " files removed"
            print(Status)
        #### Storage Management #### END
        
        #### Main Process #### START
        if GPIO.input(SENSOR) == GPIO.HIGH:
            Counter += 1
            #forLED# GPIO.output(LED, GPIO.HIGH)
            #forLED# GPIO.output(LED, GPIO.LOW)
            time.sleep(0.5)
            
            # Run if sensor HIGH keeps 5 times.
            if Counter >= 5:
                Status = Status + " / Sensor HIGH"
                StatusSensor = "HIGH"
                Counter = 0
                
                #### Date/Time/Folder update #### START
                dir_path = dir_image + datetime.now().strftime("%Y%m%d") + "/"
                file_name = ID + ".jpg"
                file_path = dir_path + file_name
                if os.path.exists(dir_path) == False:
                    os.mkdir(dir_path)
                #### Date/Time/Folder update #### END
                
                #### Image grabbing #### START
                os.system("sudo raspistill -w 640 -h 480 -rot 180 -t 1 -o " + file_path)
                #### Image grabbing #### END
                
                #### Google: annotating, loading into memory #### START
                image_file_to_annotate = os.path.abspath(file_path)
                with io.open(image_file_to_annotate, 'rb') as image_file:
                    content = image_file.read()
                image = types.Image(content=content)
                #### Google: annotating, loading into memory #### END

                #### Google: label detection #### START
                response = client.label_detection(image=image)
                labels = response.label_annotations
                Status = Status + " / Detected as:"
                for label in labels:
                    Status = Status + " " + label.description
                print (Status)
                #### Google: label detection #### END

                #### Hektor Detection #### START
                HektorDetection = 0
                for label in labels:
                    if 'cat' in label.description:
                        HektorDetection += 1
                #### Hektor Detection #### END
                
                #### Actions #### START
                if HektorDetection > 0:
                    
                    Status = Status + " / Hektor was detected!"
                    print (Status)
                    
                    file_path_revised = file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg'
                    os.rename(file_path, file_path_revised)
                    
                    # Send LINE message.
                    send_line("Hektor was detected!", file_path_revised)
                    
                    # Play a sound file at random in the "sound" folder.
                    Files = sorted(glob.glob(dir_sound + "/*.wav"))
                    os.system("aplay " + Files[random.randint(0, len(Files) - 1)])
                        
                else:
                    
                    Status = Status + " / Hektor was not detected..."
                    print (Status)
                    
                    os.remove(file_path)
                    
                #### Action #### END
                    
        # Reset the counter if sensor LOW appears.
        else:
            Counter = 0
            Status = Status + " / Sensor LOW"
            StatusSensor = "Low"
        
        # Record results of "Main Process".
        if StatusSensor != StatusSensorLast:
            print (Status)
            fileobj = open("/home/pi/programs/HektorDetection2020/Log.txt", "a")
            fileobj.write(Status + "\n")
            fileobj.close()
        StatusSensorLast = StatusSensor        

        #### Main Process #### START

except KeyboardInterrupt:
    Status = "KeyboardInterrupt"
    print (Status)
    fileobj = open("/home/pi/programs/HektorDetection2020/Log.txt", "a")
    fileobj.write(Status + "\n")
    fileobj.close()
    
finally:
    GPIO.cleanup()
    
#### Processing #### END
