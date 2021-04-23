import sys
import time
import os
import tkinter as tk

VersionNumber = '0.WIP' #previous: 0.46.1

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