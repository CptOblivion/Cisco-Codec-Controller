import sys
import time
import os
import tkinter as tk

VersionNumber = '0.54' #previous: 0.53

class deltaTime():
    lastTime=0
    delta = 0
    def update():
        newTime = time.perf_counter()
        deltaTime.delta = newTime-deltaTime.lastTime
        deltaTime.lastTime=newTime
        
class Assets():
    def getPath(path):
        basePath=getattr(sys, '_MEIPASS', os.path.abspath('.')) #abspath(__file__) instead?
        return os.path.join(basePath, path)

class configPanel():
    #basically-empty class to drop variables in to conveniently contain access to config panel elements for access between classes
    None

class controller():
    #easy link to get the current CameraController instance
    current=None

class inputRouting():
    settingsListenForInput = None
    def bindCommand(deviceType, deviceSubtype,inputType, contents):
        commandTypeIndex = inputType=='analog' #0 if it's 'button', 1 if it's 'analog'
        if ((commandTypeIndex==1) or inputRouting.settingsListenForInput.commandType[commandTypeIndex]): #TODO: this is a hacky holdover. Rework to a cleaner version of "button can take analog input, analog can't take digital input"
            inputRouting.settingsListenForInput.changeDeviceType(None)
            inputRouting.settingsListenForInput.setDevice(deviceType, deviceSubtype, contents)
            inputRouting.bindListenCancel()
    def bindListen(bindingFrame):
        inputRouting.bindListenCancel()
        inputRouting.settingsListenForInput = bindingFrame
        bindingFrame.listenButton.config(relief='sunken')

    def bindListenCancelSafe():
        inputRouting.expectedType=None
        inputRouting.settingsListenForInput = None
    def bindListenCancel(): 
        if (inputRouting.settingsListenForInput):
            inputRouting.settingsListenForInput.listenButton.config(relief='raised')
        inputRouting.bindListenCancelSafe()

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