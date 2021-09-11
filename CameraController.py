import pygame
import pygame.midi
import pygame.joystick
import math

from helpers import *
from Camera import *
from UI import *
from Bindings import *
import debug
from Settings import *
from Shell import *

#Note to self: F9 on a line to set a breakpoint

class CameraController():
    def __init__(self):
        controller.current=self
        
        for arg in sys.argv:
            if (arg=='DebugCam'):
                debug.forceCameraConnection=True
                print('forcing debug cameras on')
            elif (arg=='DummySSH'):
                print('IN INTERFACE DEBUG MODE, USING DUMMY SSH! No actual device connected!')
                debug.DummySSH.UseDummy=True

        self.init = False

        self.window = tk.Tk()
        self.window.title('Cisco Codec Controller XD Deluxe 9000 👌👏😁👍')

        #Settings.initializeSettings()

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
        self.cameras=[None, Camera(1), Camera(2), Camera(3), Camera(4), Camera(5), Camera(6), Camera(7)]

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
        self.CameraPresets = [] #list of CameraPresetPanel
        self.CamerasPresets = [] #probably won't use, but reserving the variable name
        self.Frame_PresetsContainer = None
        self.PresetsFilteredConnected = tk.IntVar()
        self.PresetsFilteredConnected.set(1)
        self.PresetsFilteredCurrent = tk.IntVar()
        self.PresetsFilteredCurrent.set(0)

        self.inputBuffer = None
        self.inputBufferTime = self.inputBufferTimer = .05 #TODO: make configurable

        self.inputDevicesMidis = []
        self.outputDevicesMidis = []
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

        Shell.setup()
        self.SettingsMenu= None
        self.SettingsMenuOld = None

        Settings.openConfig()
        
        self.loadControls()

        Settings.parseBindings(Settings.config['Startup']['Bindings'])

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
        if (not CamNumber): CamNumber = Camera.selectedNum
        message = 'xStatus Camera ' + str(CamNumber) + ' ' + message
        self.shell.send(message+'\n')

    def xCommand(self,message, CamNumber = None):
        if (not CamNumber): CamNumber = Camera.selectedNum
        message = 'xCommand Camera ' + message + ' CameraID:' + str(CamNumber)
        self.shell.send(message+'\n')
        debug.print('Message sent: ' + message)

    def xConfiguration(self,message, CamNumber = None):
        if (not CamNumber): CamNumber = Camera.selectedNum
        message='xConfiguration Cameras Camera ' + str(CamNumber) + ' ' + message
        self.shell.send(message+'\n')
        debug.print('Message sent: ' + message)

    def FeedbackSubscribe(self):
        self.FeedbackUpdate(None, 1)
        for i in range(1,8):
            self.shell.send('xfeedback register /Status/Camera[@item="' + str(i) + '"]/Connected\n')
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
        message = message.replace(self.PrefabCommandCurrentCamera, 'CameraID:' + str(Camera.selectedNum))
        message = message.replace(self.PrefabConfigCurrentCamera, 'Camera ' + str(Camera.selectedNum))

        self.shell.send(message + '\n')
        debug.print('Message sent: ' + message)

        
    def toggleAllPresetEditStates(self, state):
        for child in self.Frame_PresetsContainer.contents.winfo_children():
            if (isinstance(child, CameraPresetPanel)):
                child.SetEditState(state)
        self.PresetsFilteredConnected.set(not state)
        self.filterPresetsCurrent()

    def filterPresetsCurrent(self):
        for child in self.Frame_PresetsContainer.contents.winfo_children():
            if (isinstance(child, CameraPresetPanel)):
                child.filter()
        filterConnectedStatus=self.PresetsFilteredConnected.get()
        filterCurrentStatus=self.PresetsFilteredCurrent.get()
        if (not filterConnectedStatus):
            self.presetAddButtons[0].pack(padx=5)
            self.presetAddButtons[0].master.grid(column=0, row=0, sticky='nsew')
        else:
            self.presetAddButtons[0].forget()
        for i in range(1, len(self.presetAddButtons)):

            if (not filterConnectedStatus and self.cameras[i].connected):
                self.presetAddButtons[i].pack(padx=5)
            else:
                self.presetAddButtons[i].forget()

            filtered=False
            if (filterConnectedStatus and not self.cameras[i].connected): filtered=True
            if (filterCurrentStatus and not Camera.selectedNum==i): filtered=True

            if (filtered):
                self.presetAddButtons[i].master.grid_forget()
                self.Frame_PresetsContainer.contents.columnconfigure(i, weight=0)
            else:
                self.presetAddButtons[i].master.grid(column=i, row=0, sticky='nsew')
                self.Frame_PresetsContainer.contents.columnconfigure(i, weight=1)

        #not totally sure why this is necessary here and nowhere elese, but the frame resizes wrong otherwise.
        self.Frame_PresetsContainer.contents.update_idletasks()
        self.Frame_PresetsContainer.onFrameConfigure(None)

    def ListPresets(self):
        self.shell.send('xCommand Camera Preset List\n')
        self.shell.send('xStatus Preset\n')

    def CreateNewPreset(self, camNum, nameField=None, numField=None):
        #because it's coming from a tk.Entry, presetNum is a str (either '' or str(int))
        if (camNum is None): camNum=Camera.selectedNum
        if (camNum == 0):
            num=''
            if (numField):
                num=numField.get()
                numField.delete(0,'end')
            name=None
            if (nameField):
                name=nameField.get()
                nameField.delete(0,'end')
                if (hasattr(nameField, 'defaultValue')):
                    nameField.insert(0,nameField.defaultValue)
            if (num ==''):
                for num in range(1,16):
                    if(self.CamerasPresets[num]==None):
                        num=str(num)
                        break
            if (name is None or name==''):
                name='Global Preset ' + presetNum
            self.shell.send('xCommand Preset Store PresetId: '
                            + num + ' Type:Camera Description: "'+name+'"\n')
        else:
            if (nameField is None):
                name='unnamed'
            else:
                name=nameField.get()
            self.shell.send('xCommand Camera Preset Store CameraId: ' + str(camNum) + ' Name: "'+name+'"\n')

    def InitializePresetLists(self):
        debug.print('(re)initializing presets')
        for container in self.CameraPresets:
            if (container): container.destroy()
        self.CameraPresets=[]
        for i in range(36):
            self.CameraPresets.append(None)
        for container in self.CamerasPresets:
            if (container): container.destroy()
        self.CamerasPresets=[]
        for i in range(16):
            self.CamerasPresets.append(None)
        self.ListPresets()

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
        if (p is not None and p!= Camera.selected.position[0]):
            self.PanningStart()
            sendString += ' Pan: ' + str(p*panRange)
        if (t is not None and t != Camera.selected.position[1]):
            self.TiltingStart()
            sendString += ' Tilt: ' + str(t*tiltRange)

        self.xCommand(sendString)

    def CenterCamera(self):
        self.xCommand('PositionReset')
        if (Camera.selected.position[0] != self.CameraPanCenter): self.PanningStart()
        if (Camera.selected.position[1] != self.CameraTiltCenter): self.TiltingStart()
        if (Camera.selected.position[2] != self.CameraZoomCenter): self.ZoomingStart()
        #if (Camera.selected.position[3] != self.CameraFocusCenter): self.FocusingStart() #check if focus is manual before doing this

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
            try: image = tk.PhotoImage(file = Assets.getAsset(image))
            except: image=None
        if (image): button = tk.Button(frame, image=image, relief='flat', borderwidth=0)
        else: button = tk.Button(frame, text=label, width=3, height=2)
        button.image = image
        button.grid(row=gridY,column=gridX, sticky='nsew')
        button.bind('<ButtonPress-1>', functionDn)
        button.bind('<ButtonRelease-1>', functionUp)
        return button

    def OnCameraChange(self, cameraNumber):
        if (cameraNumber != Camera.selectedNum): self.FeedbackUpdate(Camera.selectedNum, cameraNumber)

        if (self.Frame_PresetsContainer): self.filterPresetsCurrent()
        self.toggleFocusManual.config(variable=Camera.selected.focusManual)
        self.toggleBrightnessManual.config(variable=Camera.selected.brightnessManual)
        self.ScaleBrightness.setVariable(Camera.selected.brightnessValue)
        self.toggleGammaManual.config(variable=Camera.selected.gammaManual)
        self.ScaleGamma.setVariable(Camera.selected.gammaValue)
        self.toggleWhitebalanceManual.config(variable=Camera.selected.whitebalanceManual)
        self.ScaleWhitebalance.setVariable(Camera.selected.whitebalanceValue)
        self.UpdateCameraDetails()

    def UpdateCameraDetails(self):
        self.xStatus('Position')
        self.GetCameraConfig(Camera.selectedNum)
    def UpdateCameraConnectionStatus(self):
        for i in range(7):
            self.shell.send('xStatus Camera ' + str(i+1) + ' Connected\n')

    def CameraAvailable(self, cameraNumber, available):
        if (available): self.cameras[cameraNumber].onEnable()
        else:
            self.cameras[cameraNumber].onDisable()
            if (cameraNumber == Camera.selectedNum):
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
        Settings.config['User Commands'][Settings.CustomCommandName] = CustomCommandString

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
        #command = UserPrefabCommands[index]
        del self.UserPrefabCommands[index]
        self.PrefabCommandsList.delete(index + self.PrefabCommandCustomStart)
        frame.destroy()
        self.UpdateCustomCommandList()
        Settings.SaveConfig()

    def AddCustomCommand(self, command):
        Frame_CommandParent = tk.Frame(self.Frame_CustomCommands.contents, relief='groove', borderwidth = 2)
        Frame_CommandParent.pack(fill='x')

        RemoveButton = tk.Button(Frame_CommandParent, text='x', command=Frame_CommandParent.destroy)#lambda:root.RemoveCustomCommand(Frame_CommandParent))
        CommandEntry = tk.Entry(Frame_CommandParent)
        SaveButton = tk.Button(Frame_CommandParent, text='Save', command=lambda:self.SaveCustomCommand(self.Frame_CustomCommands.contents, CommandEntry.get()))

        CommandEntry.insert(0, command)
        CommandEntry.bind('<Return>', lambda event: self.SendManualCommand(CommandEntry))
        CommandButton = tk.Button(Frame_CommandParent, text='Send', command = lambda: self.SendManualCommand(CommandEntry))

        RemoveButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)
        SaveButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)
        CommandEntry.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt, fill='x', expand=True)
        CommandButton.pack(side=tk.RIGHT, padx=self.PadInt, pady=self.PadInt)

    def SetBrightnessLevel(self, value, cam=None):
        self.xConfiguration('Brightness Level: ' + str(value), cam)
    def SetWhitebalanceLevel(self, value, cam=None):
        self.xConfiguration('Whitebalance Level: ' + str(value), cam)
    def SetGammaLevel(self, value, cam=None):
        self.xConfiguration('Gamma Level: ' + str(value), cam)
    def SetFocusAuto(self):
        if (Camera.selected.focusManual.get()): self.xConfiguration('Focus Mode: Auto')
        else: self.xConfiguration('Focus Mode: Manual')
    def SetBrightnessAuto(self):
        if (Camera.selected.brightnessManual.get()): self.xConfiguration('Brightness Mode: Auto')
        else: self.xConfiguration('Brightness Mode: Manual')
    def SetWhitebalanceAuto(sel):
        if (Camera.selected.whitebalanceManual.get()): self.xConfiguration('Whitebalance Mode: Auto')
        else: self.xConfiguration('Whitebalance Mode: Manual')
    def SetGammaAuto(self):
        if (Camera.selected.gammaManual.get()): self.xConfiguration('Gamma Mode: Auto')
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
                    self.cameras[cami].selectButton = tk.Button(self.Frame_CameraList, text=str(cami)+'  ', image=Camera.imageCamAvailable, compound='center', command=lambda cami=cami: self.cameras[cami].select())
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
                self.AddDirectionButton('↖', Frame_ButtonGrid, 1, 1, lambda event:
                                        self.StartMove(-self.PanSpeed.get(),self.TiltSpeed.get()),self.StopMove, image='Arrow_LU.png')
                self.AddDirectionButton('⬆', Frame_ButtonGrid, 1, 2, lambda event:
                                        self.StartMove(0,self.TiltSpeed.get()),self.StopMove, image='Arrow_U.png')
                self.AddDirectionButton('↗', Frame_ButtonGrid, 1, 3, lambda event:
                                        self.StartMove(self.PanSpeed.get(),self.TiltSpeed.get()),self.StopMove, image='Arrow_RU.png')
                self.AddDirectionButton('⬅', Frame_ButtonGrid, 2, 1, lambda event:
                                        self.StartMove(-self.PanSpeed.get(),0),self.StopMove, image='Arrow_L.png')
                self.AddDirectionButton('➡', Frame_ButtonGrid, 2, 3, lambda event:
                                        self.StartMove(self.PanSpeed.get(),0),self.StopMove, image='Arrow_R.png')
                self.AddDirectionButton('↙', Frame_ButtonGrid, 3, 1, lambda event:
                                        self.StartMove(-self.PanSpeed.get(),-self.TiltSpeed.get()),self.StopMove, image='Arrow_LD.png')
                self.AddDirectionButton('⬇', Frame_ButtonGrid, 3, 2, lambda event:
                                        self.StartMove(0,-self.TiltSpeed.get()),self.StopMove, image='Arrow_D.png')
                self.AddDirectionButton('↘', Frame_ButtonGrid, 3, 3, lambda event:
                                        self.StartMove(1,-self.TiltSpeed.get()),self.StopMove, image='Arrow_RD.png')
                self.AddDirectionButton('Z+', Frame_ButtonGrid, 1, 5, self.ZoomIn,self.StopZoom,image='Button_Zoom_In.png')
                self.AddDirectionButton('Z-', Frame_ButtonGrid, 2, 5, self.ZoomOut,self.StopZoom, image='Button_Zoom_Out.png')
                self.AddDirectionButton('F+', Frame_ButtonGrid, 1, 6, self.FocusFar, self.StopFocus)
                self.AddDirectionButton('F-', Frame_ButtonGrid, 2, 6, self.FocusNear, self.StopFocus)
                image=tk.PhotoImage(file=Assets.getAsset('Arrow_C.png'))
                button=tk.Button(Frame_ButtonGrid, text='FTrig', relief='flat', borderwidth=0, image=image, command= self.TriggerAutofocus)
                button.grid(column=2, row=2)
                button.image=image

                tk.Scale(Frame_ButtonGrid, variable=self.PanSpeed, from_=1,to_=15, orient='horizontal'
                         ).grid(column=1, row=0, columnspan=3)
                tk.Scale(Frame_ButtonGrid, variable=self.TiltSpeed, to_=1,from_=15, orient='vertical'
                         ).grid(column=0,row=1, rowspan=3)
                tk.Scale(Frame_ButtonGrid, variable=self.ZoomSpeed, to_=1,from_=15, orient='vertical'
                         ).grid(column=4,row=1, rowspan=2)

                tk.Checkbutton(Frame_ButtonGrid, text='flip X', variable=self.webcamFlip, offvalue=1, onvalue=-1
                               ).grid(column=5, row=3, columnspan=2)


                ButtonRecenter= tk.Button(Frame_ButtonGrid,text='Recenter', command=self.CenterCamera)
                ButtonRecenter.grid(column=0, row=4, padx=3, pady=3, columnspan=2)

            Frame_Presets = tk.Frame(Frame_Main, relief='sunken', borderwidth=2)
            if True:
                Frame_PresetsToolbar = tk.Frame(Frame_Presets)
                if True:
                    self.TogglePresetEdit = ToggleButtonChecked(Frame_PresetsToolbar,
                                                                textOff=['locked', 'edit'],textOn = ['lock','editing'],
                                                                toggleCommand=self.toggleAllPresetEditStates)
                    self.TogglePresetEdit.pack(side='left')
                    tk.Checkbutton(Frame_PresetsToolbar, text='only current camera',
                                   variable=self.PresetsFilteredCurrent,
                                   command=self.filterPresetsCurrent).pack(side='left')

                    tk.Button(Frame_PresetsToolbar, text = 'Refresh',
                              command = self.InitializePresetLists).pack(side='right')
                
                self.Frame_PresetsContainer = ScrollFrame(Frame_Presets, maxHeight=400,
                                                          frameConfigureCommand=lambda widget:
                                                          self.UpdateWindowCellWeights(widget, 0, rootFrame=Frame_Main))
                
                def validatePresetNumber(newValue):
                    if (newValue==''): return True
                    try:
                        intval=int(newValue)
                    except: return False
                    return 1<=intval<=16

                self.presetAddButtons=[]

                #first column is global presets
                frame_presetHeader=tk.Frame(self.Frame_PresetsContainer.contents, relief='ridge',borderwidth=1)
                tk.Label(frame_presetHeader, text='Presets').pack()
                #packing of this button happens in Camera.onEnable()

                self.presetAddButtons.append(tk.Frame(frame_presetHeader))
                presetNameField=tk.Entry(self.presetAddButtons[0])
                presetNameField.validation=presetNameField.register(CameraPresetPanel.validatePresetName)
                presetNameField.defaultValue='Preset_Name'
                presetNameField.insert(0,presetNameField.defaultValue)
                presetNameField.config(validate='key', validatecommand=(presetNameField.validation, '%S'))
                presetNumField=tk.Entry(self.presetAddButtons[0], width=2)
                presetNumField.validation=presetNumField.register(validatePresetNumber)
                presetNumField.config(validate='key',validatecommand=(presetNumField.validation, '%P'))
                
                presetNameField.grid(column=0, row=0, columnspan=3, sticky='nsew')
                tk.Label(self.presetAddButtons[0],text='#').grid(column=0,row=1)
                presetNumField.grid(column=1,row=1)
                tk.Button(self.presetAddButtons[0], text='add preset',
                          command = lambda: self.CreateNewPreset(0, nameField=presetNameField,
                                                                 numField=presetNumField)).grid(column=2, row=1)
                self.presetAddButtons[0].columnconfigure(2,weight=1)
                frame_presetHeader.grid(column=0, row=0, sticky='nsew')

                #rest of the columns are individual camera presets
                for i in range(1,8):
                    frame_presetHeader=tk.Frame(self.Frame_PresetsContainer.contents, relief='ridge',borderwidth=1)
                    tk.Label(frame_presetHeader, text='Cam '+str(i)).pack()
                    #packing of this button happens in Camera.onEnable()
                    self.presetAddButtons.append(tk.Button(frame_presetHeader, text='add preset',
                                                           command = lambda i=i: self.CreateNewPreset(i)))
                    frame_presetHeader.grid(column=i, row=0, sticky='nsew')
                    self.Frame_PresetsContainer.contents.columnconfigure(i, weight=1)
                Frame_PresetsToolbar.pack(fill='x')
                self.Frame_PresetsContainer.pack(fill='both', expand=True)

            def OptionsMenuToggle(toggle): #TODO: move somewhere better
                self.OptionsMenuOpen = toggle
                if (toggle):
                    self.GetCameraConfig(Camera.selectedNum)
                    self.ConfigUpdateTimer = self.ConfigUpdateInterval
            Frame_SetupPanel = tk.Frame(Frame_Main)
            if True:
                tk.Button(Frame_SetupPanel, text='settings', command=self.OpenSettingsMenu).pack(side='top')

                self.Frame_ConfigPopout = ToggleFrame(Frame_SetupPanel, title='Configuration', keepTitle=True,
                                                      relief='groove', borderwidth=2, buttonShowTitle='show',
                                                      buttonHideTitle='hide', toggleCommand=OptionsMenuToggle,
                                                      togglePin='left').contentFrame
                if True:
                    Frame_FocusMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_FocusMode, text='Focus').pack(pady=(2,0))
                        frame_FocusButtons = tk.Frame(Frame_FocusMode)
                        if True:
                            
                            self.toggleFocusManual=tk.Checkbutton(frame_FocusButtons, text='Auto',
                                                                         command=self.SetFocusAuto)
                            self.toggleFocusManual.pack(side='left')
                        frame_FocusButtons.pack(fill='x')

                    Frame_BrightnessMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_BrightnessMode, text='Brightness').pack(pady=(2,0))
                        frame_BrightnessButtons = tk.Frame(Frame_BrightnessMode)
                        if True:
                            self.ScaleBrightness=ConfigSlider(frame_BrightnessButtons,
                                                                     command=self.SetBrightnessLevel, from_=1, to_=31)
                            self.toggleBrightnessManual = tk.Checkbutton(frame_BrightnessButtons,text='Auto',
                                                                                command=self.SetBrightnessAuto)
                            self.toggleBrightnessManual.pack(side='left')
                            self.ScaleBrightness.pack(side='left', fill='x')
                        frame_BrightnessButtons.pack(fill='x')

                    Frame_WhitebalanceMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_WhitebalanceMode, text='White Balance').pack(pady=(2,0))
                        frame_WhitebalanceButtons = tk.Frame(Frame_WhitebalanceMode)
                        if True:
                            self.ScaleWhitebalance=ConfigSlider(frame_WhitebalanceButtons,
                                                                     command=self.SetWhitebalanceLevel, from_=1, to_=16)
                            self.toggleWhitebalanceManual=tk.Checkbutton(frame_WhitebalanceButtons, text='Auto',
                                                                                command=self.SetWhitebalanceAuto)
                            self.toggleWhitebalanceManual.pack(side='left')
                            self.ScaleWhitebalance.pack(side='left', fill='x')
                        frame_WhitebalanceButtons.pack(fill='x')

                    Frame_GammaMode = tk.Frame(self.Frame_ConfigPopout, relief='groove', borderwidth=4)
                    if True:
                        tk.Label(Frame_GammaMode, text='Gamma').pack(pady=(2,0))
                        frame_GammaButtons = tk.Frame(Frame_GammaMode)
                        if True:
                            self.ScaleGamma=ConfigSlider(frame_GammaButtons,
                                                                     command=self.SetGammaLevel, from_=0, to_=7)
                            self.toggleGammaManual = tk.Checkbutton(frame_GammaButtons, text='Auto',
                                                                           command=self.SetGammaAuto)
                            self.toggleGammaManual.pack(side='left')
                            self.ScaleGamma.pack(side='left', fill='x')
                        frame_GammaButtons.pack(fill='x')
    
            
                    Frame_FocusMode.pack(fill='x')
                    Frame_BrightnessMode.pack(fill='x')
                    Frame_WhitebalanceMode.pack(fill='x')
                    Frame_GammaMode.pack(fill='x')
            
                self.Frame_ConfigPopout.master.pack(side='top', padx=self.PadInt, pady=self.PadInt)
    
            self.Frame_CameraList.pack(side='left', fill='y',padx=self.PadInt, pady=self.PadInt)
            Frame_Readout.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)
            Frame_ButtonGrid.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)
            Frame_Presets.pack(side='left', fill='both', padx=self.PadInt, pady=self.PadInt, expand=True)
            Frame_SetupPanel.pack(side='left', fill='y', padx=self.PadInt, pady=self.PadInt)

        def weightToggle(state): #TODO: move to root of class?
            if (state):
                self.Frame_CustomCommands.frameConfigureCommand(self.Frame_CustomCommands)
            else:
                self.window.rowconfigure(1, weight=0)

        Frame_CustomCommandsParent = ToggleFrame(self.window, title='Custom commands', togglePin='left',
                                                 buttonShowTitle='Custom Commands', buttonHideTitle='Hide',
                                                 toggleCommand=weightToggle)
        self.Frame_CustomCommands = ScrollFrame(Frame_CustomCommandsParent.contentFrame, maxHeight=400,
                                                frameConfigureCommand=lambda widget:
                                                self.UpdateWindowCellWeights(widget, 1))
        if True:
            PrefabCommandsButton = tk.Menubutton(Frame_CustomCommandsParent.contentFrame,
                                                 text='Add Custom Command',relief='raised')
            Frame_CustomCommandsToolbar = tk.Frame(Frame_CustomCommandsParent.contentFrame)
            if True:
                PrefabCommandsButton.pack()

                #TODO: add a scrollbar into this
                self.SavedPrefabCommandsView = ToggleFrame(Frame_CustomCommandsToolbar, title='Saved Commands',
                                                           buttonShowTitle = 'Show Saved Commands', buttonHideTitle='Hide',
                                                           relief='groove', borderwidth=2)
                self.SavedPrefabCommandsView.contentFrame.configure(bg='white')
    
                self.SavedPrefabCommandsView.pack(side='right')

                self.PrefabCommandsList= tk.Menu(PrefabCommandsButton, tearoff = 0)
                PrefabCommandsButton['menu'] = self.PrefabCommandsList

                self.PrefabCommandsList.add_command(label='blank command', command=lambda:self.AddCustomCommand(''))
                self.PrefabCommandsList.add_separator()
                for customCommand in self.PrefabCommands:
                    self.PrefabCommandsList.add_command(label=customCommand, command=lambda c=customCommand:
                                                        self.AddCustomCommand(c))

                self.PrefabCommandsList.add_separator()

                self.PrefabCommandCustomStart=self.PrefabCommandsList.index('end')+2 #index of the end doesn't account for separators, but all other index operations do

                self.PrefabCommandsList.add_command(label='          Custom User Commands:', state='disabled')
                i = 0
                for userCommand in self.UserPrefabCommands:
                    self.PrefabCommandsList.add_command(label=userCommand, command=lambda
                                                        c=userCommand: self.AddCustomCommand(c))
                    Frame_Command = tk.Frame(self.SavedPrefabCommandsView.contentFrame, bg='white')
                    Frame_Command.pack(fill='x')
                    tk.Label(Frame_Command, text=userCommand,bg='white').pack(side='left')
                    tk.Button(Frame_Command, text='Delete', command=lambda f=Frame_Command:
                              self.DeleteCustomCommand(f)).pack(side='right')

                    i += 1

            Frame_CustomCommandsToolbar.pack(side='bottom', pady=8, fill='x')
            self.Frame_CustomCommands.pack(padx=self.PadExt, pady=self.PadExt, fill='both', expand=True)
    
        Frame_Main.grid(column=0, row=0, padx=self.PadExt, pady=self.PadExt, sticky='nsew')
        Frame_CustomCommandsParent.grid(column=0, row=1, padx=self.PadExt, pady=self.PadExt, sticky='nsew')
        self.window.columnconfigure(0, weight=1)

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

    def closeSettings(self):
        if (Settings.unsavedChanges):
            confirmClose=messagebox.askokcancel('Close','Unsaved changes! Close anyway?')
            if (confirmClose):
                self.SettingsMenu.destroy()
        else:
            self.SettingsMenu.destroy()

    def settingsMenuClosed(self, event):
        self.SettingsMenu=None
        #self.enableFrame(self.window)
        inputRouting.bindListenCancelSafe()

    def OpenSettingsMenu(self):
        if (self.SettingsMenu is None):

            Settings.openSettings()

            #self.disableFrame(self.window)

            self.SettingsMenu = tk.Toplevel(self.window)
            self.SettingsMenu.protocol('WM_DELETE_WINDOW', self.closeSettings)

            self.SettingsMenu.grab_set()
    
            self.SettingsMenu.geometry('1200x800')

            debugToggleFrame=tk.Frame(self.SettingsMenu)
            if True:
                tk.Checkbutton(debugToggleFrame, text='print verbose debug',
                               variable=debug.printVerbose, command=Settings.toggleVerboseDebugPrints).pack(side='left')
                tk.Checkbutton(debugToggleFrame, text='mute codec responses',
                               variable=debug.muteCodecResponse, command=Settings.toggleMuteCodecPrints).pack(side='left')
                
            Settings.buildBindingsFrame()

            #TODO: put frameFooter and self.SettingsMenu.bindingsList in a collapsable frame together
            frameFooter = tk.Frame(self.SettingsMenu)
            if True:
                Settings.saveButton= tk.Button(frameFooter, text='save', command=Settings.SaveBindings)
                Settings.saveButton.pack(side='right')
                Settings.unsavedChangesWarning=tk.Label(frameFooter, text='Unsaved Changes!')
                tk.Button(frameFooter, text='reset bindings', command=Settings.resetBindingsButton).pack(side='left')
            settingsTitle = tk.Label(self.SettingsMenu, text='Settings')
            settingsTitle.pack()
            settingsTitle.bind('<Destroy>', self.settingsMenuClosed)
            debugToggleFrame.pack(fill='x')
            self.SettingsMenu.bindingsList.pack(fill='both', expand=True)
            frameFooter.pack(padx=3, pady=3, fill='x')
        else:
            #TODO: remove this dumb gag
            window=tk.Toplevel(self.window)
            tk.Label(window, text='nice try').pack()

    def PopulateStartScreen(self):
        def SSHConnect():
            connected=False

            Settings.config['Startup']['IPADDRESS'] = AddressField.get()
            Settings.config['Startup']['USERNAME'] = UsernameField.get()
            Settings.config['Startup']['PASSWORD'] = PasswordField.get()

            Settings.SaveConfig()
            if (debug.DummySSH.UseDummy):
                self.shell=debug.DummySSH()
                connected=True
            else:
                print('connecting to ' + Settings.config['Startup']['USERNAME'] + '@' + Settings.config['Startup']['IPADDRESS'])
                connected=Shell.connect(hostname=Settings.config['Startup']['IPADDRESS'],
                                     username=Settings.config['Startup']['USERNAME'],
                                     password=Settings.config['Startup']['PASSWORD'])
                
                if (connected):
                    self.shell = Shell(self)
                    while not (self.shell.recv_ready()):
                            time.sleep(1)
                    out = self.shell.recv().decode('ascii')
                    debug.printCodec(out)
                    #TODO: login message might come in several messages, keep checking for a match for a second or so if none is found
                    #TODO: also, check if codec login message is different on various firmwares
                    #TODO: also also, add override option in settings

                    #matchString=['Welcome to',
                    #             'Cisco Codec Release']
                    #for match in matchString:
                    #    if (match not in out):
                    #        print ( 'connected to wrong device??')
                    #        connected=False
                    #        #TODO: close SSH session
                    #        break
            if (connected):
                StartFrame.destroy()
                self.PopulateButtons()
                self.FeedbackSubscribe()
                for i in range(7):
                    self.CameraAvailable(i+1, False)

                self.UpdateCameraConnectionStatus()
                self.InitializePresetLists()
                self.init = True
            
        def SSHConnectEvent(event):
            SSHConnect()

        StartFrame = tk.Frame(self.window)
        if True:
            tk.Label(StartFrame, text='Codec Login').pack()

            AddressFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(AddressFrame, text='IP Address').pack(side='left')

                AddressField = tk.Entry(AddressFrame)
                AddressField.insert(0,Settings.config['Startup']['IPADDRESS'])
                AddressField.focus_set()
                AddressField.bind('<Return>',SSHConnectEvent)
                AddressField.pack(side='left')

            UsernameFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(UsernameFrame, text='Username').pack(side='left')

                UsernameField = tk.Entry(UsernameFrame)
                UsernameField.insert(0,Settings.config['Startup']['USERNAME'])
                UsernameField.bind('<Return>',SSHConnectEvent)
                UsernameField.pack(side='left')

            PasswordFrame=tk.Frame(StartFrame)
            if True:
                tk.Label(PasswordFrame, text='Password').pack(side='left')

                PasswordField = tk.Entry(PasswordFrame)
                PasswordField.insert(0,Settings.config['Startup']['PASSWORD'])
                PasswordField.bind('<Return>',SSHConnectEvent)
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

    def clearFeedback(self, deviceIndex):
        if ('Launchpad Mini' in self.getMidiName(deviceIndex)):
            device=self.outputDevicesMidis[deviceIndex]
            device.write_short(0xb0, 00,00) #this should clear the pad
            #for i in range(121):
            #    device.note_on(i, velocity=0, channel=0)

    def getMidiName(self, deviceIndex):
        return str(pygame.midi.get_device_info(deviceIndex)[1], 'utf-8')
    def refreshInputDevicesMidi(self):
        debug.print('midi devices:')
        self.inputDevicesMidis = []
        self.inputDevicesMidiNames = []
        self.outputDevicesMidis = []
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            debug.print(info)
            name=self.getMidiName(i)
            print(name)
            if (info[2]==1):
                self.inputDevicesMidis.append(pygame.midi.Input(i))
            else:
                self.inputDevicesMidis.append(None)
            #throws an error if Microsoft MIDI Mapper is loaded 
            #TODO: we shouldn't be loading outputs unless we're using them anyways
            if (info[3]==1 and str(info[1], 'utf-8') != 'Microsoft MIDI Mapper'):
                self.outputDevicesMidis.append(pygame.midi.Output(i))
                self.clearFeedback(i)
                if (name in self.inputDevicesMidiNames):
                    bindables.midiIOMapping[self.inputDevicesMidiNames.index(name)]=i
            else:
                self.outputDevicesMidis.append(None)
            self.inputDevicesMidiNames.append(name)
        print(bindables.midiIOMapping)

    def refreshInputDevicesControllers(self):
        debug.print ('controllers:')
        self.inputDevicesControllers = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        debug.print(self.inputDevicesControllers)
        self.inputDevicesControllersLastVals = None
        #axis bindings are command, type, flip (where 'type' is 'stick' or 'trigger', deadzone is treated differently between the two)
        #hat bindings are a list of commands for the eight directions (call the direction's command with (1) when the hat moves to that direction, call the direction's command with (0) when the hat moves and hat last was that direction)


        if (len(self.inputDevicesControllers)):
            controller = pygame.joystick.Joystick(0) #TODO: selector to pick which controller is active, and then a ChangeController function
            self.inputDevicesControllers.append(controller)
            self.inputDevicesControllersLastVals = { 'axis':[], 'button':[], 'hat':[] }
            for a in range(controller.get_numaxes()):
                self.inputDevicesControllersLastVals['axis'].append(0)
            for b in range(controller.get_numbuttons()):
                self.inputDevicesControllersLastVals['button'].append(False)
            for h in range(controller.get_numhats()):
                self.inputDevicesControllersLastVals['hat'].append(None)


    def loadControls(self):
        pygame.midi.init()
        self.refreshInputDevicesMidi()
        pygame.joystick.init()
        self.refreshInputDevicesControllers()


    def processInputs(self):
        self.ProcessMidi()
        self.processController()

    def processController(self):

        def processAxis(axisNumber, axisType, flip, threshold): #TODO: move to root of class
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
        
        def checkButton(buttonNumber): #TODO: move to root of class
            value = controller.get_button(buttonNumber)
            changed = value != self.inputDevicesControllersLastVals['button'][buttonNumber]
            self.inputDevicesControllersLastVals['button'][buttonNumber] = value
            return (changed, value)


        if (len(self.inputDevicesControllers)):
            controller=self.inputDevicesControllers[0]

            for a in range(len(self.inputDevicesControllersLastVals['axis'])):
                binding=Settings.commandBinds['controller']['axis'][a]
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
                            inputRouting.bindCommand('controller', 'axis', 'analog',
                                                     (a, axisType, 1, bindables.thresholdDefaultController))
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
                elif (Settings.commandBinds['controller']['button'][b]):
                    changed, value = checkButton(b)
                    if (changed):
                        Settings.commandBinds['controller']['button'][b].callCommand(value)

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
                        if (lastVal is not None and Settings.commandBinds['controller']['hat'][h][lastVal]):
                            Settings.commandBinds['controller']['hat'][h][lastVal].callCommand(False)
                        if (hat is not None and Settings.commandBinds['controller']['hat'][h][hat]):
                            Settings.commandBinds['controller']['hat'][h][hat].callCommand(True)
                    self.inputDevicesControllersLastVals['hat'][h] = hat


    def ProcessMidi(self):

        def checkInputValidity(bind): #TODO: move to root of class?
            return ((not bind.midiDevice or bind.midiDevice ==self.inputDevicesMidiNames[deviceIndex])
                    and (not bind.midiChannel or bind.midiChannel == channel))

        eventNoteOn = 0x90
        eventNoteOff = 0x80
        eventControlChange = 0xb0
        deviceIndex = 0

        #TODO: implement RPN and NRPN checks
        #NOTE: a ControlChange with control 6 is for RPN or NRPN messages,
        #   if it's immediately preceded by two ControlChanges with 101 and 100 (RPN) or 99 and 98 (NRPN)
        #in that case, the control value of the two preceding control changes are the MSB and LSB of the command index,
        #   and the data of the control 6 command is the value of that message.
        #I think it's supposed to also be able to use the second data byte in control 6 as an LSB for the value,
        #   but I'm unable to test that with this keyboard.
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
                                inputRouting.bindCommand('midi', 'note', 'button',
                                                         (self.inputDevicesMidiNames[deviceIndex], channel, key))
                        else:
                            state = command == eventNoteOn and event[2]>0 #1 for noteOn, 0 for noteOff, velocity 0 is always off
                            for bind in Settings.commandBinds['midi']['note']:
                                if (checkInputValidity(bind) and bind.inputNumber == key):
                                    bind.midiDeviceLast=self.inputDevicesMidiNames[deviceIndex]
                                    bind.midiChannelLast=channel
                                    bind.callCommand(state)

                    elif (command== eventControlChange):
                        control = event[1]
                        if (self.SettingsMenu):
                            if (inputRouting.settingsListenForInput != None):
                                inputRouting.bindCommand('midi', 'control', 'analog',
                                                         (self.inputDevicesMidiNames[deviceIndex], channel, control,
                                                          bindables.thresholdDefaultMidiCC))
                        else:
                            value = event[2]/127 #map to 0-1
                            for bind in Settings.commandBinds['midi']['control']:
                                if (checkInputValidity(bind) and bind.inputNumber == control):

                                    bind.midiDeviceLast=self.inputDevicesMidiNames[deviceIndex]
                                    bind.midiChannelLast=channel

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
        #self.window.update_idletasks()
        self.window.update()
        if (self.SettingsMenu):
            #self.SettingsMenu.update_idletasks()
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
                    self.GetCameraConfig(Camera.selectedNum)

            self.shell.checkResponses()
        
        self.updateDirectValues()

#start the actual program
if __name__ == '__main__':

    if (not hasattr(sys, '_MEIPASS')):
        #in the dev environment, let exceptions happen normally
        print('\n~~~~~ running in dev environment ~~~~~\n\n')
        programMain = CameraController()
        while True:
            programMain.main()
    else:
        #in the bundled exe:
        #   * catch all exceptions
        #   * write them to the console and a log file
        #   * exit properly so pyinstaller can clean up temp files
        programMain = CameraController()
        while True:
            try:
                programMain.main()
            except tk.TclError:
                sys.exit('Window closed, quitting')
            except:
                debug.writeErrorLog()
                sys.exit('Error log written, quitting')