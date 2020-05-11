#!/bin/bash --rcfile
echo "Hektor Detection 2020 is running!"
python3 /home/pi/programs/HektorDetection2020/HektorDetection2020.py --model /home/pi/programs/HektorDetection2020/tflite/detect.tflite --labels /home/pi/programs/HektorDetection2020/tflite/coco_labels.txt
