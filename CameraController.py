VersionNumber = '0.WIP' #previous: 0.46.1

import tkinter as tk
import time
import paramiko
import pygame
import pygame.midi
import pygame.joystick
import math
import sys
from configparser import ConfigParser
from copy import deepcopy

class debug():
    #turning this to True will force the UI to always show Camera 2 and 3 as connected
    forceCameraConnection = False
    
    #turning this to true will add a bunch of extra debug prints to the console
    verbosePrints = False

    def print(message):
        if (debug.verbosePrints): print(message)

#Note to self: F9 on a line to set a breakpoint

class CameraController():
    current = None #singleton, baybee!

    def __init__(self):
        CameraController.current=self
        
        for arg in sys.argv:
            if (arg=='DebugCam'):
                debug.forceCameraConnection=True
                print('forcing debug cameras on')
            elif (arg=='Verbose'):
                debug.verbosePrints=True
                debug.print('verbose printing on')
            elif (arg=='DummySSH'):
                DummySSH.UseDummy=True

        self.init = False

        self.window = tk.Tk()
        self.window.title('Cisco Codec Controller XD Deluxe 9000 👌👏😁👍')

        #Pan: 0-816
        #Tilt: 0-212
        #Zoom: 0-2885
        #Focus: 4096-4672
        self.PanSpeed = tk.IntVar()#1-15
        self.TiltSpeed = tk.IntVar() #1-15
        self.ZoomSpeed = tk.IntVar() #1-15
        self.PanSpeed.set(1)
        self.TiltSpeed.set(1)
        self.ZoomSpeed.set(0)
        self.CameraCount = 0
        self.cameras=[None, camera(1), camera(2), camera(3), camera(4), camera(5), camera(6), camera(7)]

        self.CameraPanning = False
        self.CameraTilting = False
        self.CameraZooming = False
        self.CameraFocusing = False
        self.webcamFlip = tk.IntVar()
        self.webcamFlip.set(1)

        self.CameraPanCenter, self.CameraTiltCenter, self.CameraZoomCenter, self.CameraFocusCenter = 408, 126, 49,457

        self.LastTime = time.perf_counter()
        self.OptionsMenuOpen = False
        self.ConfigUpdateTimer = self.ConfigUpdateInterval = 10.0


        self.PadExt = 15 #padding around container frames
        self.PadInt = 3 #padding around internal frames

        self.BlankCommand = 'Empty command'
        self.PrefabCommands = [
            'xCommand Camera PositionSet Pan:# Tilt:# Zoom:# Focus:# CameraID:#',
            'xConfiguration Cameras Camera # Backlight: On',
            'xCommand Camera Preset Store PresetId: 1 CameraID:# ListPosition: 1 Name: ""'
            ]

        self.UserPrefabCommands= []

        self.PrefabCommandCurrentCamera = 'CameraID:#'
        self.PrefabConfigCurrentCamera = 'Camera #'


        #the codec is 1-indexed, so we'll ignore [0] and use [1]-[35]
        self.CameraPresets = [] #list of CameraPreset 
        self.CamerasPresets = [] #probably won't use, but reserving the variable name
        self.Frame_PresetsContainer = None
        self.PresetsFiltered = False

        self.inputBuffer = None
        self.inputBufferTime = self.inputBufferTimer = .05 #TODO: make configurable

        self.commandBindsEmpty={
            'midi':{
                'note': [], #note binds are deviceName, channel, note
                'control':[]}, #control binds are deviceName, channel, CC#
            'controller':{
                'button':[], #button binds are buttonNum
                'axis':[], #axis binds are axisNum, axisType, flip
                'hat':[]}} #hat bindings are hatNum, hatDirection

        for i in range(20): #space for 20 buttons, 20 axes
            self.commandBindsEmpty['controller']['button'].append(None)
            self.commandBindsEmpty['controller']['axis'].append(None)
        for i in range(4): #4 hats (8 directions each)
            self.commandBindsEmpty['controller']['hat'].append([None,None,None,None,None,None,None,None])

        self.commandBinds={}
        self.inputDevicesMidis = []
        self.inputDevicesMidiNames=[]
        self.inputDevicesControllers = []
        self.hatBoundVal = [None,None,None,None,None,None,None,None]

        self.joystickPanAxesRaw = [0,0]
        self.joystickPanAxesInt = [0,0]
        self.rampZoomValue = 0
        self.rampFocusValue = 0

        self.directControls = {
                                'pan':controlDirect(command = lambda value: self.QueueInput(lambda: self.SetPanTilt(value, None))),
                                'tilt':controlDirect(command = lambda value: self.QueueInput(lambda: self.SetPanTilt(None, value))),
                                'zoom':controlDirect(command = lambda value: self.QueueInput(lambda: self.SetZoom(value))),
                                'focus':controlDirect(command = lambda value: self.QueueInput(lambda: self.SetFocus(value)))}


        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.SettingsMenu= None
        self.SettingsMenuOld = None
        
        self.loadControls()
        
        Settings.openConfig()
        
        self.printCodecResponse=tk.IntVar()
        self.printCodecResponse.set(int(Settings.config['Startup']['PrintFullCodecResponse']))

        self.parseBindings(Settings.config['Startup']['Bindings'])

        UserPrefabCommandsTemp = Settings.config['User Commands'][Settings.CustomCommandName].splitlines()
        for command in UserPrefabCommandsTemp:
            if (command): self.UserPrefabCommands.append(command)

        self.PopulateStartScreen()

    def updateDirectValues(self):
        for key in self.directControls:
            self.directControls[key].update()

    def TriggerAutofocus(self):
        self.xCommand('TriggerAutoFocus')
    #TODO: check if we're already at limits, since the camera won't move (and thus won't return a new position) if we try to go past
    def PanningStart(self):
        self.CameraPanning=True
        self.LabelPan.config(fg='red')
    def TiltingStart(self):
        self.CameraTilting=True
        self.LabelTilt.config(fg='red')
    def ZoomingStart(self):
        self.CameraZooming=True
        self.LabelZoom.config(fg='red')
    def FocusingStart(self):
        self.CameraFocusing=True
        self.LabelFocus.config(fg='red')
    def PanningDone(self):
        self.CameraPanning=False
        self.LabelPan.config(fg='black')
    def TiltingDone(self):
        self.CameraTilting=False
        self.LabelTilt.config(fg='black')
    def ZoomingDone(self):
        self.CameraZooming=False
        self.LabelZoom.config(fg='black')
    def FocusingDone(self):
        self.CameraFocusing=False
        self.LabelFocus.config(fg='black')
    def CanMove(self):
        return not (self.CameraPanning or self.CameraTilting or self.CameraZooming or self.CameraFocusing)

    def xStatus(self, message, CamNumber = None):
        if (not CamNumber): CamNumber = camera.selectedNum
        message = 'xStatus Camera ' + str(CamNumber) + ' ' + message
        self.shell.send(message+'\n')

    def xCommand(self,message, CamNumber = None):
        if (not CamNumber): CamNumber = camera.selectedNum
        message = 'xCommand Camera ' + message + ' CameraID:' + str(CamNumber)
        self.shell.send(message+'\n')
        print('Message sent: ' + message)

    def xConfiguration(self,message, CamNumber = None):
        if (not CamNumber): CamNumber = camera.selectedNum
        message='xConfiguration Cameras Camera ' + str(CamNumber) + ' ' + message
        self.shell.send(message+'\n')
        print('Message sent: ' + message)

    def FeedbackSubscribe(self):
        self.FeedbackUpdate(None, 1)
        for i in range(7):
            self.shell.send('xfeedback register /Status/Camera[@item='' + str(i+1) + '']/Connected\n')
        #TODO: subscribe to all seven camera position statuses at once? (test if this is viable)
    def FeedbackUpdate(self, OldCam, NewCam):
        if (OldCam != None):
            self.shell.send('xfeedback deregister /Status/Camera[@item="' +str(OldCam)+'"]/position\n')
            self.shell.send('xfeedback deregister /Configuration/Cameras/Camera[@item="' +str(OldCam)+'"]/Brightness/Level\n')
            self.shell.send('xfeedback deregister /Configuration/Cameras/Camera[@item="' +str(OldCam)+'"]/Whitebalance/Level\n')
            self.shell.send('xfeedback deregister /Configuration/Cameras/Camera[@item="' +str(OldCam)+'"]/Gamma/Level\n')
        self.shell.send('xfeedback register /Status/Camera[@item="' +str(NewCam)+'"]/position\n')
        self.shell.send('xfeedback register /Configuration/Cameras/Camera[@item="' +str(NewCam)+'"]/Brightness/Level\n')
        self.shell.send('xfeedback register /Configuration/Cameras/Camera[@item="' +str(NewCam)+'"]/Whitebalance/Level\n')
        self.shell.send('xfeedback register /Configuration/Cameras/Camera[@item="' +str(NewCam)+'"]/Gamma/Level\n')

    def SendManualCommand(self, entryWidget):
        message = entryWidget.get()
        message = message.replace(self.PrefabCommandCurrentCamera, 'CameraID:' + str(camera.selectedNum))
        message = message.replace(self.PrefabConfigCurrentCamera, 'Camera ' + str(camera.selectedNum))

        self.shell.send(message + '\n')
        print('Message sent: ' + message)

        
    def toggleAllPresetEditStates(self, state):
        for child in self.Frame_PresetsContainer.winfo_children():
            child.SetEditState(state)
    def filterPresetsCurrent(self, filter):
        self.PresetsFiltered = filter
        for child in self.Frame_PresetsContainer.winfo_children():
            child.filter()

    def ListPresetsCamera(self):
        self.shell.send('xCommand Camera Preset List\n')

    def CreateNewPreset(self):
        self.shell.send('xCommand Camera Preset Store CameraId: ' + str(camera.selectedNum) + ' Name: "Unnamed"\n')

    def InitializePresetLists(self):
        print('initializing presets')
        self.CameraPresets=[]
        for i in range(36):
            self.CameraPresets.append(None)
        if (self.Frame_PresetsContainer):
            for child in self.Frame_PresetsContainer.winfo_children():
                child.destroy()
        self.CamerasPresets=[]
        self.ListPresetsCamera()

    def UpdatePresetButton(self, PresetIndex):
        presetPanel = self.CameraPresets[PresetIndex].widget
        if (not presetPanel):
            presetPanel = CameraPresetPanel(self.Frame_PresetsContainer, PresetIndex)
            presetPanel.grid(column=0, row=PresetIndex, sticky='ew')
            self.CameraPresets[PresetIndex].widget = presetPanel
        presetPanel.updateContents()

    def StartMove(self, X, Y):
        if True:#(CameraPanning == CameraTilting == False):
            X*= self.webcamFlip.get()
            command = 'Ramp'
            if (X < 0):
                command += ' Pan:left PanSpeed:' + str(-X)
                #PanningStart()
            elif (X > 0):
                command += ' Pan:right PanSpeed:' + str(X)
                #PanningStart()
            if (Y < 0):
                command += ' Tilt:down TiltSpeed:' + str(-Y)
                #TiltingStart()
            elif (Y > 0):
                command += ' Tilt:up TiltSpeed:' + str(Y)
                #TiltingStart()
            self.xCommand(command)
    def StopMove(self, discard): self.xCommand('Ramp Pan:stop Tilt:stop')

    def SetZoom(self, value):
        #TODO: detect if slider is still moving, don't send command until it's stopped (no new updates for some number of ms)
        ZoomRange=2885
        self.ZoomingStart()
        self.xCommand('PositionSet Zoom: ' + str(value*ZoomRange))

    def SetFocus(self, value):
        #TODO: detect if slider is still moving, don't send command until it's stopped (no new updates for some number of ms)
        focusRange=(4096,4672)
        value = value*(focusRange[1]-focusRange[0]) + focusRange[0]
        self.FocusingStart()
        self.xCommand('PositionSet Focus: ' + str(value))
    
    def SetPanTilt(self, p, t):
        panRange = 816
        tiltRange = 212


        sendString = 'PositionSet'
        if (p is not None and p!= self.CameraPan):
            self.PanningStart()
            sendString += ' Pan: ' + str(p*panRange)
        if (t is not None and t != self.CameraTilt):
            self.TiltingStart()
            sendString += ' Tilt: ' + str(t*tiltRange)

        self.xCommand(sendString)

    def CenterCamera(self):
        self.xCommand('PositionReset')
        if (self.CameraPan != self.CameraPanCenter): self.PanningStart()
        if (self.CameraTilt != self.CameraTiltCenter): self.TiltingStart()
        if (self.CameraZoom != self.CameraZoomCenter): self.ZoomingStart()
        if (self.CameraFocus != self.CameraFocusCenter): self.FocusingStart() #check if focus is manual before doing this

    def ZoomIn(self, discard):self.xCommand('Ramp Zoom:In ZoomSpeed:' + str(self.ZoomSpeed.get()))
    def ZoomOut(self, discard):self.xCommand('Ramp Zoom:Out ZoomSpeed:' + str(self.ZoomSpeed.get()))
    def startZoom(self, value):
        if (value>0):self.xCommand('Ramp Zoom:In ZoomSpeed:' + str(value))
        else:self.xCommand('Ramp Zoom:Out ZoomSpeed:' + str(-value))
    def StopZoom(self, discard): self.xCommand('Ramp Zoom:Stop')
    def FocusFar(self, discard):self.xCommand('Ramp Focus:Far')
    def FocusNear(self, discard):self.xCommand('Ramp Focus:Near')
    def startFocus(self, value):
        if (value>0):self.xCommand('Ramp Focus:Far')
        else:self.xCommand('Ramp Focus:Near')
    def StopFocus(self, discard): self.xCommand('Ramp Focus:Stop')

    def nudge(self, P=0, T=0, Z=0, F=0):
        Command = 'PositionSet'
        if (P != 0):
            Command += ' Pan:' + str(self.CameraPan+P)
            self.PanningStart()
        if (T != 0):
            Command += ' Tilt:' + str(self.CameraTilt+T)
            self.TiltingStart()
        if (Z != 0):
            Command += ' Zoom:' + str(self.CameraZoom+Z)
            self.ZoomingStart()
        if (F != 0):
            Command += ' Focus:' + str(self.FocusZoom+Z)
            self.FocusingStart()
        self.xCommand(Command)

    def AddDirectionButton(self, label,frame,gridY, gridX, functionDn, functionUp, image=None):
        if (image):
            try: image = tk.PhotoImage(file = image)
            except: image=None
        if (image): button = tk.Button(frame, image=image, relief='flat', borderwidth=0)
        else: button = tk.Button(frame, text=label, width=3, height=2)
        button.image = image
        button.grid(row=gridY,column=gridX, sticky='nsew')
        button.bind('<ButtonPress-1>', functionDn)
        button.bind('<ButtonRelease-1>', functionUp)
        return button

    def OnCameraChange(self, cameraNumber):
        if (cameraNumber != camera.selectedNum): self.FeedbackUpdate(camera.selectedNum, cameraNumber)

        if (self.Frame_PresetsContainer): self.filterPresetsCurrent(self.PresetsFiltered)
        configPanel.toggleFocusManual.config(variable=camera.selected.focusManual)
        configPanel.toggleBrightnessManual.config(variable=camera.selected.brightnessManual)
        configPanel.ScaleBrightness.config(variable=camera.selected.brightnessValue)
        configPanel.toggleGammaManual.config(variable=camera.selected.gammaManual)
        configPanel.ScaleGamma.config(variable=camera.selected.gammaValue)
        configPanel.toggleWhitebalanceManual.config(variable=camera.selected.whitebalanceManual)
        configPanel.ScaleWhitebalance.config(variable=camera.selected.whitebalanceValue)
        self.UpdateCameraDetails()

    def UpdateCameraDetails(self):
        self.xStatus('Position')
        self.GetCameraConfig(camera.selectedNum)
    def UpdateCameraConnectionStatus(self):
        for i in range(7):
            self.shell.send('xStatus Camera ' + str(i+1) + ' Connected\n')

    def CameraAvailable(self, cameraNumber, available):
        if (available): self.cameras[cameraNumber].onEnable()
        else:
            self.cameras[cameraNumber].onDisable()
            if (cameraNumber == camera.selectedNum):
                i=1
                for cam in self.cameras:
                    if (cam.connected):
                        cam.select()
                    break
                    i += 1
                if (i==8): #if we got through the end of cameras without finding a match
                    #TODO: disable interface
                    print ('no connected cameras!')

    def UpdateCustomCommandList(self):
        CustomCommandString = ''
        for command in self.UserPrefabCommands:
            CustomCommandString += '\n' + command
        Settings.config['User Commands'][self.CustomCommandName] = CustomCommandString

    def SaveCustomCommand(self, frame, customCommand):
        self.PrefabCommandsList.add_command(label=customCommand, command=lambda: self.AddCustomCommand(frame, customCommand))

        Frame_Command = tk.Frame(self.SavedPrefabCommandsView.contentFrame, bg='white')
        Frame_Command.pack(fill='x')
        tk.Label(Frame_Command, text=customCommand, bg='white').pack(side='left')
        tk.Button(Frame_Command, text='Delete', command = lambda f=Frame_Command: self.DeleteCustomCommand(f)).pack(side='right')

        self.UserPrefabCommands.append(customCommand)
        self.UpdateCustomCommandList()
        Settings.SaveConfig()

    def UpdateWindowCellWeights(self, widget, row, rootFrame=None):
        weight=max(0, widget.canvas.bbox('all')[3]-widget.winfo_reqheight())
        if rootFrame:
            weight = max(0, weight + widget.master.winfo_reqheight() - rootFrame.winfo_reqheight()+8) #TODO: is that off-by-8 an artifact of the formula being bad, or am I just not accounting for two sets of width-2 borders or something?
            #TODO: this will need to also update when the parent frame reconfigures due to other contents changing (EG configuration panel opening or closing will change minsize for presets)
        self.window.rowconfigure(row, weight=weight)

    def RemoveCustomCommand(self, frame):
        frame.destroy()

    def DeleteCustomCommand(self, frame):
        index = frame.master.winfo_children().index(frame)
        print('Deleting ' + str(index))
        #command = UserPrefabCommands[index]
        del self.UserPrefabCommands[index]
        self.PrefabCommandsList.delete(index + self.PrefabCommandCustomStart)
        frame.destroy()
        self.UpdateCustomCommandList()
        Settings.SaveConfig()

    def AddCustomCommand(self, command):
        Frame_CommandParent = tk.Frame(self.Frame_CustomCommands, relief='groove', borderwidth = 2)
        Frame_CommandParent.pack(fill='x')

        RemoveButton = tk.Button(Frame_CommandParent, text='x', command=Frame_CommandParent.destroy)#lambda:root.RemoveCustomCommand(Frame_CommandParent))
        CommandEntry = tk.Entry(Frame_CommandParent)
        SaveButton = tk.Button(Frame_CommandParent, text='Save', command=lambda:self.SaveCustomCommand(self.Frame_CustomCommands, CommandEntry.get()))

        CommandEntry.insert(0, command)
        CommandEntry.bind('<Return>', lambda event: self.SendManualCommand(CommandEntry))
        CommandButton = tk.Button(Frame_CommandParent, text='Send', command = lambda: self.SendManualCommand(CommandEntry))

        RemoveButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)
        SaveButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)
        CommandEntry.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt, fill='x', expand=True)
        CommandButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)

    def SetBrightnessLevel(self, Scale):
        self.xConfiguration('Brightness Level: ' + str(Scale.get()))
        Scale.config(variable=camera.selected.brightnessValue)
    def SetWhitebalanceLevel(self, Scale):
        self.xConfiguration('Whitebalance Level: ' + str(Scale.get()))
        Scale.config(variable=camera.selected.whitebalanceValue)
    def SetGammaLevel(self, Scale):
        self.xConfiguration('Gamma Level: ' + str(Scale.get()))
        Scale.config(variable=camera.selected.gammaValue)
    def SetFocusAuto(self):
        if (camera.selected.focusManual.get()): self.xConfiguration('Focus Mode: Auto')
        else: self.xConfiguration('Focus Mode: Manual')
    def SetBrightnessAuto(self):
        if (camera.selected.brightnessManual.get()): self.xConfiguration('Brightness Mode: Auto')
        else: self.xConfiguration('Brightness Mode: Manual')
    def SetWhitebalanceAuto(self):
        if (camera.selected.whitebalanceManual.get()): self.xConfiguration('Whitebalance Mode: Auto')
        else: self.xConfiguration('Whitebalance Mode: Manual')
    def SetGammaAuto(self):
        if (camera.selected.gammaManual.get()): self.xConfiguration('Gamma Mode: Auto')
        else: self.xConfiguration('Gamma Mode: Manual')
    def GetCameraConfig(self, camNumber):
        self.xConfiguration('Focus Mode', CamNumber = camNumber)
        self.xConfiguration('Brightness Mode', CamNumber = camNumber)
        self.xConfiguration('Whitebalance Mode', CamNumber = camNumber)
        self.xConfiguration('Gamma Mode', CamNumber = camNumber)
        self.xConfiguration('Brightness Level', CamNumber = camNumber)
        self.xConfiguration('Whitebalance Level', CamNumber = camNumber)
        self.xConfiguration('Gamma Level', CamNumber = camNumber)

    def PopulateButtons(self):
        Frame_Main = tk.Frame(self.window)

        #TODO: find better alternative than 'if True:' to allow indentation for organization of UI code
        if True:
            self.Frame_CameraList = tk.Frame(Frame_Main, relief='sunken', borderwidth=2)
            if True:
                for i in range(7):
                    cami=i+1
                    #'lambda i=i' makes a new property within the lambda scope to store the current iteration value (rather than a reference to the original i, which keeps increasing)
                    self.cameras[cami].selectButton = tk.Button(self.Frame_CameraList, text=str(cami)+'  ', image=camera.imageCamAvailable, compound='center', command=lambda cami=cami: self.cameras[cami].select())
                    self.cameras[cami].selectButton.pack(padx=self.PadInt, pady=self.PadInt)
                #self.cameras[1].select()
                tk.Button(self.Frame_CameraList, text='Refresh', command=self.UpdateCameraConnectionStatus).pack(padx=self.PadInt, pady=self.PadInt)

            Frame_Readout = tk.Frame(Frame_Main, relief='ridge', borderwidth=2)
            if True:
                self.LabelPan=tk.Label(Frame_Readout, text='Pan: -')
                self.LabelTilt=tk.Label(Frame_Readout, text='Tilt: -')
                self.LabelZoom=tk.Label(Frame_Readout, text='Zoom: -')
                self.LabelFocus=tk.Label(Frame_Readout, text='Focus: -')

                self.LabelPan.pack()
                self.LabelTilt.pack()
                self.LabelZoom.pack()
                self.LabelFocus.pack()
                tk.Button(Frame_Readout, text='Refresh', command=self.UpdateCameraDetails).pack(pady=self.PadInt)

            Frame_ButtonGrid = tk.Frame(Frame_Main, relief='sunken', borderwidth=2)
            if True:
                self.AddDirectionButton('↖', Frame_ButtonGrid, 1, 1, lambda event: self.StartMove(-self.PanSpeed.get(),self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_LU.png')
                self.AddDirectionButton('⬆', Frame_ButtonGrid, 1, 2, lambda event: self.StartMove(0,self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_U.png')
                self.AddDirectionButton('↗', Frame_ButtonGrid, 1, 3, lambda event: self.StartMove(self.PanSpeed.get(),self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_RU.png')
                self.AddDirectionButton('⬅', Frame_ButtonGrid, 2, 1, lambda event: self.StartMove(-self.PanSpeed.get(),0),self.StopMove, image=r'Assets\Arrow_L.png')
                self.AddDirectionButton('➡', Frame_ButtonGrid, 2, 3, lambda event: self.StartMove(self.PanSpeed.get(),0),self.StopMove, image=r'Assets\Arrow_R.png')
                self.AddDirectionButton('↙', Frame_ButtonGrid, 3, 1, lambda event: self.StartMove(-self.PanSpeed.get(),-self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_LD.png')
                self.AddDirectionButton('⬇', Frame_ButtonGrid, 3, 2, lambda event: self.StartMove(0,-self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_D.png')
                self.AddDirectionButton('↘', Frame_ButtonGrid, 3, 3, lambda event: self.StartMove(1,-self.TiltSpeed.get()),self.StopMove, image=r'Assets\Arrow_RD.png')
                self.AddDirectionButton('Z+', Frame_ButtonGrid, 1, 5, self.ZoomIn,self.StopZoom)
                self.AddDirectionButton('Z-', Frame_ButtonGrid, 2, 5, self.ZoomOut,self.StopZoom)
                self.AddDirectionButton('F+', Frame_ButtonGrid, 1, 6, self.FocusFar, self.StopFocus)
                self.AddDirectionButton('F-', Frame_ButtonGrid, 2, 6, self.FocusNear, self.StopFocus)
                image=tk.PhotoImage(file=r'Assets\Arrow_C.png')
                button=tk.Button(Frame_ButtonGrid, text='FTrig', relief='flat', borderwidth=0, image=image, command= self.TriggerAutofocus)
                button.grid(column=2, row=2)
                button.image=image

                tk.Scale(Frame_ButtonGrid, variable=self.PanSpeed, from_=1,to_=15, orient='horizontal').grid(column=1, row=0, columnspan=3)
                tk.Scale(Frame_ButtonGrid, variable=self.TiltSpeed, to_=1,from_=15, orient='vertical').grid(column=0,row=1, rowspan=3)
                tk.Scale(Frame_ButtonGrid, variable=self.ZoomSpeed, to_=1,from_=15, orient='vertical').grid(column=4,row=1, rowspan=2)

                tk.Checkbutton(Frame_ButtonGrid, text='flip X', variable=self.webcamFlip, offvalue=1, onvalue=-1).grid(column=5, row=3, columnspan=2)


                ButtonRecenter= tk.Button(Frame_ButtonGrid,text='Recenter', command=self.CenterCamera)
                ButtonRecenter.grid(column=0, row=4, padx=3, pady=3, columnspan=2)

            Frame_Presets = tk.Frame(Frame_Main, relief='sunken', borderwidth=2)
            if True:
                Frame_PresetsToolbar1 = tk.Frame(Frame_Presets)
                if True:
                    tk.Button(Frame_PresetsToolbar1, text='New preset', command = self.CreateNewPreset).pack(side='left')
                    tk.Button(Frame_PresetsToolbar1, text = 'Reload', command = self.InitializePresetLists).pack(side='left')
            
                Frame_PresetsToolbar2 = tk.Frame(Frame_Presets)
                if True:
                    self.TogglePresetEdit = ToggleButtonChecked(Frame_PresetsToolbar2, textOff=['locked', 'unlock'], textOn = ['lock','unlocked'], toggleCommand=self.toggleAllPresetEditStates)
                    self.TogglePresetEdit.pack(side='left')
                
                    ToggleButtonChecked(Frame_PresetsToolbar2, textOff=['unfiltered', 'filter'], textOn = ['unfilter', 'filtered'], toggleCommand=self.filterPresetsCurrent).pack(side='left')
                
                self.Frame_PresetsContainer = ScrollFrame(Frame_Presets, cHeight=0, frameConfigureCommand=lambda widget: self.UpdateWindowCellWeights(widget, 0, rootFrame=Frame_Main))

                Frame_PresetsToolbar1.pack()
                Frame_PresetsToolbar2.pack()
                self.Frame_PresetsContainer.pack(fill='both', expand=True)

                self.Frame_PresetsContainer = self.Frame_PresetsContainer.contents #from here on out, we only care about accessing the contents so we'll just change the variable over to avoid accidentally addressing the parent
                self.Frame_PresetsContainer.columnconfigure(0, weight=1) #the column should stretch to fill available space
            


            def OptionsMenuToggle(toggle):
                self.OptionsMenuOpen = toggle
                if (toggle):
                    self.GetCameraConfig(camera.selectedNum)
                    self.ConfigUpdateTimer = self.ConfigUpdateInterval
            Frame_SetupPanel = tk.Frame(Frame_Main)
            if True:
                tk.Button(Frame_SetupPanel, text='settings', command=self.OpenSettingsMenu).pack(side='top')

                self.Frame_ConfigPopout = ToggleFrame(Frame_SetupPanel, title='Configuration', keepTitle=True, relief='groove', borderwidth=2, buttonShowTitle='show', buttonHideTitle='hide', toggleCommand=OptionsMenuToggle, togglePin='left').contentFrame
                if True:
                    Frame_FocusMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_FocusMode, text='Focus').pack(pady=(2,0))
                        frame_FocusButtons = tk.Frame(Frame_FocusMode)
                        if True:
                            
                            configPanel.toggleFocusManual=tk.Checkbutton(frame_FocusButtons, text='Auto', command=self.SetFocusAuto)
                            configPanel.toggleFocusManual.pack(side='left')
                            #self.ToggleFocusManual = ToggleButtonChecked(frame_FocusButtons, textOff=['auto', 'go manual'], textOn=['go auto', 'manual'], toggleCommand=self.SetFocusManual)
                            #self.ToggleFocusManual.pack(side='left')
                        frame_FocusButtons.pack(fill='x')

                    Frame_BrightnessMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_BrightnessMode, text='Brightness').pack(pady=(2,0))
                        frame_BrightnessButtons = tk.Frame(Frame_BrightnessMode)
                        if True:
                            #self.ToggleBrightnessManual = ToggleButtonChecked(frame_BrightnessButtons, textOff=['auto', 'go manual'], textOn=['go auto', 'manual'], toggleCommand=self.SetBrightnessManual)
                            configPanel.ScaleBrightness = tk.Scale(frame_BrightnessButtons, from_=1, to_=31, orient='horizontal')
                            configPanel.ScaleBrightness.bind('<ButtonPress-1>', lambda event: configPanel.ScaleBrightness.config(variable=None)) #TODO: this is supposed to unbind the vairable while we have the cursor down, so incoming updates don't move it out from under us, but it doesn't work
                            configPanel.ScaleBrightness.bind('<ButtonRelease-1>', lambda event: self.SetBrightnessLevel(configPanel.ScaleBrightness))

                            #self.ToggleBrightnessManual.pack(side='left')
                            configPanel.toggleBrightnessManual = tk.Checkbutton(frame_BrightnessButtons, text='Auto', command=self.SetBrightnessAuto)
                            configPanel.toggleBrightnessManual.pack(side='left')
                            configPanel.ScaleBrightness.pack(side='left', fill='x')
                        frame_BrightnessButtons.pack(fill='x')

                    Frame_WhitebalanceMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_WhitebalanceMode, text='White Balance').pack(pady=(2,0))
                        frame_WhitebalanceButtons = tk.Frame(Frame_WhitebalanceMode)
                        if True:
                            #self.ToggleWhitebalanceManual = ToggleButtonChecked(frame_WhitebalanceButtons, textOff=['auto', 'go manual'], textOn=['go auto', 'manual'], toggleCommand=self.SetWhitebalanceManual)
                            configPanel.ScaleWhitebalance = tk.Scale(frame_WhitebalanceButtons, from_=1, to_=16, orient='horizontal')
                            configPanel.ScaleWhitebalance.bind('<ButtonPress-1>', lambda event: configPanel.ScaleWhitebalance.config(variable=None))
                            configPanel.ScaleWhitebalance.bind('<ButtonRelease-1>', lambda event: self.SetWhitebalanceLevel(configPanel.ScaleWhitebalance))

                            #self.ToggleWhitebalanceManual.pack(side='left')
                            configPanel.toggleWhitebalanceManual=tk.Checkbutton(frame_WhitebalanceButtons, text='Auto', command=self.SetWhitebalanceAuto)
                            configPanel.toggleWhitebalanceManual.pack(side='left')
                            configPanel.ScaleWhitebalance.pack(side='left', fill='x')
                        frame_WhitebalanceButtons.pack(fill='x')

                    Frame_GammaMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_GammaMode, text='Gamma').pack(pady=(2,0))
                        frame_GammaButtons = tk.Frame(Frame_GammaMode)
                        if True:
                            configPanel.ScaleGamma = tk.Scale(frame_GammaButtons, from_=0, to_=7, orient='horizontal')
                            configPanel.ScaleGamma.bind('<ButtonPress-1>', lambda event: configPanel.ScaleGamma.config(variable=None))
                            configPanel.ScaleGamma.bind('<ButtonRelease-1>', lambda event: self.SetGammaLevel(configPanel.ScaleGamma))

                            configPanel.toggleGammaManual = tk.Checkbutton(frame_GammaButtons, text='Auto', command=self.SetGammaAuto)
                            configPanel.toggleGammaManual.pack(side='left')
                            configPanel.ScaleGamma.pack(side='left', fill='x')
                        frame_GammaButtons.pack(fill='x')
    
            
                    Frame_FocusMode.pack(fill='x')
                    Frame_BrightnessMode.pack(fill='x')
                    Frame_WhitebalanceMode.pack(fill='x')
                    Frame_GammaMode.pack(fill='x')
            
                self.Frame_ConfigPopout.master.pack(side='top', padx=self.PadInt, pady=self.PadInt)
    
            self.Frame_CameraList.pack(side='left', fill='y',padx=self.PadInt, pady=self.PadInt)
            Frame_Readout.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)
            Frame_ButtonGrid.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)
            Frame_Presets.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)
            Frame_SetupPanel.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)


        Frame_CustomCommandsParent = tk.LabelFrame(self.window, text='Custom commands')
        self.Frame_CustomCommands = ScrollFrame(Frame_CustomCommandsParent, cHeight=0, frameConfigureCommand=lambda widget: self.UpdateWindowCellWeights(widget, 1))
        if True:
            PrefabCommandsButton = tk.Menubutton(Frame_CustomCommandsParent, text='Add Custom Command', relief='raised')
            Frame_CustomCommandsToolbar = tk.Frame(Frame_CustomCommandsParent)
            if True:
                PrefabCommandsButton.pack()

                #TODO: add a scrollbar into this
                self.SavedPrefabCommandsView = ToggleFrame(Frame_CustomCommandsToolbar, title='Saved Commands', buttonShowTitle = 'Show Saved Commands', buttonHideTitle='Hide', relief='groove', borderwidth=2)
                self.SavedPrefabCommandsView.contentFrame.configure(bg='white')
    
                self.SavedPrefabCommandsView.pack(side='right')

                self.PrefabCommandsList= tk.Menu(PrefabCommandsButton, tearoff = 0)
                PrefabCommandsButton['menu'] = self.PrefabCommandsList

                self.PrefabCommandsList.add_command(label='blank command', command=lambda:self.AddCustomCommand(''))
                self.PrefabCommandsList.add_separator()
                for customCommand in self.PrefabCommands:
                    self.PrefabCommandsList.add_command(label=customCommand, command=lambda c=customCommand: self.AddCustomCommand(c))

                self.PrefabCommandsList.add_separator()

                self.PrefabCommandCustomStart=self.PrefabCommandsList.index('end')+2 #index of the end doesn't account for separators, but all other index operations do

                self.PrefabCommandsList.add_command(label='          Custom User Commands:', state='disabled')
                i = 0
                for userCommand in self.UserPrefabCommands:
                    self.PrefabCommandsList.add_command(label=userCommand, command=lambda c=userCommand: self.AddCustomCommand(c))
                    Frame_Command = tk.Frame(self.SavedPrefabCommandsView.contentFrame, bg='white')
                    Frame_Command.pack(fill='x')
                    tk.Label(Frame_Command, text=userCommand,bg='white').pack(side='left')
                    tk.Button(Frame_Command, text='Delete', command=lambda f=Frame_Command: self.DeleteCustomCommand(f)).pack(side='right')

                    i += 1

            Frame_CustomCommandsToolbar.pack(side='bottom', pady=8, fill='x')
            self.Frame_CustomCommands.pack(padx=self.PadExt, pady=self.PadExt, fill='both', expand=True)
            self.Frame_CustomCommands = self.Frame_CustomCommands.contents
    
        Frame_Main.grid(column=0, row=0, padx=self.PadExt, pady=self.PadExt, sticky='nsew')
        Frame_CustomCommandsParent.grid(column=0, row=1, padx=self.PadExt, pady=self.PadExt, sticky='nsew')
        self.window.columnconfigure(0, weight=1)

    def parseBindings(self, bindingString):
        #print (bindingString)
        #TODO: make a class to hold all the save/load stuff, put this in it
        self.commandBinds = deepcopy(self.commandBindsEmpty) #maybe unnecessary to deep copy? The source is like six entries so it's fine either way
        lines=bindingString.splitlines()
        bindables.bindablePresets=[]
        for line in lines:
            if line:
                presetName=None

                segments=line.split(',')
                print(line)
                commandIndex = segments[0]

                if (commandIndex.startswith(bindables.bindingPresetsPrefix)):
                    presetName=commandIndex[len(bindables.bindingPresetsPrefix):]
                    commandIndex=bindables.bindingPresets
                    command=(lambda value, presetName=presetName: bindables.activatePreset(value,presetName), bindables.index[bindables.bindingPresets][1])
                    if (not presetName in bindables.bindablePresets):
                        bindables.bindablePresets.append(presetName)
                else:
                    command=bindables.index[commandIndex]

                def addBinding(binding):
                    if (presetName is not None):
                        binding.bindablePreset=presetName
                    return binding

                bindingDevice, bindingSubdevice = segments[1].split('.')
                if (bindingDevice == 'midi'):
                    midiDevice, midiChannel, inputNumber=segments[2:5]
                    if (len(segments) == 6): threshold=float(segments[5])
                    else: threshold=None
                    if (midiDevice=='any'): midiDevice = None
                    if (midiChannel=='any'): midiChannel = None
                    else: midiChannel = int(midiChannel)
                    if (inputNumber=='any'): inputNumber = None #TODO: parse as int only (no None)
                    else: inputNumber = int(inputNumber)
                    self.commandBinds[bindingDevice][bindingSubdevice].append(addBinding(bindingMidi(midiDevice, midiChannel, inputNumber, command, threshold=threshold)))
                elif (bindingDevice=='controller'):
                    if (bindingSubdevice == 'axis'):
                        axisNum, axisType, axisFlip = segments[2:5]
                        if (len(segments)==6): threshold = float(segments[5])
                        else: threshold=None
                        if (threshold is not None): print(threshold)
                        self.commandBinds['controller']['axis'][int(axisNum)] = addBinding(bindingControllerAxis(axisType, int(axisFlip), command, threshold=threshold))
                    elif (bindingSubdevice == 'button'):
                        button = segments[2]
                        self.commandBinds['controller']['button'][int(button)] = addBinding(bindingControllerButton(command))
                    elif (bindingSubdevice == 'hat'):
                        hatNum, hatDirection = segments[2:]
                        self.commandBinds['controller']['hat'][int(hatNum)][int(hatDirection)] = addBinding(bindingControllerButton(command))
            

    def settingsMenuClosed(self, event):
        self.SettingsMenu=None
        self.enableFrame(self.window)
        inputRouting.bindListenCancelSafe()

    def toggleCodecDebugPrints(self):
        Settings.config['Startup']['PrintFullCodecResponse']=str(self.printCodecResponse.get())
        Settings.SaveConfig()

    noDisable=('Frame', 'Labelframe', 'Scrollbar', 'Toplevel', 'Canvas')
    def disableFrame(self,frame):
        for child in frame.winfo_children():
            wtype= child.winfo_class()
            if (wtype not in self.noDisable):
                child.oldState=child['state']
                child.configure(state='disabled')
            else:
                self.disableFrame(child)
    def enableFrame(self, frame):
        for child in frame.winfo_children():
            wtype= child.winfo_class()
            if (wtype not in self.noDisable):
                if (hasattr(child, 'oldState')):
                    child.configure(state=child.oldState)
                else:
                    child.configure(state='normal')
            elif (wtype == 'Toplevel'):
                None #windows that are child of this one will be ignored
            else:
                self.enableFrame(child)

    def OpenSettingsMenu(self):
        def SaveBindings():
            bindingString = ''
            for command in tempBinds:
                for child in command.BindingList.winfo_children():
                    output = child.makeOutput(command.bindableName)
                    if (output):
                        bindingString += output+'\n'
            self.parseBindings(bindingString)
            Settings.config['Startup']['Bindings'] = bindingString
            Settings.SaveConfig()
        if (self.SettingsMenu is None):
            
            self.disableFrame(self.window)

            self.SettingsMenu = tk.Toplevel(self.window)
    
            self.SettingsMenu.geometry('1200x800')

            debugToggleFrame=tk.Frame(self.SettingsMenu)
            if True:
                tk.Checkbutton(debugToggleFrame, text='print verbose codec responses', variable=self.printCodecResponse, command=self.toggleCodecDebugPrints).pack(side='left')

            bindingsList = ScrollFrame(self.SettingsMenu, cHeight=400)

            tempBinds=[]
            i=0
            categoryFrame=None
            categoryEnd=None
            for key in bindables.index:
                if (key.startswith(bindables.bindingCategory)):
                    categoryEnd=bindables.index[key]
                    title=key[len(bindables.bindingCategory):]
                    categoryFrame=ToggleFrame(bindingsList.contents, title=title, keepTitle=False, buttonShowTitle=title, buttonHideTitle='collapse', togglePin='left', contentPadx=(30,3), relief='groove', borderwidth=2)
                    categoryFrame.pack(fill='x', expand=True)
                    categoryFrame=categoryFrame.contentFrame
                    if (key == bindables.bindingPresets):
                        def addNewPreset(frame):
                            newPanel=ControlBindPresetPanel(frame, bindables.bindingPresetsPrefix+'unnamed', bindables.index[key], 'unnamed', tempBinds, newBinding=True)
                            newPanel.pack(fill='x', expand=True)
                            tempBinds.append(newPanel)

                        panelSide=tk.Frame(categoryFrame)
                        panelSide.pack(side='left', fill='y')
                        panelBody=tk.Frame(categoryFrame)
                        panelBody.pack(side='left', fill='x')
                        tk.Button(panelSide, text='+', command=lambda frame=panelBody: addNewPreset(frame)).pack()

                        for pkey in bindables.bindablePresets:
                            tempBinds.append(ControlBindPresetPanel(panelBody, bindables.bindingPresetsPrefix+pkey, bindables.index[key], pkey, tempBinds))
                            tempBinds[i].pack(fill='x', expand=True)
                            i+=1
                        categoryFrame=None
                        categoryEnd=None
                else:
                    if(categoryFrame):
                        packFrame=categoryFrame
                        if (key==categoryEnd):
                            categoryEnd=categoryFrame=None
                    else:
                        packFrame=bindingsList.contents
                    tempBinds.append(ControlBindPanel(packFrame, key, bindables.index[key]))
                    tempBinds[i].pack(fill='x', expand=True)
                    i+=1
    
            frameFooter = tk.Frame(self.SettingsMenu)
            if True:
                tk.Button(frameFooter, text='save', command=SaveBindings).pack(side='right')
            settingsTitle = tk.Label(self.SettingsMenu, text='Settings')
            settingsTitle.pack()
            settingsTitle.bind('<Destroy>', self.settingsMenuClosed)
            debugToggleFrame.pack(fill='x')
            bindingsList.pack(fill='both', expand=True)
            frameFooter.pack(padx=3, pady=3, fill='x')
        else:
            #TODO: remove this dumb gag
            window=tk.Toplevel(self.window)
            tk.Label(window, text='nice try').pack()

    def PopulateStartScreen(self):
        def SSHConnect():

            Settings.config['Startup']['IPADDRESS'] = AddressField.get()
            Settings.config['Startup']['USERNAME'] = UsernameField.get()
            Settings.config['Startup']['PASSWORD'] = PasswordField.get()

            Settings.SaveConfig()
            if (not DummySSH.UseDummy):
                print('connecting to ' + Settings.config['Startup']['USERNAME'] + '@' + Settings.config['Startup']['IPADDRESS'])


                self.ssh.connect(hostname=Settings.config['Startup']['IPADDRESS'], username=Settings.config['Startup']['USERNAME'], password=Settings.config['Startup']['PASSWORD'])
                self.shell = self.ssh.invoke_shell()
                while not (self.shell.recv_ready()):
                        time.sleep(1)
                out = self.shell.recv(9999)
                print(out.decode('ascii'))
                #TODO: handle connection refused: wrong IP address, username/password incorrect

                #TODO: some sort of check to see if we're connected to the right device
                #   look for: 'Welcome to\r\n Cisco Codec Release' and 'Login successful'
            else:
                self.shell=DummySSH()

            StartFrame.destroy()
            self.PopulateButtons()
            self.FeedbackSubscribe()
            for i in range(7):
                self.CameraAvailable(i+1, False)

            self.UpdateCameraConnectionStatus()
            self.InitializePresetLists()
            self.init = True


        StartFrame = tk.Frame(self.window)
        if True:
            tk.Label(StartFrame, text='Codec Login').pack()

            AddressFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(AddressFrame, text='IP Address').pack(side='left')

                AddressField = tk.Entry(AddressFrame)
                AddressField.insert(0,Settings.config['Startup']['IPADDRESS'])
                AddressField.focus_set()
                AddressField.bind('<Return>',lambda event: SSHConnect)
                AddressField.pack(side='left')

            UsernameFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(UsernameFrame, text='Username').pack(side='left')

                UsernameField = tk.Entry(UsernameFrame)
                UsernameField.insert(0,Settings.config['Startup']['USERNAME'])
                UsernameField.bind('<Return>',lambda event: SSHConnect)
                UsernameField.pack(side='left')

            PasswordFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(PasswordFrame, text='Password').pack(side='left')

                PasswordField = tk.Entry(PasswordFrame)
                PasswordField.insert(0,Settings.config['Startup']['PASSWORD'])
                PasswordField.bind('<Return>',lambda event: SSHConnect)
                PasswordField.pack(side='left')

            EnterButton = tk.Button(StartFrame, text='Connect', command=SSHConnect)

            AddressFrame.pack(pady=self.PadInt)
            UsernameFrame.pack(pady=self.PadInt)
            PasswordFrame.pack(pady=self.PadInt)
            EnterButton.pack(pady=self.PadInt)
            tk.Label(StartFrame, text='Version no. ' + VersionNumber).pack(pady=self.PadInt)
            tk.Button(StartFrame, text='Settings', command=self.OpenSettingsMenu).pack()

        StartFrame.pack(padx=15, pady=15)

    def QueueInput(self, command):
        self.inputBuffer=command

    def refreshInputDevicesMidi(self):
        print('midi devices:')
        self.inputDevicesMidis = []
        self.inputDevicesMidiNames = []
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            print(info)
            if (info[2]==1):
                self.inputDevicesMidis.append(pygame.midi.Input(i))
                self.inputDevicesMidiNames.append(str(pygame.midi.get_device_info(i)[1], 'utf-8'))
            else:
                self.inputDevicesMidis.append(None)
                self. inputDevicesMidiNames.append(None)

    def refreshInputDevicesControllers(self):
        print ('controllers:')
        self.inputDevicesControllers = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        print(self.inputDevicesControllers)
        self.inputDevicesControllersLastVals = None
        #axis bindings are command, type, flip (where 'type' is 'stick' or 'trigger', deadzone is treated differently between the two)
        #hat bindings are a list of commands for the eight directions (call the direction's command with (1) when the hat moves to that direction, call the direction's command with (0) when the hat moves and hat last was that direction)


        if (len(self.inputDevicesControllers)):
            controller = pygame.joystick.Joystick(0) #TODO: selector to pick which controller is active, and then a ChangeController function
            self.inputDevicesControllers.append(controller)
            print(controller)
            self.inputDevicesControllersLastVals = { 'axis':[], 'button':[], 'hat':[] }
            for a in range(controller.get_numaxes()):
                self.inputDevicesControllersLastVals['axis'].append(0)
            for b in range(controller.get_numbuttons()):
                self.inputDevicesControllersLastVals['button'].append(False)
            for h in range(controller.get_numhats()):
                self.inputDevicesControllersLastVals['hat'].append(None)
            print(self.inputDevicesControllersLastVals)


    def loadControls(self):
        pygame.midi.init()
        self.refreshInputDevicesMidi()
        pygame.joystick.init()
        self.refreshInputDevicesControllers()


    def processInputs(self):
        self.ProcessMidi()
        self.processController()

    def processController(self):

        def processAxis(axisNumber, axisType, flip, threshold):
            value = controller.get_axis(axisNumber)
            if (threshold==1): threshold=.999
            
            if (axisType=='stick' or axisType == 'both'):
                value = max(0, abs(value)-threshold)/(1-threshold) * math.copysign(1, value) * flip
            if (axisType == 'trigger' or axisType == 'both'):
                #triggers are returned as -1 to 1, -1 is at rest- remap to 0-1
                value = max(0, ((value+1)/2-threshold)/(1-threshold)) 
            
            changedLast=self.inputDevicesControllersLastVals['axis'][a]
            changed = changedButton = value != changedLast

            if (value != 0 and changedLast != 0): changedButton=False #if we were not at rest and we still aren't, the button is still pressed
            #TODO: check if we crossed zero?

            self.inputDevicesControllersLastVals['axis'][a] = value
            return (changed,value, changedButton)
        
        def checkButton(buttonNumber):
            value = controller.get_button(buttonNumber)
            changed = value != self.inputDevicesControllersLastVals['button'][buttonNumber]
            self.inputDevicesControllersLastVals['button'][buttonNumber] = value
            return (changed, value)


        if (len(self.inputDevicesControllers)):
            controller=self.inputDevicesControllers[0]

            for a in range(len(self.inputDevicesControllersLastVals['axis'])):
                binding=self.commandBinds['controller']['axis'][a]
                if (self.SettingsMenu):
                    last=self.inputDevicesControllersLastVals['axis'][a]
                    value = controller.get_axis(a)
                    self.inputDevicesControllersLastVals['axis'][a]=value
                    
                    if (inputRouting.settingsListenForInput):
                        stickThreshold = .5
                        triggerThreshold = -.8

                        if (value > triggerThreshold and not (-stickThreshold<value<stickThreshold)):
                            if (last < triggerThreshold): axisType='trigger'
                            else: axisType='stick'
                            inputRouting.bindCommand('controller', 'axis', 'analog', (a, axisType, 1, bindables.thresholdDefaultController))
                elif (binding):
                    changed, value, changedButton = processAxis(a, binding.type, binding.flip, binding.threshold)

                    #TODO: merge processAxis back into this bit? (now that it's not being used anywhere else, might be able to simplify it back down a bit)

                    if (changed):
                        if (binding.command[1] == 'button'):
                            if (changedButton): #extra check for button commands, since an axis will otherwise repeatedly send non-0 values
                                binding.callCommand(value!=0)
                        else: binding.callCommand(value)

            for b in range(len(self.inputDevicesControllersLastVals['button'])):
                if (self.SettingsMenu):
                    changed, value = checkButton(b)
                    if (changed and value and inputRouting.settingsListenForInput):
                         inputRouting.bindCommand('controller', 'button', 'button', [b])
                elif (self.commandBinds['controller']['button'][b]):
                    changed, value = checkButton(b)
                    if (changed):
                        self.commandBinds['controller']['button'][b].callCommand(value)

            for h in range(len(self.inputDevicesControllersLastVals['hat'])):
                hat = controller.get_hat(h)
                #TODO: there's probably a better way to convert axes into a direction index
                if hat == (0,0): hat = None
                elif hat==(0,1): hat= 0
                elif hat==(1,1): hat= 1
                elif hat==(1,0): hat= 2
                elif hat==(1,-1): hat= 3
                elif hat==(0,-1): hat= 4
                elif hat==(-1,-1): hat= 5
                elif hat==(-1,0): hat= 6
                elif hat==(-1,1): hat= 7
                lastVal = self.inputDevicesControllersLastVals['hat'][h]
                if (hat != lastVal):
                    if (self.SettingsMenu):
                        if (inputRouting.settingsListenForInput):
                            if (hat is not None):
                                #this nonsense is so diagonals are possible to bind in the interface (since otherwise both directions would need to be pressed in the same frame)
                                if (self.hatBoundVal[h] is None): self.hatBoundVal[h] = hat
                                elif (hat%2==1): self.hatBoundVal[h] = hat
                            else:
                                inputRouting.bindCommand('controller', 'hat', 'button', (h, self.hatBoundVal[h]))
                                self.hatBoundVal[h] = None
                    else:
                        #TODO: some filtering here similar to the above, but with a time delay instead of triggering on release, so diagonals can be hit and released without also triggering one of the cardinals it contains
                        if (lastVal is not None and self.commandBinds['controller']['hat'][h][lastVal]):self.commandBinds['controller']['hat'][h][lastVal].callCommand(False)
                        if (hat is not None and self.commandBinds['controller']['hat'][h][hat]): self.commandBinds['controller']['hat'][h][hat].callCommand(True)
                    self.inputDevicesControllersLastVals['hat'][h] = hat


    def ProcessMidi(self):

        def checkInputValidity(bind):
            return ((not bind.midiDevice or bind.midiDevice ==self.inputDevicesMidiNames[deviceIndex])
                    and (not bind.midiChannel or bind.midiChannel == channel))

        eventNoteOn = 0x90
        eventNoteOff = 0x80
        eventControlChange = 0xb0
        deviceIndex = 0

        #TODO: implement RPN and NRPN checks
        #NOTE: a ControlChange with control 6 is for RPN or NRPN messages, if it's immediately preceded by two ControlChanges with 101 and 100 (RPN) or 99 and 98 (NRPN)
        #in that case, the control value of the two preceding control changes are the MSB and LSB of the command index, and the data of the control 6 command is the value of that message.
        #I think it's supposed to also be able to use the second data byte in control 6 as an LSB for the value, but I'm unable to test that with this keyboard.
        for device in self.inputDevicesMidis:
            if (device and device.poll()):
                for event in device.read(1024):
                    event = event[0] #strip the timing component, we don't need it
                    channel = event[0] & 0b00001111 #just the 0x1s place
                    command = event[0] & 0b11110000 #just the 0x10s place
                    if (command == eventNoteOn or command == eventNoteOff):
                        key = event[1]
                        if (self.SettingsMenu):
                            if (inputRouting.settingsListenForInput and command==eventNoteOn):
                                inputRouting.bindCommand('midi', 'note', 'button', (self.inputDevicesMidiNames[deviceIndex], channel, key))
                        else:
                            state = command == eventNoteOn #1 for noteOn, 0 for noteOff
                            for bind in self.commandBinds['midi']['note']:
                                if (checkInputValidity(bind) and bind.inputNumber == key):
                                    bind.callCommand(state)

                    elif (command== eventControlChange):
                        control = event[1]
                        if (self.SettingsMenu):
                            if (inputRouting.settingsListenForInput != None):
                                inputRouting.bindCommand('midi', 'control', 'analog',(self.inputDevicesMidiNames[deviceIndex], channel, control, bindables.thresholdDefaultMidiCC))
                        else:
                            value = event[2]/127 #map to 0-1
                            for bind in self.commandBinds['midi']['control']:
                                if (checkInputValidity(bind) and bind.inputNumber == control):
                                    valueProcessed=max(0,(value-bind.threshold)/(1-bind.threshold))
                                    if (deviceIndex not in bind.valueLast):
                                        bind.valueLast[deviceIndex]={channel:valueProcessed}
                                    elif (channel not in bind.valueLast[deviceIndex]):
                                        bind.valueLast[deviceIndex][channel]=0
                                    valueLast=bind.valueLast[deviceIndex][channel]
                                    
                                    if (bind.command[1]=='button'):
                                        if ((valueLast==0)!=(valueProcessed==0)): bind.callCommand(valueProcessed)
                                    else:
                                        if (not(valueLast==0 and valueProcessed==0)): bind.callCommand(valueProcessed)
                                    bind.valueLast[deviceIndex][channel]=valueProcessed
            deviceIndex += 1


    def main(self):
        self.window.update_idletasks()
        self.window.update()
        if (self.SettingsMenu):
            self.SettingsMenu.update_idletasks()
            self.SettingsMenu.update()
            self.processInputs()

        deltaTime.update()

        if (self.init):
            if (not self.SettingsMenu): self.processInputs()
            self.inputBufferTimer += deltaTime.delta
            if (self.inputBufferTimer >= self.inputBufferTime):
                if (self.inputBuffer and self.CanMove()):
                    self.inputBuffer()
                    self.inputBuffer = None
                    self.inputBufferTimer = 0

            if (self.OptionsMenuOpen):
                self.ConfigUpdateTimer -= deltaTime.delta
                if (self.ConfigUpdateTimer <= 0):
                    self.ConfigUpdateTimer = self.ConfigUpdateInterval
                    self.GetCameraConfig(camera.selectedNum)

            if (self.shell.recv_ready()):
                out=self.shell.recv(9999).decode('ascii')
                debug.print('vvvv')
                Responses = out.splitlines()

                StartPhraseCamera = ' Camera '
                StartPhrasePan = 'Position Pan: '
                StartPhraseTilt = 'Position Tilt: '
                StartPhraseZoom = 'Position Zoom: '
                StartPhraseFocus = 'Position Focus: '
                StartPhraseBrightnessLevel = 'Brightness Level: '
                StartPhraseWhitebalanceLevel = 'Whitebalance Level: '
                StartPhraseGammaLevel = 'Gamma Level: '
                StartPhraseFocusMode = 'Focus Mode: '
                StartPhraseBrightnessMode = 'Brightness Mode: '
                StartPhraseWhitebalanceMode = 'Whitebalance Mode: '
                StartPhraseGammaMode = 'Gamma Mode: '
                StartPhrasePresetResult = 'PresetListResult Preset '
                StartPhrasePresetStoreResult = 'PresetStoreResult'

                StartPhraseCamera = 'Camera '

                for ResponseLine in Responses:
                    print('>>' + ResponseLine)
                    #TODO: turn all these calls into a more general function
                    #TODO: get the camera number referred to in ResponseLine (if applicable), check if it's the current camera
                    #TODO: handling for bad inputs (EG newline missing)
                    if (ResponseLine.startswith('*')):
                        if (StartPhraseCamera in ResponseLine):
                            sIndex=ResponseLine.rfind(StartPhraseCamera) + len(StartPhraseCamera)
                            cameraNumber = int(ResponseLine[sIndex])
                        if (StartPhrasePan in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhrasePan) + len(StartPhrasePan)
                            value = int(ResponseLine[sIndex:])
                            self.cameras[cameraNumber].position[0]=value
                            self.LabelPan.config(text = 'Pan: ' + str(value))
                            self.PanningDone()

                        elif (StartPhraseTilt in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseTilt) + len(StartPhraseTilt)
                            value = int(ResponseLine[sIndex:])
                            self.cameras[cameraNumber].position[1]=value
                            self.LabelTilt.config(text = 'Tilt: ' + str(value))
                            self.TiltingDone()
                    
                        elif (StartPhraseZoom in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseZoom) + len(StartPhraseZoom)
                            value = int(ResponseLine[sIndex:])
                            self.cameras[cameraNumber].position[2]=value
                            self.LabelZoom.config(text = 'Zoom: ' + str(value))
                            self.ZoomingDone()
                    
                        elif (StartPhraseFocus in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseFocus) + len(StartPhraseFocus)
                            value = int(ResponseLine[sIndex:])
                            self.cameras[cameraNumber].position[3]=value
                            self.LabelFocus.config(text = 'Focus: ' + str(value))
                            self.FocusingDone()
                    
                        elif (StartPhraseBrightnessLevel in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseBrightnessLevel) + len(StartPhraseBrightnessLevel)
                            self.cameras[cameraNumber].brightnessValue.set(int(ResponseLine[sIndex:]))
                    
                        elif (StartPhraseWhitebalanceLevel in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseWhitebalanceLevel) + len(StartPhraseWhitebalanceLevel)
                            self.cameras[cameraNumber].whitebalanceValue.set(int(ResponseLine[sIndex:]))
                            
                        elif (StartPhraseGammaLevel in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseGammaLevel) + len(StartPhraseGammaLevel)
                            self.cameras[cameraNumber].gammaValue.set(int(ResponseLine[sIndex:]))

                        elif (StartPhraseFocusMode in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseFocusMode) + len(StartPhraseFocusMode)
                            self.cameras[cameraNumber].focusManual.set(ResponseLine[sIndex:]=='Auto')

                        elif (StartPhraseBrightnessMode in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseBrightnessMode) + len(StartPhraseBrightnessMode)
                            self.cameras[cameraNumber].brightnessManual.set(ResponseLine[sIndex:]=='Auto')

                        elif (StartPhraseWhitebalanceMode in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseWhitebalanceMode) + len(StartPhraseWhitebalanceMode)
                            self.cameras[cameraNumber].whitebalanceManual.set(ResponseLine[sIndex:]=='Auto')
                    
                        elif (StartPhraseGammaMode in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhraseGammaMode) + len(StartPhraseGammaMode)
                            self.cameras[cameraNumber].gammaManual.set(ResponseLine[sIndex:]=='Auto')

                        elif (StartPhrasePresetStoreResult in ResponseLine):
                            sIndex = ResponseLine.rfind(StartPhrasePresetStoreResult) + len(StartPhrasePresetStoreResult)
                            self.ListPresetsCamera()

                        elif (StartPhrasePresetResult in ResponseLine):
                            SplitString = ResponseLine.split()
                            i=0
                            while i < len(SplitString):
                                if (SplitString[i] == 'PresetListResult' and SplitString[i+1] == 'Preset'):
                                    PresetIndex = int(SplitString[i+2])
                                    if (self.CameraPresets[PresetIndex] == None):
                                        self.CameraPresets[PresetIndex] = CameraPreset(PresetIndex)
                                        debug.print('added preset at index ' + str(PresetIndex))
                                    i+=2
                                elif (SplitString[i] == 'Name:'):
                                    nameString = SplitString[i+1]
                                    i+=2
                                    while i < len(SplitString): #keep adding to name until the end of the line
                                        nameString += ' ' + SplitString[i]
                                        i+= 1
                                    self.CameraPresets[PresetIndex].name = nameString[1:len(nameString)-1] #trim quotes
                                    debug.print('added name "' + self.CameraPresets[PresetIndex].name + '" at index ' + str(PresetIndex))
                                    i+=1
                                elif (SplitString[i] == 'CameraId:'):
                                    self.CameraPresets[PresetIndex].cameraId = int(SplitString[i+1])
                                    debug.print('added cameraId ' + str(self.CameraPresets[PresetIndex].cameraId) + ' at index ' + str(PresetIndex))
                                    i+=1
                                elif (SplitString[i] == 'PresetId:'):
                                    self.CameraPresets[PresetIndex].presetId = int(SplitString[i+1])
                                    debug.print('added Id ' + str(self.CameraPresets[PresetIndex].presetId) + ' at index ' + str(PresetIndex))
                                    i+=1
                                i+=1
                            if (self.CameraPresets[PresetIndex].isValid()):
                                debug.print('Found Preset: ' + self.CameraPresets[PresetIndex].name)
                                self.UpdatePresetButton(PresetIndex)


                        elif (StartPhraseCamera in ResponseLine): #!!!!!!!!!!!!! Make sure this elif is always the last in line !!!!!!!!!!!!
                            #(it'll catch any remaining command that includes the word 'camera')
                            sIndex = ResponseLine.rfind(StartPhraseCamera)
                            if (sIndex > -1):
                                NextPhrase = ' Connected: '
                                nIndex = ResponseLine.rfind(NextPhrase)
                                if (nIndex == sIndex + len(StartPhraseCamera)+1):
                                    sIndex += len(StartPhraseCamera)
                                    camNumber = int(ResponseLine[sIndex])
                                    nIndex += len(NextPhrase)
                                    boolConnected = ResponseLine[nIndex:] == 'True'
                                    if (debug.forceCameraConnection and (2 <= camNumber <= 3)): boolConnected = True #debug: force UI to think cameras 2 and 3 are always connected
                                    self.CameraAvailable(camNumber, boolConnected)
                                    if (camera.selected is None):
                                        self.cameras[camNumber].select()
                                    debug.print('Camera ' + str(camNumber) + ' Status: ' + str(boolConnected))
            
                debug.print('^^^^')
        
        self.updateDirectValues()

class CameraPreset():
    def __init__(self, listPosition=None, camera = None, name = None, presetId=None, widget=None):
        self.cameraId = camera
        self.name = name
        self.presetId = presetId
        self.widget = None
        self.listPosition=listPosition
    def isValid(self):
        return(self.cameraId and self.presetId)

class CameraPresetPanel(tk.Frame):
    def __init__(self, parent, index, *args, **options):
        tk.Frame.__init__(self, parent, relief='ridge', borderwidth=2, *args, **options)
        self.index = index

        self.presetEntry=CameraController.current.CameraPresets[index]

        self.frameName = tk.Frame(self)
        
        self.presetIdLabel = tk.Label(self.frameName)

        validation=self.register(self.renamePreset)
        self.presetNameLabel = tk.Label(self.frameName, text=CameraController.current.CameraPresets[self.index].name)

        self.presetNameEntry = tk.Entry(self.frameName, validate='key', validatecommand=(validation, '%S'))
        self.presetNameEntry.insert(0,CameraController.current.CameraPresets[self.index].name)
        self.presetNameEntry.bind('<Return>', lambda event: self.focus())
        self.presetNameEntry.bind('<FocusOut>', self.renamePreset)

        self.presetIdLabel.pack(side='left')
        #self.presetNameLabel.pack(side='left')

        self.frameMain = tk.Frame(self)
        self.cameraId = tk.Label(self.frameMain)
        self.activateButton = tk.Button(self.frameMain, text='activate', command=self.activatePreset)

        self.cameraId.pack(side='left')
        self.activateButton.pack(side='left')

        self.frameButtons = tk.Frame(self)

        tk.Button(self.frameButtons, text='overwrite', command=self.saveToPreset).pack(side='left')
        tk.Button(self.frameButtons, text='delete', command=self.deletePreset).pack(side='left')
        tk.Button(self.frameButtons, text='v', command=lambda: self.rearrangePreset(1)).pack(side='right')
        tk.Button(self.frameButtons, text='^', command=lambda: self.rearrangePreset(-1)).pack(side='right')
        
        self.frameName.pack(fill='x')
        self.frameMain.pack(fill='x')
        self.updateContents()
        self.SetEditState(CameraController.current.TogglePresetEdit.state)
        self.filter()
    def updateContents(self):
        self.presetNameEntry.delete(0,'end')
        self.presetNameEntry.insert(0, self.presetEntry.name)
        self.presetNameLabel.config(text=self.presetEntry.name)
        self.presetIdLabel.config(text=self.presetEntry.presetId)
        self.cameraId.config(text='Camera ' + str(self.presetEntry.cameraId))
        #CameraController.current.CameraPresets[self.index]
        self.grid(column=0, row=self.index, sticky='nsew')
    def saveToPreset(self):
        CameraController.current.shell.send('xCommand Camera Preset Store '
                    + 'PresetId: ' + str(self.presetEntry.presetId)
                    + ' CameraId: '+ str(self.presetEntry.cameraId)
                    + ' ListPosition: ' + str(self.index)
                    + ' Name: ' + self.presetNameEntry.get() + '\r')
    def validatePresetName(self, newValue):
        if (newValue.contains(' ')): return False
        return True
    def renamePreset(self, event):
        presetName=self.presetNameEntry.get()
        if (presetName):
            CameraController.current.shell.send('xCommand Camera Preset Edit PresetId: ' + str(self.presetEntry.presetId)
                        + ' Name: ' + presetName + '\n')
            self.presetNameLabel.config(text=presetName)
    def deletePreset(self):
        CameraController.current.shell.send('xCommand Camera Preset Remove PresetId: ' + str(self.presetEntry.presetId) +'\n')
        CameraController.current.CameraPresets[self.index] = None
        self.destroy()
    def rearrangePreset(self, shift):
        self.index=min(36,max(0, self.index+shift))
        CameraController.current.shell.send('xCommand Camera Preset Edit PresetID: ' + str(self.presetEntry.presetId)+ ' ListPosition: '+ str(self.index) +'\n')
        CameraController.current.InitializePresetLists()
        #TODO: rearrange list internally, instead of rebuilding the whole list on every change


    def activatePreset(self):
        CameraController.current.shell.send('xCommand Camera Preset Activate PresetID: ' + str(self.presetEntry.presetId)+'\n')


    def SetEditState(self, unlock):
        if (unlock):
            self.frameButtons.pack(fill='x')
            self.presetNameLabel.forget()
            self.presetNameEntry.pack(side='left')
        else:
            self.frameButtons.forget()
            self.presetNameEntry.forget()
            self.presetNameLabel.pack(side='left')
    def filter(self):
        if (CameraController.current.PresetsFiltered and camera.selectedNum != CameraController.current.CameraPresets[self.index].cameraId): self.grid_forget()
        else: self.grid(column = 0, row=self.index, sticky='nsew')



class inputRouting(): #move outside of parent class
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


class ToggleButton(tk.Button):

    def __init__(self, parent, textOn='on', textOff='off', toggleCommand=None, *args, **options):
        tk.Button.__init__(self, parent, *args, **options)

        self.state=True
        self.TextOn=textOn
        self.TextOff = textOff
        self.config(command=self.ToggleState)
        
        self.ToggleCommand = toggleCommand
        self.SetState(False, ignoreCommand=True)
    def SetState(self, newState, ignoreCommand = False):
        if (newState != self.state):
            self.state = newState
            if (newState == False): self.config(text=self.TextOff)
            else: self.config(text=self.TextOn)
            if (self.ToggleCommand and not ignoreCommand): self.ToggleCommand(newState)

    def ToggleState(self):
        self.SetState(not self.state)
class ToggleButtonChecked(tk.Frame):

    def __init__(self, parent, textOff=['off','on'], textOn=['off','on'], toggleCommand=None, *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)
        self.config(relief='sunken', borderwidth=2)

        self.state=True

        self.textOff = textOff
        self.textOn = textOn

        self.buttonOff=tk.Button(self, text=textOff, borderwidth=1, command=self.ToggleState)
        self.buttonOn=tk.Button(self, text=textOn, borderwidth=1, command=self.ToggleState)
        
        self.buttonOff.pack(side='left')
        self.buttonOn.pack(side='left')
        
        self.ToggleCommand = toggleCommand
        self.SetState(False, ignoreCommand=True)
    def SetState(self, newState, ignoreCommand = False):
        if (newState != self.state):
            self.state = newState
            if (newState == False):
                self.buttonOff.config(relief='sunken', state='disabled', text=self.textOff[0])
                self.buttonOn.config(relief='raised', state='normal', text=self.textOff[1])
            else:
                self.buttonOff.config(relief='raised', state='normal', text=self.textOn[0])
                self.buttonOn.config(relief='sunken', state='disabled', text=self.textOn[1])
            if (self.ToggleCommand and not ignoreCommand): self.ToggleCommand(newState)

    def ToggleState(self):
        self.SetState(not self.state)


class ToggleFrame(tk.Frame):
    def __init__(self, parent, title='frame', keepTitle=False, buttonShowTitle='Show Frame', buttonHideTitle='Hide Frame', togglePin='right', toggleCommand = None, contentPadx=3, *args, **options):
        #togglePin should be either 'left' or 'right'
        tk.Frame.__init__(self, parent, *args, **options)

        self.open = tk.IntVar()
        self.open.set(0)

        self.ButtonShowText = buttonShowTitle
        self.ButtonHideText = buttonHideTitle
        self.KeepTitle=keepTitle

        self.Titlebar = tk.Frame(self)
        self.Titlebar.pack(fill='x', ipady=2, ipadx=2, padx=3, pady=3)
        self.TogglePin=togglePin

        self.expandButton = tk.Button(self.Titlebar, text=self.ButtonShowText, command=self.toggle)
        self.expandButton.pack(side=self.TogglePin)

        self.contentFrame = tk.Frame(self) 
        self.contentPadx=contentPadx

        self.title = tk.Label(self.Titlebar, text=title)
        if (self.KeepTitle): self.title.pack(side='left')

        self.ToggleCommand = toggleCommand

    def toggle(self):
        if (bool(self.open.get())): #the menu is open and we're closing it
            self.contentFrame.forget()
            if (not self.KeepTitle): self.title.forget()
            self.expandButton.configure(text=self.ButtonShowText)
            self.open.set(0)
            if (self.ToggleCommand): self.ToggleCommand(False)
        else: #the menu is closed and we're opening it
            self.contentFrame.pack(ipady=2, ipadx=2, padx=self.contentPadx, pady=3, fill='both')
            if (not self.KeepTitle): self.title.pack(side='left')
            self.expandButton.configure(text=self.ButtonHideText)
            self.open.set(1)
            if (self.ToggleCommand): self.ToggleCommand(True)
class ScrollFrame(tk.Frame):
    def __init__(self, parent, cHeight=200, frameConfigureCommand=None, *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)
        self.config(relief='groove', borderwidth = 2)

        self.bind('<Enter>', self.bindMouseWheel)
        self.bind('<Leave>', self.unbindMouseWheel)

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, width=0, height=cHeight)
        self.scrollbar = tk.Scrollbar(self, orient='vertical', command = self.canvas.yview)
        self.contents=tk.Frame(self.canvas, relief='groove', borderwidth = 2)

        self.canvas.config(yscrollcommand = self.scrollbar.set)
        # TODO: figure out how to read borderwidth and highlightthickness, then use (borderwidth+highlightthickness, borderwidth+highlightthickness) instead of (0,0)
        self.canvasFrame = self.canvas.create_window((0,0), window=self.contents, anchor='nw')

        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.contents.bind('<Configure>', self.onFrameConfigure)
        self.canvas.bind('<Configure>', self.onCanvasConfigure)
        self.frameConfigureCommand = frameConfigureCommand
        
    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion = self.canvas.bbox('all'))
        if (self.frameConfigureCommand): self.frameConfigureCommand(self)

    def onCanvasConfigure(self, event):
        #TODO: see above about borderwidth and highlightthickness
        width=event.width #-borderwidth*2 - highlightthickness*2
        self.canvas.itemconfig(self.canvasFrame,  width=width)
        #self.contents.columnconfigure(0,minsize=width-4) #what's this extra 4? grid padding, maybe?
    def bindMouseWheel(self, event):
        #TODO: for X11 systems, may need to use <Button-4> and <Button-5> instead
        self.canvas.bind_all('<MouseWheel>', self.onMouseWheel)
    def unbindMouseWheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')
    def onMouseWheel(self,event):
        #TODO: mac systems might not need the 120 divider
        self.canvas.yview_scroll(int(-1*(event.delta/120)),'units')

class bindingFrame(tk.Frame):
    #class to hold an individual keybind within a control
    labelUnassignedDevice = 'select device'
    labelUnassignedSubdevice = 'select input type'

    class parsedEntry(tk.Entry):
        #subclass of entry to display, adjust, and error check binding inputs
        def __init__(self, parent, rules, initialValue, range=None, **args):
            tk.Entry.__init__(self, parent, **args)
            self.bind('<FocusOut>', self.errorCheckEvent)
            self.bind('<FocusIn>', self.selectAll)
            self.rules=rules
            if (initialValue is not None): self.insert(0,initialValue)
            self.range=range

            self.errorCheck()

        def selectAll(self, event):
            self.selection_range(0,'end')

        def errorCheckEvent(self, event):
            self.errorCheck()
        def errorCheck(self):
            value=self.get()

            if (self.rules=='int'): value = self.rulesInt(value)
            elif (self.rules=='midi'): value = self.rulesMidi(value)
            elif (self.rules=='midiString'): value = self.rulesMidiString(value)

            self.delete(0,'end')
            self.insert(0, value)
            return self.get()
        def rulesMidi(self, input):
            #convert string into a valid midi device or channel (int or 'any')
            if (input != 'any'):
                input = self._rulesInt(input)
                if input == None: input = 'any'
            return input
        def rulesMidiString(self, input):
            if (input != 'any'):
                input = self._rulesString(input)
                if input == None: input = 'any'
            return input
        def rulesInt(self, input):
            #convert string into an int (or 0, if it's not a valid int)
            input = self._rulesInt(input)
            if (input == None): return 0

            if (self.range):
                input = max(self.range[0], min(self.range[1], input))

            return input
        def _rulesInt(self, input):
            #helper function to parse a string as int or None
            try: return int(input)
            except: return None 
        def _rulesString(self, input):
            if (input == ''): return None
            return input

    def __init__(self, parent, command, deviceType=None, deviceSubtype=None, contents=None, **options):
        tk.Frame.__init__(self, parent, **options)
        self.titlebar = tk.Frame(self)
        self.deviceType=tk.StringVar(self)
        self.deviceType.set(bindingFrame.labelUnassignedDevice)
        self.deviceSubtype = tk.StringVar(self)
        self.deviceSubtype.set(bindingFrame.labelUnassignedSubdevice)
        self.deviceTypeLast = None
        self.deviceSubtypeLast = None
        #(button, analog) each is true or false
        self.commandType=(command[1]=='button' or command[1]=='both', command[1]=='analog' or command[1]=='both')
        

        self.contents=None
        if True:
            self.listenButton = tk.Button(self.titlebar, text='listen for input', command=lambda:inputRouting.bindListen(self, ))
            self.listenButton.pack(side='left')
            self.deviceTypeLabel = tk.OptionMenu(self.titlebar, self.deviceType, bindingFrame.labelUnassignedDevice, 'controller', 'midi', command=self.changeDeviceType)
            self.deviceTypeLabel.pack(side='left', padx=(5,3))
            self.deviceSubtypeLabel = tk.OptionMenu(self.titlebar, self.deviceSubtype, bindingFrame.labelUnassignedSubdevice, command=self.changeDeviceSubtype)
            #self.deviceSubtypeLabel.pack(side='left', padx=(10,3))
            tk.Button(self.titlebar, text='X', command=self.destroy).pack(side='right')
        self.body=tk.Frame(self)
        self.titlebar.pack(fill='x', padx=2, pady=2)
        self.body.pack(fill='x', padx=2, pady=2)
        self.setDevice(deviceType, deviceSubtype, contents)

    def changeDeviceType(self, deviceType):
        if (self.deviceTypeLast != deviceType):
            self.setDevice(deviceType, None)
    def changeDeviceSubtype(self, deviceSubtype):
        if (self.deviceSubtypeLast != deviceSubtype):
            self.setDevice(self.deviceType.get(), deviceSubtype)
    def setDevice(self, deviceType, deviceSubtype, contents=None):
        if (self.deviceTypeLast != deviceType or self.deviceSubtypeLast != deviceSubtype):
            if (deviceType == None or deviceType == bindingFrame.labelUnassignedDevice):
                self.deviceType.set(bindingFrame.labelUnassignedDevice)
                self.deviceSubtypeLabel.forget()
            else:
                self.deviceType.set(deviceType)
                self.deviceSubtypeLabel.pack(side='left', padx=(10,3)) #TODO: test if this breaks the layout on assigning and then unassigning a bind
                if (deviceSubtype == None or deviceSubtype== bindingFrame.labelUnassignedSubdevice): self.deviceSubtype.set(bindingFrame.labelUnassignedSubdevice)
                else: self.deviceSubtype.set(deviceSubtype)

            self.deviceTypelast=self.deviceType.get()
            self.deviceSubtypeLast=self.deviceSubtype.get()
            self.contents=[]

            for child in self.body.winfo_children():
                child.destroy()

            #populate the subtype menu
            if (deviceType == 'midi'):
                #TODO: make this bit a general function
                #TODO: allow CC input into button commands, but not note input into analog commands
                self.deviceSubtypeLabel['menu'].delete(0,'end')
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(label='note', command=lambda: self.changeDeviceSubtype('note'))
                self.deviceSubtypeLabel['menu'].add_command(label='control', command=lambda: self.changeDeviceSubtype('control'))
            elif (deviceType=='controller'):
                self.deviceSubtypeLabel['menu'].delete(0,'end')
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(label='button', command=lambda: self.changeDeviceSubtype('button'))
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(label='hat', command=lambda: self.changeDeviceSubtype('hat'))
                self.deviceSubtypeLabel['menu'].add_command(label='axis', command=lambda: self.changeDeviceSubtype('axis'))

            #populate the inputs
            if (deviceSubtype != None and deviceSubtype != self.labelUnassignedSubdevice):
                if (deviceType == 'midi'):
                    #midi contents: midi device (int or None), midi channel (int or None), control number (int), threshold
                    #TODO: figure out if we can get tooltips going (or just add a descriptor text like 'leave blank for any'

                    if (contents==None): contents=(None,None,None)
                    self.contents=[None, None, None, None]


                    tk.Label(self.body, text='device: ').pack(side='left', padx=2, pady=2)
                    self.contents[0]= bindingFrame.parsedEntry(self.body, 'midiString',contents[0], width=40)
                    self.contents[0].pack(side='left', padx=2, pady=2)

                    tk.Label(self.body, text='channel: ').pack(side='left', padx=2, pady=2)
                    self.contents[1]= bindingFrame.parsedEntry(self.body, 'midi',contents[1], width=3)
                    self.contents[1].pack(side='left', padx=2, pady=2)

                    tk.Label(self.body, text='index: ').pack(side='left', padx=2, pady=2)
                    self.contents[2]= bindingFrame.parsedEntry(self.body, 'int',contents[2], width=3)
                    self.contents[2].pack(side='left', padx=2, pady=2)

                    if (deviceSubtype == 'control'):
                        self.contents[3] = tk.DoubleVar(self.body)
                        if (len(contents)==4 and contents[3]): self.contents[3].set(contents[3])
                        else: self.contents[3].set(bindables.thresholdDefaultMidiCC)
                        tk.Label(self.body, text='threshold').pack(side='left', padx=2, pady=2)
                        tk.Scale(self.body, variable=self.contents[3], from_=0, to_=1, digits=3, resolution=0.01, orient='horizontal' ).pack(side='left', padx=2, pady=2)


                elif (deviceType == 'controller'): 
                    if (deviceSubtype == 'axis'):
                        #axisNumber, axisType, axisFlip, threshold
                        if (contents == None): contents = [None, None, None, None]
                        self.contents = [None, None, None, None]
                        tk.Label(self.body, text='axis: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= bindingFrame.parsedEntry(self.body, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)
                        
                        tk.Label(self.body, text='type: ').pack(side='left', padx=2, pady=2)
                        self.contents[1]= tk.StringVar(self.body)
                        if (contents[1]): self.contents[1].set(contents[1])
                        else: self.contents[1].set('stick')
                        tk.OptionMenu(self.body, self.contents[1],'stick','trigger').pack(side='left', padx=2, pady=2)
                        
                        self.contents[2] = tk.IntVar(self.body)
                        if (contents[2]): self.contents[2].set(contents[2])
                        else: self.contents[2].set(1)
                        tk.Checkbutton(self.body, variable=self.contents[2], text='invert', onvalue=-1, offvalue=1).pack(side='left', padx=2, pady=2)

                        self.contents[3] = tk.DoubleVar(self.body)
                        if (contents[3] is not None): self.contents[3].set(contents[3])
                        else: self.contents[3].set(bindables.thresholdDefaultController)
                        tk.Label(self.body, text='threshold').pack(side='left', padx=2, pady=2)
                        tk.Scale(self.body, variable=self.contents[3], from_=0.01, to_=1, digits=3, resolution=0.01, orient='horizontal').pack(side='left', padx=2, pady=2)

                    elif (deviceSubtype == 'button'):
                        #buttonNumber
                        if (contents == None): contents = [None]
                        self.contents=[None]
                        
                        tk.Label(self.body, text='button: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= bindingFrame.parsedEntry(self.body, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)

                    elif (deviceSubtype == 'hat'):
                        #hatNumber, hatDirection
                        if (contents == None): contents = [None, None]
                        self.contents=[None, None]

                        tk.Label(self.body, text='hat number: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= bindingFrame.parsedEntry(self.body, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)
                        
                        tk.Label(self.body, text='hat direction (clockwise, 0 is up): ').pack(side='left', padx=2, pady=2)
                        self.contents[1]= bindingFrame.parsedEntry(self.body, 'int',contents[1], range=(0,7), width=3)
                        self.contents[1].pack(side='left', padx=2, pady=2)
                elif (deviceType == 'keyboard'):
                    None
    def getSubtypeString(self):
        return self.deviceType + '_' + self.deviceSubtype
    def makeOutput(self, commandAddress):
        if (self.contents and self.deviceSubtype.get() != bindingFrame.labelUnassignedSubdevice):
            if(self.deviceType.get() == 'midi'):
                midiDevice, midiChannel, inputNumber, threshold = self.contents

                outstring= commandAddress + ',midi.'+ self.deviceSubtype.get() +','+midiDevice.errorCheck() + ',' + midiChannel.errorCheck()+','+inputNumber.errorCheck()
                if (threshold is not None and threshold.get() != bindables.thresholdDefaultMidiCC): outstring += ','+str(threshold.get())
                return outstring
        
            elif(self.deviceType.get() == 'controller'):
                if (self.deviceSubtype.get() == 'axis'):
                    axisNum, axisType, axisFlip, threshold = self.contents
                    outstring= commandAddress + ',controller.axis,'+axisNum.errorCheck()+','+axisType.get() + ','+str(axisFlip.get())
                    if (threshold.get() != bindables.thresholdDefaultController): outstring += ','+str(threshold.get())
                    return outstring
                elif (self.deviceSubtype.get() == 'button'):
                    buttonNum=self.contents[0]
                    return commandAddress+',controller.button,'+buttonNum.errorCheck()
                elif (self.deviceSubtype.get() == 'hat'):
                    hatNum, hatDirection = self.contents
                    return commandAddress+',controller.hat,'+hatNum.errorCheck()+','+hatDirection.errorCheck()
        return None
        
class ControlBindPanel(ToggleFrame):
    #class to hold several keybinds that all point to the same command
    def __init__(self, parent, bindableName, command, **options):
        title=bindableName.replace('_', ' ')
        ToggleFrame.__init__(self, parent, title=title, keepTitle=True, buttonShowTitle = 'show', buttonHideTitle='hide', togglePin='left', relief='groove', borderwidth=1)
        self.bindableName = bindableName
        self.command = command
        #self.config(highlightbackground='black', highlightthickness=1)

        frameBody = tk.Frame(self.contentFrame)
        if True:
            frameSidebar=tk.Frame(frameBody)
            self.BindingList = tk.Frame(frameBody, relief='sunken', borderwidth=2)
            tk.Button(frameSidebar, text='add', command=self.AddBinding).pack(padx=2,pady=3)
            frameSidebar.pack(side='left', fill='y', padx=2, pady=2)
            self.BindingList.pack(side='left', fill='x', expand=True)

        frameBody.pack(padx=3,pady=3, fill='both', expand=True)

        def compareCommand():
            if (not binding):
                return False
            command=binding.command
            if (self.bindableName.startswith(bindables.bindingPresetsPrefix)):
                command=self.bindableName[len(bindables.bindingPresetsPrefix):]
                if (binding.bindablePreset==command):
                    return True
            elif (command==bindables.index[self.bindableName]): return True
            return False
        
        if (command[1]=='button' or command[1]=='both'): #digital inputs can only be bound to button commands, or commands that handle their own input
            for binding in CameraController.current.commandBinds['midi']['note']:
                if (compareCommand()):
                    self.AddBinding(deviceType='midi', deviceSubtype='note', contents=(binding.midiDevice,binding.midiChannel,binding.inputNumber))
            b=0
            for binding in CameraController.current.commandBinds['controller']['button']:
                if (compareCommand()):
                    self.AddBinding(deviceType='controller', deviceSubtype='button', contents=[b])
                b+=1
            h = 0
            for hat in CameraController.current.commandBinds['controller']['hat']:
                direction=0
                for binding in hat:
                    if (compareCommand()):
                        self.AddBinding(deviceType='controller', deviceSubtype='hat', contents=[h, direction])
                    direction+=1
                h+=1

        #analog inputs can always be bound to button commands, as long as the threshold is properly set
        for binding in CameraController.current.commandBinds['midi']['control']:
            if (compareCommand()):
                self.AddBinding(deviceType='midi', deviceSubtype='control', contents=(binding.midiDevice,binding.midiChannel,binding.inputNumber, binding.threshold))
        a=0
        for binding in CameraController.current.commandBinds['controller']['axis']:
            if (compareCommand()):
                self.AddBinding(deviceType='controller', deviceSubtype='axis', contents=[a, binding.type, binding.flip, binding.threshold])
            a+=1

    def AddBinding(self, deviceType=None, deviceSubtype=None, contents=None):
        bindingFrame(self.BindingList, self.command, relief='ridge', borderwidth=2, deviceType=deviceType, deviceSubtype=deviceSubtype, contents=contents).pack(fill='x', padx=2, pady=2)

class ControlBindPresetPanel(ControlBindPanel):
    def __init__(self, parent, bindableName, command, presetName, bindsList, newBinding=False, **options):
        ControlBindPanel.__init__(self, parent, bindableName,command,**options)
        def updateCommandName(newText):
            self.bindableName=bindables.bindingPresetsPrefix+newText
            #TODO: make invalid if newText is empty

            return True
        validateCommand=self.register(updateCommandName)

        self.title.destroy() #we're two subclases down from ToggleFrame, but that pesky title gotta go
        self.title=tk.Entry(self.Titlebar, validate='key', validatecommand=(validateCommand, '%P'))
        self.title.insert('insert',presetName)
        self.title.pack(side='left')
        ControlBindPresetPanel.bindsList=bindsList #reminder to self: singleton

        def deleteButton():
            ControlBindPresetPanel.bindsList.remove(self)
            self.destroy()

        tk.Button(self.Titlebar, text='X', command=deleteButton).pack(side='left')
        if (newBinding):
            self.toggle()
            self.title.focus_set()
            self.title.selection_range(0,'end')
            self.AddBinding()

class _bindingBase_():
    def __init__(self, command):
        self.command=command
        self.bindablePreset=None
    def callCommand(self, state):
        if (self.command): self.command[0](state)

class bindingMidi(_bindingBase_):
    def __init__(self, midiDevice, midiChannel,inputNumber, command, threshold=None):
        _bindingBase_.__init__(self, command)
        self.midiDevice=midiDevice
        self.midiChannel = midiChannel
        if (threshold is None):
            threshold=bindables.thresholdDefaultMidiCC
        self.threshold=threshold
        self.valueLast={}
        
        self.inputNumber = inputNumber

class bindingControllerButton(_bindingBase_):
    def __init__(self, command):
        _bindingBase_.__init__(self, command)
class bindingControllerAxis(_bindingBase_):
    def __init__(self, type, flip, function, threshold=None):
        _bindingBase_.__init__(self, function)
        self.type=type
        self.flip=flip
        if (threshold is None):
            threshold=bindables.thresholdDefaultController
        self.threshold=threshold

class bindables():

    thresholdDefaultController = .2
    thresholdDefaultMidiCC = .1
    
    def _CameraRamp_(value, x, y):
        if (value): CameraController.current.StartMove(CameraController.current.PanSpeed.get()*x,CameraController.current.TiltSpeed.get()*y)
        else: CameraController.current.StopMove(None)
    def buttonPanUL(value):
        bindables._CameraRamp_(value, -1,1)
    def buttonPanU(value):
        bindables._CameraRamp_(value, 0,1)
    def buttonPanUR(value):
        bindables._CameraRamp_(value, 1,1)
    def buttonPanL(value):
        bindables._CameraRamp_(value, -1,0)
    def buttonPanR(value):
        bindables._CameraRamp_(value, 1,0)
    def buttonPanDL(value):
        bindables._CameraRamp_(value, -1,-1)
    def buttonPanD(value):
        bindables._CameraRamp_(value, 0,-1)
    def buttonPanDR(value):
        bindables._CameraRamp_(value, 1,-1)
    def bothTriggerAutofocus(value):
        if (CameraController.current.init and value): CameraController.current.TriggerAutofocus()
    def buttonFocusNear(value):
        if (CameraController.current.init and value): CameraController.current.FocusNear(None)
        else: CameraController.current.StopFocus(None)
    def buttonFocusFar(value):
        if (CameraController.current.init and value): CameraController.current.FocusFar(None)
        else: CameraController.current.StopFocus(None)
    def bothRefreshPosition(value):
        if (CameraController.current.init and value): CameraController.current.UpdateCameraDetails()
    
    def _ProcessAxis_(value):
        flip = 1
        if (value < 0): flip=-1
        deadzone = .13
        value = (max(0,abs(value)-deadzone))/(1-deadzone)*flip
        return value
    def _queueJoystickPan_():
        CameraController.current.StartMove(CameraController.current.joystickPanAxesInt[0], CameraController.current.joystickPanAxesInt[1])
    def _SetJoystickPan_(axis, value):
        value = (abs(value)**2.2)*math.copysign(1,value) #gamma curve on stick
        CameraController.current.joystickPanAxesRaw[axis] = value

        tempVec=[CameraController.current.joystickPanAxesRaw[0],CameraController.current.joystickPanAxesRaw[1]]
        tempVec =[int(tempVec[0] * 15), int(tempVec[1] * 15)]

        if (CameraController.current.joystickPanAxesInt != tempVec):
            CameraController.current.joystickPanAxesInt = tempVec
            if (CameraController.current.joystickPanAxesInt == [0,0]): CameraController.current.QueueInput(lambda: CameraController.current.StopMove(None))
            else: CameraController.current.QueueInput(bindables._queueJoystickPan_)

    def analogPTSpeed(value):
        CameraController.current.PanSpeed.set(int(value*14+1))
        CameraController.current.TiltSpeed.set(int(value*14+1))
    def analogSetZSpeed(value):
        CameraController.current.ZoomSpeed.set(int(value*14+1))
    def analogPanDirect(value):
        CameraController.current.directControls['pan'].set(value)
    def analogTiltDirect(value):
        CameraController.current.directControls['tilt'].set(value)
    def analogZoomDirect(value):
        CameraController.current.directControls['zoom'].set(value)
    def analogFocusDirect(value):
        CameraController.current.directControls['focus'].set(value)
    def analogRampZoom(value):
        if (value==0):
            CameraController.current.QueueInput(lambda: CameraController.current.StopZoom(None))
        else:
            if (value > 0): value = int(math.ceil(value*15))
            else: value = int(math.floor(value*15))
            CameraController.current.rampZoomValue = value
            CameraController.current.QueueInput(lambda: CameraController.current.startZoom(CameraController.current.rampZoomValue))
    def analogRampFocus(value):
        value = value*2-1
        if (value==0):
            CameraController.current.QueueInput(lambda: CameraController.current.StopFocus(None))
        else:
            value=int(math.copysign(1,value))
            CameraController.current.rampFocusValue = value
            CameraController.current.QueueInput(lambda: CameraController.current.startFocus(CameraController.current.rampFocusValue))
    def analogRampPan(value):
        bindables._SetJoystickPan_(0,value)
    def analogRampTilt(value):
        bindables._SetJoystickPan_(1,value)
    def bothDebugOutputValue(value):
        print(value)

    def _selectCamera_(value):
        CameraController.current.cameras[value].select()
    def selectCamera1(value):
        bindables._selectCamera_(1)
    def selectCamera2(value):
        bindables._selectCamera_(2)
    def selectCamera3(value):
        bindables._selectCamera_(3)
    def selectCamera4(value):
        bindables._selectCamera_(4)
    def selectCamera5(value):
        bindables._selectCamera_(5)
    def selectCamera6(value):
        bindables._selectCamera_(6)
    def selectCamera7(value):
        bindables._selectCamera_(7)

    def activatePreset(buttonValue, presetName):
        if (buttonValue):
            for preset in CameraController.current.CameraPresets:
                if (preset and preset.isValid() and preset.name==presetName):
                    preset.widget.activatePreset()
                
                    #TODO: figure out of it's preferable to run the whole loop and trigger every matching preset, or just the first match
                    #break
    
    bindablePresets=[]

    bindingCategory = '__CATEGORY__' #append this to the beginning of a key to mark that entry as a category rather than a proper entry
    bindingPresets=bindingCategory+'activate presets'
    bindingPresetsPrefix='preset_'
    index = {
            bindingCategory+'move digital':'move_right_down', #collapsible categories contain all entries up to (and including) the key they contain
                'move_left':(buttonPanL, 'button'),
                'move_right':(buttonPanR, 'button'),
                'move_up':(buttonPanU, 'button'),
                'move_down':(buttonPanD, 'button'),
                'move_left_up':(buttonPanUL, 'button'),
                'move_right_up':(buttonPanUR, 'button'),
                'move_left_down':(buttonPanDL, 'button'),
                'move_right_down':(buttonPanDR, 'button'),
            bindingCategory+'move ramp analog':'ramp_focus',
                'ramp_pan':(analogRampPan, 'analog'),
                'ramp_tilt':(analogRampTilt, 'analog'),
                'ramp_zoom':(analogRampZoom, 'analog'),
                'ramp_focus':(analogRampFocus, 'analog'),
            bindingCategory+'move direct':'focus_direct',
                'pan_direct':(analogPanDirect, 'analog'),
                'tilt_direct':(analogTiltDirect, 'analog'),
                'zoom_direct':(analogZoomDirect, 'analog'),
                'focus_direct':(analogFocusDirect, 'analog'),
            'trigger_autofocus':(bothTriggerAutofocus, 'button'),
            'focus_near':(buttonFocusNear, 'button'),
            'focus_far':(buttonFocusFar, 'button'),
            'refresh_position': (bothRefreshPosition, 'both'),
            bindingCategory+'select camera':'select_camera_7',
                'select_camera_1': (selectCamera1, 'button'),
                'select_camera_2': (selectCamera2, 'button'),
                'select_camera_3': (selectCamera3, 'button'),
                'select_camera_4': (selectCamera4, 'button'),
                'select_camera_5': (selectCamera5, 'button'),
                'select_camera_6': (selectCamera6, 'button'),
                'select_camera_7': (selectCamera7, 'button'),
            bindingPresets:(activatePreset,'button'),
            'pan_tilt_speed':(analogPTSpeed, 'analog'),
            'zoom_speed':(analogSetZSpeed, 'analog'),
            bindingCategory+'debug':'debugOutputValue',
                'debugOutputValueButton':(bothDebugOutputValue, 'button'),
                'debugOutputValue':(bothDebugOutputValue, 'both'),
            }

class deltaTime():
    lastTime=0
    delta = 0
    def update():
        newTime = time.perf_counter()
        deltaTime.delta = newTime-deltaTime.lastTime
        deltaTime.lastTime=newTime

class Settings():
    iniFilename='CameraController_'+VersionNumber+'.ini' 
    CustomCommandName="Add custom commands below this line (just make sure they're tabbed in a level)"
    Defaults = {
        'Startup':{
            'IPADDRESS': '192.168.1.27',
            'USERNAME':'admin',
            'PASSWORD':'',
            'PrintFullCodecResponse':'0',
            'Bindings':('ramp_pan,controller.axis,0,stick,1\n'
                        'ramp_tilt,controller.axis,1,stick,-1\n'
	                    'ramp_zoom,controller.axis,3,stick,-1\n'
	                    'trigger_autofocus,controller.button,9\n'
	                    'trigger_autofocus,controller.button,8\n'
	                    'focus_near,controller.button,4\n'
	                    'focus_far,controller.button,5\n'),
                },

        'User Commands':{
            CustomCommandName:''
            }
        }
    def openConfig():
        Settings.config=ConfigParser(delimiters=(':'))
        print(Settings.iniFilename)
        Settings.config.read(Settings.iniFilename)

        for rootLevel in Settings.Defaults:
            if (rootLevel not in Settings.config):
                Settings.config[rootLevel]=Settings.Defaults[rootLevel]
            else:
                for key in Settings.Defaults[rootLevel]:
                    if (key not in Settings.config[rootLevel]):
                        Settings.config[rootLevel][key]=Settings.Defaults[rootLevel][key]

    def SaveConfig():
        with open(Settings.iniFilename, 'w') as configfile:
            Settings.config.write(configfile)
            configfile.close()

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

class camera():
    selected=None
    selectedNum=None
    def __init__(self, number):
        camera.imageCamAvailable = tk.PhotoImage(file=r'Assets\Button_CamAvailable.png')
        camera.imageCamSelected = tk.PhotoImage(file=r'Assets\Button_CamSelected.png')
        camera.imageCamNone = tk.PhotoImage(file=r'Assets\Button_CamNone.png')
        self.number=number
        self.connected=False
        #Pan Tilt Zoom Focus
        self.position=[False, False, False, False]

        self.selectButton=None

        self.selected=False

        self.brightnessValue=tk.IntVar()
        self.gammaValue = tk.IntVar()
        self.whitebalanceValue = tk.IntVar()
        self.focusManual=tk.IntVar()
        self.brightnessManual=tk.IntVar()
        self.gammaManual = tk.IntVar()
        self.whitebalanceManual = tk.IntVar()

    def select(self):
        if (self.connected): camera.selectCamera(self)

    def onSelect(self):
        self.selected=True
        self.selectButton.config(image=camera.imageCamSelected, state='disabled')

    def onDeselect(self):
        self.selected=False
        if (self.connected): self.selectButton.config(image=camera.imageCamAvailable, state='normal')

    def onDisable(self):
        self.connected=False
        self.onDeselect()
        self.selectButton.config(image=camera.imageCamNone, state='disabled')
    def onEnable(self):
        self.connected=True
        self.onDeselect()

    def selectCamera(newCamera):
        if ((not camera.selected) or camera.selected != newCamera):
            if (camera.selected):
                camera.selected.onDeselect()
            camera.selected=newCamera
            camera.selectedNum = newCamera.number
            newCamera.onSelect()
            CameraController.current.OnCameraChange(newCamera.number)

class configPanel():
    #basically-empty class to drop variables in to conveniently contain access to config panel elements for access between classes
    None

class DummySSH():
    UseDummy=False
    dummyPresetData=('* PresetListResult Preset 1 CameraId: 1\n'
                    '* PresetListResult Preset 1 Name: "Fake_preset"\n'
                    '* PresetListResult Preset 1 PresetId: 1\n'
                    '* PresetListResult Preset 2 CameraId: 1\n'
                    '* PresetListResult Preset 2 Name: "Not_A_Real_Preset"\n'
                    '* PresetListResult Preset 2 PresetId: 2\n'
                    '* PresetListResult Preset 3 CameraId: 2\n'
                    '* PresetListResult Preset 3 Name: "Don\'t_Believe_this_Preset"\n'
                    '* PresetListResult Preset 3 PresetId: 3\n'
                    '* PresetListResult Preset 4 CameraId: 3\n'
                    '* PresetListResult Preset 4 Name: "Definitely_Real_Preset"\n'
                    '* PresetListResult Preset 4 PresetId: 4\n')
    def __init__(self):

        #populate the initial response with a handful of things to get us started
        self.responseQueue = ('* Camera 1 Connected: True\n'
                              '* Camera 2 Connected: True\n'
                              '* Camera 3 Connected: True\n'
                              ) + DummySSH.dummyPresetData
        for i in range(3):
            self.responseQueue += ('* Camera ' + str(i+1) + ' Position Focus: 4500\n'
                                '* Camera ' + str(i+1) + ' Position Zoom: 0\n'
                                '* Camera ' + str(i+1) + ' Position Pan: 400\n'
                                '* Camera ' + str(i+1) + ' Position Tilt: 60\n'
                                   )
    def recv_ready(self):
        if (self.responseQueue is not None): return True
        return False
    def recv(self, amount):
        response=self.responseQueue.encode('ASCII')
        self.responseQueue = None
        return response
    def send(self, message):
        #TODO: resend all the preset list result stuff on request
        #TODO: 
        None




#start the actual program
if __name__ == '__main__':
    programMain = CameraController()
    while True:
        programMain.main()