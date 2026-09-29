import cv2
import mediapipe as mp
import numpy as np
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import serial
from collections import deque
import pygame
import threading

pygame.mixer.init()


alarm_on = False
drowsy = False
alarm_thread_started=False
drowsy_start_time = None 

def play_alarm():
    global alarm_on
    alarm_on = True
    try:
        pygame.mixer.music.load("alarm.mp3")
        pygame.mixer.music.play(-1)
    except Exception as e:
        print("ALARM ERROR:", e)

def stop_alarm():
    global alarm_on
    if alarm_on:
        pygame.mixer.music.stop()
        alarm_on = False
        print("ALARM STOPPED")


arduino=serial.Serial('/dev/cu.usbmodem141011',9600)
time.sleep(2)
prevstate = False
drowsy = False

base_options=python.BaseOptions(model_asset_path="face_landmarker.task")
options=vision.FaceLandmarkerOptions(base_options=base_options,num_faces=1)
detector=vision.FaceLandmarker.create_from_options(options)
LeftEye=[33,160,158,133,153,144]
RightEye=[362,385,387,267,373,380]

def calculate_EAR(EyesPoint,landmark,w,h):
    points=[]
    for i in EyesPoint:
        x=int(landmark[i].x*w)
        y=int(landmark[i].y*h)
        points.append((x,y))
    
    A=np.linalg.norm(np.array(points[1])-np.array(points[5]))
    B=np.linalg.norm(np.array(points[2])-np.array(points[4]))
    C=np.linalg.norm(np.array(points[0])-np.array(points[3]))
    return (A+B)/(2.0*C)

PrevNoseY=None
NodState="UP"
NodCount=0
LastNodTime=time.time()
NodTimeWindow=2.5
NodThreshold=20


cap =cv2.VideoCapture(0)
FPS = cap.get(cv2.CAP_PROP_FPS)
if FPS == 0:
    FPS = 25
FRAME_THRESHOLD = int(FPS * 0.8)
frameCounter = 0
EAR_THRESHOLD = None
calibration_frames = 30
earValues = []
while True:
    ret,frame=cap.read()
    if not ret:
        break

    h,w,_=frame.shape
    rgbFrame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    mpImage= mp.Image(image_format=mp.ImageFormat.SRGB,data=rgbFrame)
    result=detector.detect(mpImage)

    if result.face_landmarks:
        face_landmark = result.face_landmarks[0]
        for landmark in face_landmark:
            x=int(landmark.x*w)
            y=int(landmark.y*h)
            cv2.circle(frame,(x,y),1,(255,0,0),-1)

        leftear=calculate_EAR(LeftEye,face_landmark,w,h)
        rightear=calculate_EAR(RightEye,face_landmark,w,h)
        ear=(leftear+rightear)/2

        cv2.putText(frame,f"EAR:{ear:0.2f}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

        if EAR_THRESHOLD is None:
            earValues.append(ear)
            cv2.putText(frame, "Calibrating... Keep eyes open",(50,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)
            if len(earValues) >= calibration_frames:
                baseline = np.mean(earValues)
                EAR_THRESHOLD = baseline * 0.75
                print("EAR Threshold:", EAR_THRESHOLD)
                earValues=[]
            continue
        if ear<EAR_THRESHOLD:
            frameCounter+=1
            if frameCounter>=FRAME_THRESHOLD:
                cv2.putText(frame,"DROWSY DRIVER",(50,80),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
        else:
            frameCounter=0
            

        nose=face_landmark[1]
        NoseY=int(nose.y*h)
        if PrevNoseY is not None:
            NoseY=int(0.7*NoseY+0.3*PrevNoseY)

        if PrevNoseY is not None:
            diff=NoseY-PrevNoseY

            if diff > NodThreshold and NodState == "UP":
                NodState="DOWN"

            elif diff < -NodThreshold and NodState == "DOWN":
                NodState="UP"
                NodCount+=1
                LastNodTime=time.time()
                print("Nod detected:",NodCount)
            
        PrevNoseY=NoseY
        
        if frameCounter>=FRAME_THRESHOLD:
            if not drowsy:
                print("Eyes Closed -> Drowsy")
                drowsy=True
                drowsy_start_time=time.time()

        if NodCount>=2:
            cv2.putText(frame,"Repeated Nod ALERT!",(50,120),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,0),3)
            NodCount = 0 
            arduino.write(b'X')
            print("CRITICAL: Repeated Nod → STOP CAR")
            drowsy=True
            drowsy_start_time=time.time()

        elif NodCount==1:
            cv2.putText(frame,"One Nod (IGNORED)",
                        (50,120),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,0),3)

        if drowsy and not alarm_on:
            print("ALARM START")
            threading.Thread(target=play_alarm, daemon=True).start()
            arduino.write(b'S')

        if not drowsy and alarm_on:
            print("Stopping alarm (normal)")
            stop_alarm()
            arduino.write(b'N')
            
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print("Driver responded")
            drowsy=False
            frameCounter=0
            NodCount=0
            drowsy_start_time=None

        if drowsy and drowsy_start_time is not None:
            if time.time()-drowsy_start_time > 10:
                print("STOP CAR")
                stop_alarm()
                arduino.write(b'X')
                drowsy=False
                frameCounter=0
                NodCount=0

        currentTime=time.time()
        if currentTime-LastNodTime > NodTimeWindow and NodCount<2:
            NodCount=0   

            
        try:
            if drowsy!=prevstate:
                if drowsy:
                    arduino.write(b'1')
                else:
                    arduino.write(b'0')
                prevstate=drowsy
        except:
            pass
        
    cv2.imshow("Driver Drowsiness Detection",frame)
    if cv2.waitKey(1)& 0XFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()