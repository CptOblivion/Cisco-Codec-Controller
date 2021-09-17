
from helpers import *
import math
import main
import pygame
import settings as s
import camera
import ui

class _BindingBase_():
    def __init__(self, command):
        self.command=command
        self.bindablePreset=None
    def callCommand(self, state):
        if (self.command):
            if (self.bindablePreset):
                self.command[0](self, state, self.bindablePreset)
            else:
                self.command[0](self, state)
    def triggerFeedback(self, state):
        #placeholder so we can call this function on any binding even if it's not midi
        return None

class BindingMidi(_BindingBase_):
    deviceIn = None
    deviceOut = None
    deviceNamesIn=[]
    deviceNamesOut=[]
    deviceOutIndex=None
    deviceName = None
    deviceNamesClean = []
    activeIns={}
    activeOuts={}

    def refreshDevices(makeDropdown=None, select=True, save=True):
        BindingMidi.deviceName = tk.StringVar(main.current.window)
        #pass in a parent object to makeDropdown to use it
        BindingMidi.deviceNamesIn.clear()
        BindingMidi.deviceNamesOut.clear()
        BindingMidi.deviceNamesClean.clear()
        count=pygame.midi.get_count()
        if (count):
            for i in range(count):
                info = pygame.midi.get_device_info(i)
                name=str(info[1], 'utf-8')
                if (info[2]):
                    BindingMidi.deviceNamesIn.append(name)
                    BindingMidi.deviceNamesClean.append(name)
                    BindingMidi.deviceNamesOut.append(None)
                else:
                    BindingMidi.deviceNamesIn.append(None)
                    BindingMidi.deviceNamesOut.append(name)
            if (s.Settings.config['Startup']['LastMidiDevice'] in BindingMidi.deviceNamesIn):
                BindingMidi.deviceName.set(s.Settings.config['Startup']['LastMidiDevice'])
            else:
                BindingMidi.deviceName.set(BindingMidi.deviceNamesClean[0])
            BindingMidi.selectDevice(BindingMidi.deviceName.get(), select, False)
            if (makeDropdown):
                return tk.OptionMenu(makeDropdown, BindingMidi.deviceName,
                                     *BindingMidi.deviceNamesClean, command=lambda name,
                                     select=select, save=save: BindingMidi.selectDevice(name, select,save))
        if (makeDropdown):
            return  tk.Label(makeDropdown, text='No midi devices')
    def applyFeedback(state):
        if (camera.Camera.selected and camera.Camera.selected.triggerBinding):
            camera.Camera.selected.triggerBinding.triggerFeedback(state)
        for i in range(8):
            if (ui.CameraPresetPanel.lastTriggerBinding[i]):
                ui.CameraPresetPanel.lastTriggerBinding[i].triggerBinding.triggerFeedback(True)
    def selectDevice(name, activate, save):
        num = BindingMidi.deviceNamesIn.index(name)
        s.Settings.config['Startup']['LastMidiDevice'] = name
        if (save):s.Settings.SaveConfig()
        #if (BindingMidi.deviceIn):
        #    print(BindingMidi.deviceIn)
        #    BindingMidi.deviceIn.close()
        #    BindingMidi.deviceIn = None
        #if (BindingMidi.deviceOut):
        #    BindingMidi.clearFeedback()
        #    BindingMidi.deviceOut.close()
        #    BindingMidi.deviceOut=None

        if (activate):
            BindingMidi.clearFeedback()
            if (not name in BindingMidi.activeIns):
                print('adding ', name,' to devices, list is now ',BindingMidi.activeIns)
                BindingMidi.activeIns[name] = pygame.midi.Input(num)
            BindingMidi.deviceIn = BindingMidi.activeIns[name]
            #name = BindingMidi.deviceNamesIn[num]
            if (name in BindingMidi.deviceNamesOut):
                if (not name in BindingMidi.activeOuts):
                    BindingMidi.activeOuts[name] = pygame.midi.Output(
                        BindingMidi.deviceNamesOut.index(name))
                BindingMidi.deviceOut = BindingMidi.activeOuts[name]
                BindingMidi.clearFeedback()
                BindingMidi.applyFeedback(True)

        else: BindingMidi.deviceOut=None
    def __init__(self, midiChannel,inputNumber, command, subdevice, threshold=None):
        _BindingBase_.__init__(self, command)
        #TODO: if channel is None, when this binding is activated store the channel that was used
        self.midiChannel =midiChannel
        #TODO: rename subdevice to inputType
        self.subdevice=subdevice
        if (threshold is None):
            threshold=Bindables.thresholdDefaultMidiCC
        self.threshold=threshold
        self.valueLast={}
        self.inputNumber = inputNumber

    def triggerFeedback(self, state): #state is bool
        if (BindingMidi.deviceOut and self.midiChannel is not None and self.inputNumber is not None):
            if (state): vel = 63
            else: vel=0
            if (self.subdevice=='note'):
                #TODO: catch 'Host Error' for midi control disconnect, run refreshDevices
                BindingMidi.deviceOut.note_on(self.inputNumber, velocity=vel,
                                channel=self.midiChannel)
            else:
                BindingMidi.deviceOut.write_short(0xb0+self.midiChannel,self.inputNumber, vel)
            return self #success
        return None #no dice
    def clearFeedback():
        if (BindingMidi.deviceOut):
            BindingMidi.applyFeedback(False)
            if ('Launchpad Mini' in BindingMidi.deviceName.get()):
                print('clearing')
                BindingMidi.deviceOut.write_short(0xb0, 00,00) #this should clear the pad
                #for i in range(121):
                #    BindingMidi.deviceOut.note_on(i, velocity=0, channel=0)

class BindingControllerButton(_BindingBase_):
    def __init__(self, command):
        _BindingBase_.__init__(self, command)

class BindingControllerAxis(_BindingBase_):
    def __init__(self, type, flip, function, threshold=None):
        _BindingBase_.__init__(self, function)
        self.type=type
        self.flip=flip
        if (threshold is None):
            threshold=Bindables.thresholdDefaultController
        self.threshold=threshold

class Bindables():
    thresholdDefaultController = .2
    thresholdDefaultMidiCC = .1

    PresetWrite=False

    midiIOMapping={}
    
    def _CameraRamp_(value, x, y):
        if (value): main.current.StartMove(main.current.PanSpeed.get()*x,main.current.TiltSpeed.get()*y)
        else: main.current.StopMove(None)
    def buttonPanUL(binding, value):
        Bindables._CameraRamp_(value, -1,1)
    def buttonPanU(binding, value):
        Bindables._CameraRamp_(value, 0,1)
    def buttonPanUR(binding, value):
        Bindables._CameraRamp_(value, 1,1)
    def buttonPanL(binding, value):
        Bindables._CameraRamp_(value, -1,0)
    def buttonPanR(binding, value):
        Bindables._CameraRamp_(value, 1,0)
    def buttonPanDL(binding, value):
        Bindables._CameraRamp_(value, -1,-1)
    def buttonPanD(binding, value):
        Bindables._CameraRamp_(value, 0,-1)
    def buttonPanDR(binding, value):
        Bindables._CameraRamp_(value, 1,-1)
    def bothTriggerAutofocus(binding, value):
        if (main.current.init and value): main.current.TriggerAutofocus()
    def buttonZoomIn(binding, value):
        if (value):
            main.current.ZoomIn(None)
        else:
            main.current.StopZoom(None)
    def buttonZoomOut(binding, value):
        if (value):
            main.current.ZoomOut(None)
        else:
            main.current.StopZoom(None)
    def buttonFocusNear(binding, value):
        if (main.current.init and value): main.current.FocusNear(None)
        else: main.current.StopFocus(None)
    def buttonFocusFar(binding, value):
        if (main.current.init and value): main.current.FocusFar(None)
        else: main.current.StopFocus(None)
    def bothRefreshPosition(binding, value):
        if (main.current.init and value): main.current.UpdateCameraDetails()
    
    def _ProcessAxis_(value):
        flip = 1
        if (value < 0): flip=-1
        deadzone = .13
        value = (max(0,abs(value)-deadzone))/(1-deadzone)*flip
        return value
    def _queueJoystickPan_():
        main.current.StartMove(main.current.joystickPanAxesInt[0], main.current.joystickPanAxesInt[1])
    def _SetJoystickPan_(axis, value):
        value = (abs(value)**2.2)*math.copysign(1,value) #gamma curve on stick
        main.current.joystickPanAxesRaw[axis] = value

        tempVec=[main.current.joystickPanAxesRaw[0],main.current.joystickPanAxesRaw[1]]
        tempVec =[int(tempVec[0] * 15), int(tempVec[1] * 15)]

        if (main.current.joystickPanAxesInt != tempVec):
            main.current.joystickPanAxesInt = tempVec
            if (main.current.joystickPanAxesInt == [0,0]): main.current.QueueInput(lambda: main.current.StopMove(None))
            else: main.current.QueueInput(Bindables._queueJoystickPan_)

    def analogPTSpeed(binding, value):
        main.current.PanSpeed.set(int(value*14+1))
        main.current.TiltSpeed.set(int(value*14+1))
    def analogSetZSpeed(binding, value):
        main.current.ZoomSpeed.set(int(value*14+1))
    def analogPanDirect(binding, value):
        main.current.directControls['pan'].set(value)
    def analogTiltDirect(binding, value):
        main.current.directControls['tilt'].set(value)
    def analogZoomDirect(binding, value):
        main.current.directControls['zoom'].set(value)
    def analogFocusDirect(binding, value):
        main.current.directControls['focus'].set(value)
    def analogRampZoom(binding, value):
        if (value==0):
            main.current.QueueInput(lambda: main.current.StopZoom(None))
        else:
            if (value > 0): value = int(math.ceil(value*15))
            else: value = int(math.floor(value*15))
            main.current.rampZoomValue = value
            main.current.QueueInput(lambda: main.current.startZoom(main.current.rampZoomValue))
    def analogRampFocus(binding, value):
        value = value*2-1
        if (value==0):
            main.current.QueueInput(lambda: main.current.StopFocus(None))
        else:
            value=int(math.copysign(1,value))
            main.current.rampFocusValue = value
            main.current.QueueInput(lambda: main.current.startFocus(main.current.rampFocusValue))
    def analogRampPan(binding, value):
        Bindables._SetJoystickPan_(0,value)
    def analogRampTilt(binding, value):
        Bindables._SetJoystickPan_(1,value)
    def bothDebugOutputValue(binding, value):
        print(value)

    def _selectCamera_(value):
        main.current.cameras[value].select()
    def selectCamera1(binding, value):
        Bindables._selectCamera_(1)
    def selectCamera2(binding, value):
        Bindables._selectCamera_(2)
    def selectCamera3(binding, value):
        Bindables._selectCamera_(3)
    def selectCamera4(binding, value):
        Bindables._selectCamera_(4)
    def selectCamera5(binding, value):
        Bindables._selectCamera_(5)
    def selectCamera6(binding, value):
        Bindables._selectCamera_(6)
    def selectCamera7(binding, value):
        Bindables._selectCamera_(7)

    def _setBrightness(camNum, val):
        #print(val*30)
        val = int(val*30)+1
        if (main.current.cameras[camNum].brightnessValue.get() != val):
            main.current.SetBrightnessLevel(val, camNum)
    def brightnessCamera1(binding, value):
        Bindables._setBrightness(1, value)
    def brightnessCamera2(binding, value):
        Bindables._setBrightness(2, value)
    def brightnessCamera3(binding, value):
        Bindables._setBrightness(3, value)
    def brightnessCamera4(binding, value):
        Bindables._setBrightness(4, value)
    def brightnessCamera5(binding, value):
        Bindables._setBrightness(5, value)
    def brightnessCamera6(binding, value):
        Bindables._setBrightness(6, value)
    def brightnessCamera7(binding, value):
        Bindables._setBrightness(7, value)

    def setPresetWrite(binding, value):
        Bindables.PresetWrite=bool(value)
        main.current.TogglePresetEdit.SetState(Bindables.PresetWrite)

    #def _getMidiOutput(binding):
    #    if (isinstance(binding, bindingMidi)):
    #        return binding.getOutput()
    #    return (None,None)
    def activatePreset(binding, buttonValue, presetName):
        if (buttonValue):
            triggered = False
            camNum=-1
            for preset in main.current.CamerasPresets:
                if (preset and preset.isValid() and preset.name==presetName):
                    camNum=0
                    if (Bindables.PresetWrite):
                        preset.saveToPreset()
                    else:
                        preset.activatePreset()
                    triggered=True
                    break
            if (not triggered):
                for preset in main.current.CameraPresets:
                    if (preset and preset.isValid() and preset.name==presetName):
                        camNum=preset.cameraId
                        if (Bindables.PresetWrite):
                            preset.saveToPreset()
                        else:
                            preset.activatePreset()
                        triggered=True
                        break

    
    bindablePresets=[]

    #append this to the beginning of a key to mark that entry as a category rather than a proper entry
    #the contents of the dictionary entry should be the name of the last function in the category
    bindingCategory = '__CATEGORY__' 


    bindingPresets=bindingCategory+'activate presets' #special category entry for camera presets (processed uniquely)
    bindingPresetsPrefix='preset_' #actual preset bindings as they appear in the ini start with this
    index = {
            bindingCategory+'move digital':'focus_far', #collapsible categories contain all entries up to (and including) the key they contain
                'move_left':(buttonPanL, 'button'),
                'move_right':(buttonPanR, 'button'),
                'move_up':(buttonPanU, 'button'),
                'move_down':(buttonPanD, 'button'),
                'move_left_up':(buttonPanUL, 'button'),
                'move_right_up':(buttonPanUR, 'button'),
                'move_left_down':(buttonPanDL, 'button'),
                'move_right_down':(buttonPanDR, 'button'),
                'zoom_in':(buttonZoomIn, 'button'),
                'zoom_out':(buttonZoomOut, 'button'),
                'focus_near':(buttonFocusNear, 'button'),
                'focus_far':(buttonFocusFar, 'button'),
            bindingCategory+'move analog':'ramp_focus',
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
            'refresh_position': (bothRefreshPosition, 'both'),
            bindingCategory+'select camera':'select_camera_7',
                'select_camera_1': (selectCamera1, 'button'),
                'select_camera_2': (selectCamera2, 'button'),
                'select_camera_3': (selectCamera3, 'button'),
                'select_camera_4': (selectCamera4, 'button'),
                'select_camera_5': (selectCamera5, 'button'),
                'select_camera_6': (selectCamera6, 'button'),
                'select_camera_7': (selectCamera7, 'button'),
            'overwrite_preset':(setPresetWrite, 'button'),
            bindingPresets:(activatePreset,'button'),
            bindingCategory+'brightness':'brightnessCamera7',
                'brightness_Camera_1':(brightnessCamera1, 'analog'),
                'brightness_Camera_2':(brightnessCamera2, 'analog'),
                'brightness_Camera_3':(brightnessCamera3, 'analog'),
                'brightness_Camera_4':(brightnessCamera4, 'analog'),
                'brightness_Camera_5':(brightnessCamera5, 'analog'),
                'brightness_Camera_6':(brightnessCamera6, 'analog'),
                'brightness_Camera_7':(brightnessCamera7, 'analog'),
            'pan_tilt_speed':(analogPTSpeed, 'analog'),
            'zoom_speed':(analogSetZSpeed, 'analog'),
            bindingCategory+'debug':'debugOutputValue',
                'debugOutputValueButton':(bothDebugOutputValue, 'button'),
                'debugOutputValue':(bothDebugOutputValue, 'both'),
            }
    iniRename = {
        'brightnessCamera1':'brightness_Camera_1',
        'brightnessCamera2':'brightness_Camera_2',
        'brightnessCamera3':'brightness_Camera_3',
        'brightnessCamera4':'brightness_Camera_4',
        'brightnessCamera5':'brightness_Camera_5',
        'brightnessCamera6':'brightness_Camera_6',
        'brightnessCamera7':'brightness_Camera_7'}
