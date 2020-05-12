# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

######## Desctiption ########
# Goal: The detection camera for my cat in our house with RasPi as a stand-alone system (no web loading).
# Last: Detection with Google Cloud Vision API.
# This: Try as a stand-alone with TensorFlow Lite.
######## Desctiption ######## END

######## Parameters ########
dir_image = "image/"
dir_sound = "sound/"
camera_width = 640
camera_height = 480
######## Parameters ######## END

######## Import ########
# General
import io
import os
import sys
sys.dont_write_bytecode = True # Avoid cache folder and files.
import argparse
import re
import time
import datetime
import random
import requests    # for LINE
import RPi.GPIO as GPIO    # for Sensor and LED
import shutil    # for storage management
import psutil    # for storage management
import glob    # for storage management
import tempfile
import numpy as np
import matplotlib.pyplot as plt
import picamera
camera = picamera.PiCamera(resolution=(camera_width, camera_height))
camera.rotation = 180

# PILLOW (image processing)
from PIL import Image
from PIL import ImageOps
from PIL import ImageDraw
from PIL import ImageFont

# Import "annotation.py" in same folder
from annotation import Annotator
annotator = Annotator(camera)

# TensorFlow
from tflite_runtime.interpreter import Interpreter
######## Import ######## END

######## GPIO: pin-assignment, setup ########
GPIO.setwarnings(False)    # To avoid used pin before.
GPIO.setmode(GPIO.BCM)
SENSOR = 14
GPIO.setup(SENSOR, GPIO.IN)
LED = 15 #### for LED ####
GPIO.setup(LED, GPIO.OUT) #### for LED ####
GPIO.output(LED, GPIO.LOW) #### for LED ####
######## GPIO: pin-assignment, setup ######## END

######## Helper Functions ########
"""LINE"""
def send_line(message, fname):
    url = "https://notify-api.line.me/api/notify"
    token = "XftPxzeo7TL4JzxaKsu1KurQd0T1g5tOM392ePLKVal"
    headers = {"Authorization": "Bearer " + token}
    message = "Hektor was detected!" if message == "" else message
    payload = {"message": message}
    files = {"imageFile": open(fname, "rb")}
    r = requests.post(url, headers = headers, params=payload, files=files)
    print("LINE sent: " + r.text)

"""Loads the labels file. Supports files with or without index numbers."""
def load_labels(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        labels = {}
        for row_number, content in enumerate(lines):
            pair = re.split(r'[:\s]+', content.strip(), maxsplit=1)
            if len(pair) == 2 and pair[0].strip().isdigit():
                labels[int(pair[0])] = pair[1].strip()
            else:
                labels[row_number] = pair[0].strip()
    return labels

"""Sets the input tensor."""
def set_input_tensor(interpreter, image):
    tensor_index = interpreter.get_input_details()[0]['index']
    input_tensor = interpreter.tensor(tensor_index)()[0]
    input_tensor[:, :] = image

"""Returns the output tensor at the given index."""
def get_output_tensor(interpreter, index):
    output_details = interpreter.get_output_details()[index]
    tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
    return tensor

"""Returns a list of detection results, each a dictionary of object info."""
def detect_objects(interpreter, image, threshold):
    set_input_tensor(interpreter, image)
    interpreter.invoke()
    boxes = get_output_tensor(interpreter, 0)
    classes = get_output_tensor(interpreter, 1)
    scores = get_output_tensor(interpreter, 2)
    count = int(get_output_tensor(interpreter, 3))
    results = []
    for i in range(count):
        if scores[i] >= threshold:
            result = {
                        'bounding_box': boxes[i],
                        'class_id': classes[i],
                        'score': scores[i]
                        }
            results.append(result)
    return results

"""Draws the bounding box and label for each object in the results."""
def annotate_objects(annotator, results, labels):
    for obj in results:
        # Convert the bounding box figures from relative coordinates
        # to absolute coordinates based on the original resolution
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * camera_width)
        xmax = int(xmax * camera_width)
        ymin = int(ymin * camera_height)
        ymax = int(ymax * camera_height)
        # Overlay the box, label, and score on the camera preview
        annotator.bounding_box([xmin, ymin, xmax, ymax])
        annotator.text([xmin, ymin], '%s\n%.2f' % (labels[obj['class_id']], obj['score']))
######## Helper Functions ######## END


######## Processing ########
try:
    Counter = 0
    ID_data = ""
    StatusSensor = "low"
    StatusSensorLast = "low"
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--model', help='File path of .tflite file.', required=True)
    parser.add_argument('--labels', help='File path of labels file.', required=True)
    parser.add_argument('--threshold', help='Threshold for detection.', required=False, type=float, default=0.4)
    args = parser.parse_args()
    labels = load_labels(args.labels)
    interpreter = Interpreter(args.model)
    interpreter.allocate_tensors()
    _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']
    
    # [System started.] will be recorded to log file and notified to LINE.
    d = datetime.datetime.now()
    fileobj = open("log/" + d.strftime("%Y%m%d") + ".txt", "a")
    fileobj.write(d.strftime("%Y%m%d_%H%M%S") + ": System started." + "\n")
    fileobj.close()
    camera.capture("tmp.jpg")
    send_line(d.strftime("%Y%m%d_%H%M%S") + ": System started.", "tmp.jpg")
    for i in range(10):
        GPIO.output(LED, GPIO.HIGH) #### for LED ####
        time.sleep(0.05)
        GPIO.output(LED, GPIO.LOW) #### for LED ####
        time.sleep(0.05)

    while True:
        d = datetime.datetime.now()
        ID = d.strftime("%Y%m%d_%H%M%S")
        ID_data = ID
        
        ######## Storage Management ########
        # Remove oldest 10 files and empty directories if free storage is less than 4GB.
        FreeGB = psutil.disk_usage('/').free / 1024 / 1024 / 1024
        if FreeGB < 1:
            Files = sorted(glob.glob(dir_image + "/*/*.jpg"))
            for F in Files:
                if Files.index(F) < 10:
                    os.remove(F)
                    RemoveNum = Files.index(F) + 1
            for D in glob.glob(dir_image + "/*"):
                try:
                    os.rmdir(D)
                except OSError as dummy:
                    pass
            ID_data = ID_data + " / " + str(RemoveNum) + " files removed"
            print(ID_data)
        ######## Storage Management ######## END

        ######## Main Process ########
        if GPIO.input(SENSOR) == GPIO.HIGH:
            Counter += 1
            GPIO.output(LED, GPIO.HIGH) #### for LED ####
            time.sleep(0.1)
            GPIO.output(LED, GPIO.LOW) #### for LED ####
            time.sleep(0.4)

            #### Sensor HIGH kept or not ####
            if Counter >=  3:
                
                GPIO.output(LED, GPIO.HIGH) #### for LED ####
                
                ID_data = ID_data + " / Sensor HIGH"
                StatusSensor = "high"
                Counter = 0

                #### Date/Time/Folder update ####
                dir_path = dir_image + datetime.datetime.now().strftime("%Y%m%d") + "/"
                file_name = ID + ".jpg"
                file_path = dir_path + file_name
                if os.path.exists(dir_path) == False:
                    os.mkdir(dir_path)
                #### Date/Time/Folder update #### END

                #### Image grabbing ####
                camera.capture("tmp.jpg")
                shutil.copy("tmp.jpg", file_path)
                #### Image grabbing #### END

                ######## Detection ########
                print("\n[Detection]")
                print("ID:", ID)
                image = Image.open(file_path).convert('RGB').resize((input_width, input_height), Image.ANTIALIAS)
                t_start = time.monotonic()
                results = detect_objects(interpreter, image, args.threshold)
                t_process = (time.monotonic() - t_start) * 1000
#                 annotator.clear()
#                 annotate_objects(annotator, results, labels)
#                 annotator.text([5, 0], '%.1fms' % (t_process))
#                 annotator.update()
                ID_data = ID_data + " / " + str(int(t_process)) + " ms"
                HektorDetection = 0
                for obj in results:
                    if "cat" in labels[obj["class_id"]]:
                        HektorDetection += 1
                    if "Cat" in labels[obj["class_id"]]:
                        HektorDetection += 1
                ######## Detection ######## END

                #### Actions ####
                if HektorDetection > 0:
                    ID_data = ID_data + " / Hektor was detected!"
                    file_path_revised = file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg'
                    os.rename(file_path, file_path_revised)
                    send_line("Hektor was detected!", file_path_revised)
                    Files = sorted(glob.glob(dir_sound + "/*.wav"))
                    os.system("aplay " + Files[random.randint(0, len(Files) - 1)])
                else:
                    ID_data = ID_data + " / Hektor was not detected..."
                    os.remove(file_path)
                #### Action #### END
                    
                #### Detected info ####
                for obj in results:
                    ID_data = ID_data + " / " + str(int(obj["class_id"])) + " " + labels[obj["class_id"]] + " " + "{:.3f}".format(obj["score"])
                #### Detected info #### END
                      
                GPIO.output(LED, GPIO.LOW) #### for LED ####
                
            else:
                ID_data = ID_data + " / Sensor MEDIUM"
                StatusSensor = "medium"
            #### Sensor HIGH kept or not #### END
                      
        else:
            # Reset the counter if sensor LOW appears.
            Counter = 0
            ID_data = ID_data + " / Sensor LOW"
            StatusSensor = "low"

        #### log.txt ####
        DoRecord = 0
        if StatusSensor == "high":
            DoRecord = 1
        if StatusSensorLast == "high":
            if StatusSensor == "medium":
                DoRecord = 1
            if StatusSensor == "low":
                DoRecord = 1
        if DoRecord == 1:
            print (ID_data)
            fileobj = open("log/" + d.strftime("%Y%m%d") + ".txt", "a")
            fileobj.write(ID_data + "\n")
            fileobj.close()
        StatusSensorLast = StatusSensor
        #### log.txt #### END

except KeyboardInterrupt:
    ID_data = "KeyboardInterrupt"
    print (ID_data)
    fileobj = open("log/" + d.strftime("%Y%m%d") + ".txt", "a")
    fileobj.write(ID_data + "\n")
    fileobj.close()

finally:
    GPIO.cleanup()
######## Processing ######## END
