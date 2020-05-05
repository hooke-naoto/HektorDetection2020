import psutil
print psutil.disk_usage('/').free

import glob
import os
PhotoDir = "/home/pi/programs/HektorDetection2020/photo"
Files = glob.glob(PhotoDir + "/*/*.jpg")
FilesSort = sorted(Files)
for F in FilesSort:
    if FilesSort.index(F) < 3:
        print(F)
        #os.remove(F)

print("test")
for D in glob.glob(PhotoDir + "/*"):
    print(D)
    try:
        os.rmdir(D)
    except OSError as dummy:
        pass

Status = "test1. "
Status = Status + "test2. "
print(Status)

Status = Status + "xx"
print(Status)
Status = Status[0:len(Status)-2] + "yy"                
print(Status)

import random
dir_sound = "/home/pi/programs/HektorDetection2020/sound/"
Files = sorted(glob.glob(dir_sound + "/*.wav"))
os.system("aplay " + Files[random.randint(0, len(Files) - 1)])
