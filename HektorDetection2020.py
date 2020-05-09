# -*- coding: utf-8 -*-

######## Desctiption ########
# Goal: The detection camera for my cat in our house with RasPi as a stand-alone system (no web loading).
# Last: Detection with Google Cloud Vision API.
# This: Try as a stand-alone with TensorFlow.
######## Desctiption ######## END

######## Parameters ########
dir_image = "/home/pi/programs/HektorDetection2020/image/"
dir_sound = "/home/pi/programs/HektorDetection2020/sound/"
save_result_image = True
show_result_image = True
min_score = 0.2 # Min scores for result image.
max_boxes = 10 # Max number of boxes for result image.
nn_model_path = "nn_model/ssd_mobilenet_v2_1"
nn_model_url = "https://tfhub.dev/google/openimages_v4/ssd/mobilenet_v2/1"
image_path = "Hektor.jpg"
######## Parameters ######## END

######## Import ########
# General
import io
import os
import time
import datetime
# from datetime import datetime
import random
import requests    # for LINE
import RPi.GPIO as GPIO    # for Sensor and LED
import psutil    # for storage management
import glob    # for storage management
import tempfile
import numpy as np
import matplotlib.pyplot as plt

# PILLOW (image processing)
from PIL import Image
from PIL import ImageOps
from PIL import ImageDraw
from PIL import ImageFont

# TensorFlow
import tensorflow as tf
import tensorflow_hub as tf_hub
print("\n[Environment for TensorFlow]")
if tf.test.gpu_device_name() != "":
    print("GPU: %s" % tf.test.gpu_device_name())
else:
    print("GPU: none")
print("TensorFlow version:", tf.__version__)

# NN Model
print("\n[NN model loading]")
# [ssd+mobilenet V2] was choosen because smaller and faster than [FasterRCNN+InceptionResNet V2].
try:
    nn_model = tf_hub.load(nn_model_path).signatures['default']
    print("NN model was loaded from local PC:", nn_model_path)
except OSError as error:
    print("NN model couldn't be loaded from local PC:", error)
    print("NN model will be loaded from TensorFlow Hub...")
    try:
        nn_model = tf_hub.load(nn_model_url).signatures['default']
        print("NN model was loaded from TensorFlow Hub:", nn_model_url)
    except OSError as error:
        print("Error - NN model loading:", error)
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
#### LINE ####
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

#### Load & Resize images ####
def load_and_resize_image(path, new_width=256, new_height=256, display=False):
    _, filename = tempfile.mkstemp(suffix=".jpg")
    pil_image = Image.open(path)
    pil_image = ImageOps.fit(pil_image, (new_width, new_height), Image.ANTIALIAS)
    pil_image_rgb = pil_image.convert("RGB")
    pil_image_rgb.save(filename, format="JPEG", quality=90)
    print("Image loaded to %s." % filename)
    return filename
#### Load & Resize images #### END

#### Draw boxes ####
# Overlay labeled boxes on an image with formatted scores and label names.
def draw_boxes(image, boxes, class_names, scores, min_score, max_boxes):
    font = ImageFont.load_default()
    for i in range(min(len(boxes), max_boxes)):
        if scores[i] >= min_score:
            ymin, xmin, ymax, xmax = tuple(boxes[i])
            display_str = "{}: {}%".format(class_names[i].decode("ascii"), int(100 * scores[i]))
            image_pil = Image.fromarray(np.uint8(image)).convert("RGB")
            draw_bounding_box_on_image(image_pil, ymin, xmin, ymax, xmax, font, display_str_list=[display_str])
        np.copyto(image, np.array(image_pil))
    return image
#### Draw boxes #### END

#### Draw bounding box on image ####
# Adds a bounding box to an image.
def draw_bounding_box_on_image(image, ymin, xmin, ymax, xmax, font, thickness=2, display_str_list=()):
    draw = ImageDraw.Draw(image)
    im_width, im_height = image.size
    (left, right, top, bottom) = (xmin * im_width, xmax * im_width, ymin * im_height, ymax * im_height)
    draw.line([(left, top), (left, bottom), (right, bottom), (right, top), (left, top)], width=thickness, fill="lightgray")
    # If the total height of the display strings added to the top of the bounding box
    # exceeds the top of the image, stack the strings below the bounding box instead of above.
    display_str_heights = [font.getsize(ds)[1] for ds in display_str_list]
    # Each display_str has a top and bottom margin of 0.05x.
    total_display_str_height = (1 + 2 * 0.05) * sum(display_str_heights)
    if top > total_display_str_height:
        text_bottom = top
    else:
        text_bottom = top + total_display_str_height
    # Reverse list and print from bottom to top.
    for display_str in display_str_list[::-1]:
        text_width, text_height = font.getsize(display_str)
        margin = np.ceil(0.05 * text_height)
        draw.rectangle(
                       [(left, text_bottom - text_height - margin*2), (left + text_width, text_bottom)],
                       fill="lightgray"
                       )
        draw.text(
                  (left + margin, text_bottom - text_height - margin),
                  display_str,
                  fill="black",
                  font=font
                  )
        text_bottom -= text_height - margin*2
#### Draw bounding box on image #### END
######## Helper Functions ######## END


######## Processing ########

try:
    Counter = 0
    Status = ""
    StatusSensor = "low"
    StatusSensorLast = "low"

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
                file_path_detection = load_and_resize_image(file_path, 400, 300)
                image = tf.io.read_file(file_path_detection)
                image = tf.image.decode_jpeg(image, channels=3)
                image_converted  = tf.image.convert_image_dtype(image, tf.float32)[tf.newaxis, ...]
                results = nn_model(image_converted)
                results = {key:value.numpy() for key,value in results.items()}
                print("%d objects were detected." % len(results["detection_scores"]))
                ######## Detection ######## END

                ######## Show & Save result image ########
                image_with_boxes = draw_boxes(
                                              image.numpy(),
                                              results["detection_boxes"],
                                              results["detection_class_entities"],
                                              results["detection_scores"],
                                              min_score,
                                              max_boxes
                                              )
                fig = plt.figure(figsize=(8, 6))
                plt.grid(False)
                plt.imshow(image_with_boxes)
                if save_result_image == True:
                    folder_path = "DetectedImage/"
                    if os.path.exists(folder_path) == False:
                        os.mkdir(folder_path)
                    plt.savefig(folder_path + ID + ".png")
                if show_result_image == True:
                    plt.show()
                ######## Show & Save result image ######## END
                
                #### Hektor Detection ####
                HektorDetection = 0
                for label in labels:
                    if 'cat' in label.description:
                        HektorDetection += 1
                #### Hektor Detection #### END

                #### Actions ####
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
            fileobj = open("/home/pi/programs/HektorDetection2020/Log.txt", "a")
            fileobj.write(Status + "\n")
            fileobj.close()
        StatusSensorLast = StatusSensor
        #### Log.txt #### END

        ######## Main Process ########

except KeyboardInterrupt:
    Status = "KeyboardInterrupt"
    print (Status)
    fileobj = open("/home/pi/programs/HektorDetection2020/Log.txt", "a")
    fileobj.write(Status + "\n")
    fileobj.close()

finally:
    GPIO.cleanup()

######## Processing ######## END
