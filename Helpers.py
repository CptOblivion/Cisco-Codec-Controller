import sys
import time
import os
import tkinter as tk
from tkinter import messagebox

VersionNumber = '0.56.4' #previous: 0.56.3

class deltaTime():
    lastTime=0
    delta = 0
    def update():
        newTime = time.perf_counter()
        deltaTime.delta = newTime-deltaTime.lastTime
        deltaTime.lastTime=newTime
        
class Assets():
    def getAsset(asset):
        if (hasattr(sys, '_MEIPASS')):
            return os.path.join(sys._MEIPASS, 'Assets', asset)
        else:
            return os.path.join('Assets', asset)

class controller():
    #easy link to get the current CameraController instance
    #so classes can refer back to CameraController without having to deal with importing it
    current=None

class controlDirect():
    def __init__(self, command=None, delay=.1):
        self.delayTimer = self.delay=.1
        self.value = None
        self.command=command
        self.enabled=True
    def set(self, value):
        self.value = value
        self.delayTimer=self.delay
    def update(self): #call every program loop iteration! Make sure deltaTime.update() is also being called every iteration!
        if (self.delayTimer > 0):
            self.delayTimer-=deltaTime.delta
            if (self.delayTimer <=0):
                if (self.value is not None and self.enabled): self.command(self.value)