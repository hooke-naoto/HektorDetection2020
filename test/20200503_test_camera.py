# coding: utf-8

#### Import #### START
import io
import os
import datetime
import time
import random
#### Import #### END

#### LINE #### START
default_max = 3
import requests
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

######## Process ######## START
while True:
    
    #### Google Cloud - Import client libraries, instantiates a client #### START
    from google.cloud import vision
    from google.cloud.vision import types
    client = vision.ImageAnnotatorClient()
    #### Google Cloud - Import client libraries, instantiates a client #### END

    #### Image file to annotate #### START
    from datetime import datetime
    dir_image = '/home/pi/programs/HektorDetection2020/photo/'
    now = datetime.now()
    dir_name = now.strftime('%Y%m%d')
    dir_path = dir_image + dir_name + '/'
    file_name = now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.jpg'
    file_path = dir_path + file_name
    if os.path.exists(dir_path) == False:
        os.mkdir(dir_path)
    os.system('sudo raspistill -w 640 -h 480 -t 1 -o ' + file_path)
    image_file_to_annotate = os.path.abspath(file_path)
    #### Image file to annotate #### END

    #### Loads the image into memory #### START
    with io.open(image_file_to_annotate, 'rb') as image_file:
        content = image_file.read()
    image = types.Image(content=content)
    #### Loads the image into memory #### END

    #### Performs label detection on the image file #### START
    response = client.label_detection(image=image)
    labels = response.label_annotations
    print('Labels [START]')
    for label in labels:
        print(label.description)
    print('Labels [END]')
    #### Performs label detection on the image file #### END

    #### Hektor Detection #### START
    HektorDetection = False
    for label in labels:
        if 'cat' in label.description:
            HektorDetection = True
    if HektorDetection == True:
        print ('Hektor detected!')
        os.rename(file_path, file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg')
        file_path = file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg'
    #### Hektor Detection #### END

    #### Play sound if Hektor detected #### START
    if HektorDetection == True:
        sound_dir = "/home/pi/programs/HektorDetection2020/sound/"
        if random.randint(0, 1) == 0:
            os.system("aplay " + sound_dir + "KoraHektorDame.wav")
        else:
            os.system("aplay " + sound_dir + "RingMouse.wav")
    #### Play sound if Hektor detected #### END

    #### LINE if Hektor detected #### START
    if HektorDetection == True:
        send_line("Hektor was detected!", file_path)
    #### LINE if Hektor detected #### END

    #### interval #### START
    time.sleep(5)
    #### interval #### END

######## Process ######## START
