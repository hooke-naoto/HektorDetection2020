import os
import glob
import random
dir_sound = "sound/"
Files = sorted(glob.glob(dir_sound + "*.mp3"))
os.system("aplay " + Files[random.randint(0, len(Files) - 1)])
print('Files:', Files)
