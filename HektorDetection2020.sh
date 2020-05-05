#!/bin/bash --rcfile
source /home/pi/env/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/GoogleApplicationCredentials.json
echo "Hektor Detection 2020 is running!"
python /home/pi/programs/HektorDetection2020/HektorDetection2020.py
