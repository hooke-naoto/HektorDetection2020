# -*- coding: utf-8 -*-

import os
import random

sound_dir = "/home/pi/programs/HektorDetection2020/sound/"

if random.randint(0, 1) == 0:
    os.system("aplay " + sound_dir + "KoraHektorDame.wav")
else:
    os.system("aplay " + sound_dir + "RingMouse.wav")
