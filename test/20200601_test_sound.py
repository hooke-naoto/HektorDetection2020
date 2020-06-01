import subprocess
import glob
import random
dir_sound = "sound/"
Files = sorted(glob.glob(dir_sound + "*.mp3"))
# print(len(Files))
# print(random.randint(0, len(Files) - 1))
# print(Files[random.randint(0, len(Files) - 1)])
while True:
    subprocess.call("vlc -I rc --play-and-exit "  + Files[random.randint(0, len(Files) - 1)], shell=True)
    