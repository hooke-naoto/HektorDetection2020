# -*- coding: utf-8 -*-

######## Desctiption ########
# Goal: The detection camera for my cat in our house with RasPi as a stand-alone system (no web loading).
# Last: Detection with Google Cloud Vision API.
# This: Try as a stand-alone with TensorFlow.
######## Desctiption ######## END

######## Parameters ########
dir_image = "image/"
dir_sound = "sound/"
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
######## Parameters ######## END

######## Import ########
# __future__ to avoid version interferences between Python2 and Python3.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# General
import io
import os
import argparse
import re
import time
import datetime
import random
import requests    # for LINE
import RPi.GPIO as GPIO    # for Sensor and LED
import psutil    # for storage management
import glob    # for storage management
import tempfile
import numpy as np
import matplotlib.pyplot as plt
import picamera

# PILLOW (image processing)
from PIL import Image
from PIL import ImageOps
from PIL import ImageDraw
from PIL import ImageFont

# ?
from annotation import Annotator

# TensorFlow
from tflite_runtime.interpreter import Interpreter
######## Import ######## END

######## GPIO: pin-assignment, setup ########
GPIO.setwarnings(False)    # To avoid used pin before.
GPIO.setmode(GPIO.BCM)
SENSOR = 14
GPIO.setup(SENSOR, GPIO.IN)
#forLED# LED = 15
#forLED# GPIO.setup(LED, GPIO.OUT)
#forLED# GPIO.output(LED, GPIO.LOW)
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
        xmin = int(xmin * CAMERA_WIDTH)
        xmax = int(xmax * CAMERA_WIDTH)
        ymin = int(ymin * CAMERA_HEIGHT)
        ymax = int(ymax * CAMERA_HEIGHT)
        # Overlay the box, label, and score on the camera preview
        annotator.bounding_box([xmin, ymin, xmax, ymax])
        annotator.text([xmin, ymin], '%s\n%.2f' % (labels[obj['class_id']], obj['score']))
######## Helper Functions ######## END


######## Processing ########
try:
    Counter = 0
    Status = ""
    StatusSensor = "low"
    StatusSensorLast = "low"
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--model', help='File path of .tflite file.', required=True)
    parser.add_argument('--labels', help='File path of labels file.', required=True)
    parser.add_argument('--threshold',　help='Threshold for detection.', required=False,
                        type=float, default=0.4)
    args = parser.parse_args()
    labels = load_labels(args.labels)
    interpreter = Interpreter(args.model)
    interpreter.allocate_tensors()
    _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']

    while True:
        now = datetime.datetime.now()
        ID = now.strftime("%Y%m%d_%H%M%S")
        Status = ID

        ######## Storage Management ########
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
        ######## Storage Management ######## END

        ######## Main Process ########
        if GPIO.input(SENSOR) == GPIO.HIGH:
            Counter += 1
            #forLED# GPIO.output(LED, GPIO.HIGH)
            #forLED# GPIO.output(LED, GPIO.LOW)
            time.sleep(0.5)

            #### Sensor HIGH kept or not ####
            if Counter >= 5:
                Status = Status + " / Sensor HIGH"
                StatusSensor = "high"
                Counter = 0

                #### Date/Time/Folder update ####
                dir_path = dir_image + datetime.now().strftime("%Y%m%d") + "/"
                file_name = ID + ".jpg"
                file_path = dir_path + file_name
                if os.path.exists(dir_path) == False:
                    os.mkdir(dir_path)
                #### Date/Time/Folder update #### END

                #### Image grabbing ####
                os.system("sudo raspistill -w 640 -h 480 -rot 180 -t 1 -o " + file_path)
                #### Image grabbing #### END

                ######## Detection ########
                print("\n[Detection]")
                print("ID:", ID)
                image = Image.open(file_path).convert('RGB').resize((input_width, input_height), Image.ANTIALIAS)
                results = detect_objects(interpreter, image, args.threshold)
                print("results:", results)
                annotator.clear()
                annotate_objects(annotator, results, labels)
                annotator.text([5, 0], '%.1fms' % (elapsed_ms))
                annotator.update()
                ######## Detection ######## END

                #### Hektor Detection ####
                # HektorDetection = 0
                # for label in labels:
                #     if 'cat' in label.description:
                #         HektorDetection += 1
                #### Hektor Detection #### END

                #### Actions ####
                # if HektorDetection > 0:
                #
                #     Status = Status + " / Hektor was detected!"
                #     print (Status)
                #
                #     file_path_revised = file_path[0:file_path.rfind('.jpg')] + '_HektorDetected.jpg'
                #     os.rename(file_path, file_path_revised)
                #
                #     # Send LINE message.
                #     send_line("Hektor was detected!", file_path_revised)
                #
                #     # Play a sound file at random in the "sound" folder.
                #     Files = sorted(glob.glob(dir_sound + "/*.wav"))
                #     os.system("aplay " + Files[random.randint(0, len(Files) - 1)])
                #
                # else:
                #
                #     Status = Status + " / Hektor was not detected..."
                #     print (Status)
                #
                #     os.remove(file_path)
                #### Action #### END

            else:
                Status = Status + " / Sensor MEDIUM"
                StatusSensor = "medium"
            #### Sensor HIGH kept or not #### END

        else:
            # Reset the counter if sensor LOW appears.
            Counter = 0
            Status = Status + " / Sensor LOW"
            StatusSensor = "low"

        #### Log.txt ####
        DoRecord = 0
        if StatusSensor == "high":
            DoRecord = 1
        if StatusSensorLast == "high":
            if StatusSensor == "medium":
                DoRecord = 1
            if StatusSensor == "low":
                DoRecord = 1
        if DoRecord == 1:
            print (Status)
            fileobj = open("Log.txt", "a")
            fileobj.write(Status + "\n")
            fileobj.close()
        StatusSensorLast = StatusSensor
        #### Log.txt #### END

except KeyboardInterrupt:
    Status = "KeyboardInterrupt"
    print (Status)
    fileobj = open("Log.txt", "a")
    fileobj.write(Status + "\n")
    fileobj.close()

finally:
    GPIO.cleanup()
######## Processing ######## END
