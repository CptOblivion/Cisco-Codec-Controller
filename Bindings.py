from Helpers import *
import math

class _bindingBase_():
    def __init__(self, command):
        self.command=command
        self.bindablePreset=None
    def callCommand(self, state):
        if (self.command):
            if (self.bindablePreset):
                self.command[0](self, state, self.bindablePreset)
            else:
                self.command[0](self, state)

class bindingMidi(_bindingBase_):
    def __init__(self, midiDevice, midiChannel,inputNumber, command, subdevice, threshold=None):
        _bindingBase_.__init__(self, command)
        #TODO: mark if note or CC
        #TODO: if channel is None, when this binding is activated store the channel that was used
        #TODO: same with device
        self.midiDevice=self.midiDeviceLast=midiDevice
        self.midiChannel = self.midiChannelLast=midiChannel
        self.subdevice=subdevice
        if (threshold is None):
            threshold=bindables.thresholdDefaultMidiCC
        self.threshold=threshold
        self.valueLast={}
        
        self.inputNumber = inputNumber
    def getMessageDetails(self):
        device=self.midiDevice
        channel=self.midiChannel
        if (self.midiDevice is None): device=self.midiDeviceLast
        if (self.midiChannel is None): channel=self.midiChannelLast
        return(device,channel)

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

    PresetWrite=False

    #TODO: this should be a list corresponding to cameras
    lastPresetBinding=[None, None, None, None, None, None, None, None]

    midiIOMapping={}
    
    def _CameraRamp_(value, x, y):
        if (value): controller.current.StartMove(controller.current.PanSpeed.get()*x,controller.current.TiltSpeed.get()*y)
        else: controller.current.StopMove(None)
    def buttonPanUL(binding, value):
        bindables._CameraRamp_(value, -1,1)
    def buttonPanU(binding, value):
        bindables._CameraRamp_(value, 0,1)
    def buttonPanUR(binding, value):
        bindables._CameraRamp_(value, 1,1)
    def buttonPanL(binding, value):
        bindables._CameraRamp_(value, -1,0)
    def buttonPanR(binding, value):
        bindables._CameraRamp_(value, 1,0)
    def buttonPanDL(binding, value):
        bindables._CameraRamp_(value, -1,-1)
    def buttonPanD(binding, value):
        bindables._CameraRamp_(value, 0,-1)
    def buttonPanDR(binding, value):
        bindables._CameraRamp_(value, 1,-1)
    def bothTriggerAutofocus(binding, value):
        if (controller.current.init and value): controller.current.TriggerAutofocus()
    def buttonZoomIn(binding, value):
        if (value):
            controller.current.ZoomIn(None)
        else:
            controller.current.StopZoom(None)
    def buttonZoomOut(binding, value):
        if (value):
            controller.current.ZoomOut(None)
        else:
            controller.current.StopZoom(None)
    def buttonFocusNear(binding, value):
        if (controller.current.init and value): controller.current.FocusNear(None)
        else: controller.current.StopFocus(None)
    def buttonFocusFar(binding, value):
        if (controller.current.init and value): controller.current.FocusFar(None)
        else: controller.current.StopFocus(None)
    def bothRefreshPosition(binding, value):
        if (controller.current.init and value): controller.current.UpdateCameraDetails()
    
    def _ProcessAxis_(value):
        flip = 1
        if (value < 0): flip=-1
        deadzone = .13
        value = (max(0,abs(value)-deadzone))/(1-deadzone)*flip
        return value
    def _queueJoystickPan_():
        controller.current.StartMove(controller.current.joystickPanAxesInt[0], controller.current.joystickPanAxesInt[1])
    def _SetJoystickPan_(axis, value):
        value = (abs(value)**2.2)*math.copysign(1,value) #gamma curve on stick
        controller.current.joystickPanAxesRaw[axis] = value

        tempVec=[controller.current.joystickPanAxesRaw[0],controller.current.joystickPanAxesRaw[1]]
        tempVec =[int(tempVec[0] * 15), int(tempVec[1] * 15)]

        if (controller.current.joystickPanAxesInt != tempVec):
            controller.current.joystickPanAxesInt = tempVec
            if (controller.current.joystickPanAxesInt == [0,0]): controller.current.QueueInput(lambda: controller.current.StopMove(None))
            else: controller.current.QueueInput(bindables._queueJoystickPan_)

    def analogPTSpeed(binding, value):
        controller.current.PanSpeed.set(int(value*14+1))
        controller.current.TiltSpeed.set(int(value*14+1))
    def analogSetZSpeed(binding, value):
        controller.current.ZoomSpeed.set(int(value*14+1))
    def analogPanDirect(binding, value):
        controller.current.directControls['pan'].set(value)
    def analogTiltDirect(binding, value):
        controller.current.directControls['tilt'].set(value)
    def analogZoomDirect(binding, value):
        controller.current.directControls['zoom'].set(value)
    def analogFocusDirect(binding, value):
        controller.current.directControls['focus'].set(value)
    def analogRampZoom(binding, value):
        if (value==0):
            controller.current.QueueInput(lambda: controller.current.StopZoom(None))
        else:
            if (value > 0): value = int(math.ceil(value*15))
            else: value = int(math.floor(value*15))
            controller.current.rampZoomValue = value
            controller.current.QueueInput(lambda: controller.current.startZoom(controller.current.rampZoomValue))
    def analogRampFocus(binding, value):
        value = value*2-1
        if (value==0):
            controller.current.QueueInput(lambda: controller.current.StopFocus(None))
        else:
            value=int(math.copysign(1,value))
            controller.current.rampFocusValue = value
            controller.current.QueueInput(lambda: controller.current.startFocus(controller.current.rampFocusValue))
    def analogRampPan(binding, value):
        bindables._SetJoystickPan_(0,value)
    def analogRampTilt(binding, value):
        bindables._SetJoystickPan_(1,value)
    def bothDebugOutputValue(binding, value):
        print(value)

    def _selectCamera_(value):
        controller.current.cameras[value].select()
    def selectCamera1(binding, value):
        bindables._selectCamera_(1)
    def selectCamera2(binding, value):
        bindables._selectCamera_(2)
    def selectCamera3(binding, value):
        bindables._selectCamera_(3)
    def selectCamera4(binding, value):
        bindables._selectCamera_(4)
    def selectCamera5(binding, value):
        bindables._selectCamera_(5)
    def selectCamera6(binding, value):
        bindables._selectCamera_(6)
    def selectCamera7(binding, value):
        bindables._selectCamera_(7)

    def _setBrightness(camNum, val):
        #print(val*30)
        val = int(val*30)+1
        if (controller.current.cameras[camNum].brightnessValue.get() != val):
            controller.current.SetBrightnessLevel(val, camNum)
    def brightnessCamera1(binding, value):
        bindables._setBrightness(1, value)
    def brightnessCamera2(binding, value):
        bindables._setBrightness(2, value)
    def brightnessCamera3(binding, value):
        bindables._setBrightness(3, value)
    def brightnessCamera4(binding, value):
        bindables._setBrightness(4, value)
    def brightnessCamera5(binding, value):
        bindables._setBrightness(5, value)
    def brightnessCamera6(binding, value):
        bindables._setBrightness(6, value)
    def brightnessCamera7(binding, value):
        bindables._setBrightness(7, value)

    def setPresetWrite(binding, value):
        bindables.PresetWrite=bool(value)
        controller.current.TogglePresetEdit.SetState(bindables.PresetWrite)

    def _getMidiOutput(binding):
        if (isinstance(binding, bindingMidi)):
            device=binding.getMessageDetails()
            if (device):
                deviceIndex=controller.current.inputDevicesMidiNames.index(device[0])
                outNum=bindables.midiIOMapping[deviceIndex]
                outDevice=controller.current.outputDevicesMidis[outNum]
                return (outDevice, device[1])
        return (None,None)
    def activatePreset(binding, buttonValue, presetName):
        if (buttonValue):
            triggered = False
            camNum=-1
            for preset in controller.current.CamerasPresets:
                if (preset and preset.isValid() and preset.name==presetName):
                    camNum=0
                    if (bindables.PresetWrite):
                        preset.saveToPreset()
                    else:
                        preset.activatePreset()
                    triggered=True
                    break
            if (not triggered):
                for preset in controller.current.CameraPresets:
                    if (preset and preset.isValid() and preset.name==presetName):
                        camNum=preset.cameraId
                        if (bindables.PresetWrite):
                            preset.saveToPreset()
                        else:
                            preset.activatePreset()
                        triggered=True
                        break
            if (triggered):
                if (bindables.lastPresetBinding[camNum]):
                    device=bindables._getMidiOutput(bindables.lastPresetBinding[camNum])
                    if (device[0]):
                        if (binding.subdevice=='note'):
                            device[0].note_on(bindables.lastPresetBinding[camNum].inputNumber,
                                            channel=device[1], velocity=0)
                        else:
                            device[0].write_short(0xb0+device[1],bindables.lastPresetBinding[camNum].inputNumber, 0)
                
                bindables.lastPresetBinding[camNum]=binding
                if (isinstance(binding, bindingMidi)):
                    device=bindables._getMidiOutput(binding)
                    if (device[0]):
                        if (binding.subdevice=='note'):
                            device[0].note_on(binding.inputNumber, velocity=63,
                                           channel=device[1])
                        else:
                            device[0].write_short(0xb0+device[1],binding.inputNumber, 63)

    
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