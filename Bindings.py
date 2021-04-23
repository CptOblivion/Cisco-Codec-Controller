from Helpers import *

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
        if (value): controller.current.StartMove(controller.current.PanSpeed.get()*x,controller.current.TiltSpeed.get()*y)
        else: controller.current.StopMove(None)
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
        if (controller.current.init and value): controller.current.TriggerAutofocus()
    def buttonFocusNear(value):
        if (controller.current.init and value): controller.current.FocusNear(None)
        else: controller.current.StopFocus(None)
    def buttonFocusFar(value):
        if (controller.current.init and value): controller.current.FocusFar(None)
        else: controller.current.StopFocus(None)
    def bothRefreshPosition(value):
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

    def analogPTSpeed(value):
        controller.current.PanSpeed.set(int(value*14+1))
        controller.current.TiltSpeed.set(int(value*14+1))
    def analogSetZSpeed(value):
        controller.current.ZoomSpeed.set(int(value*14+1))
    def analogPanDirect(value):
        controller.current.directControls['pan'].set(value)
    def analogTiltDirect(value):
        controller.current.directControls['tilt'].set(value)
    def analogZoomDirect(value):
        controller.current.directControls['zoom'].set(value)
    def analogFocusDirect(value):
        controller.current.directControls['focus'].set(value)
    def analogRampZoom(value):
        if (value==0):
            controller.current.QueueInput(lambda: controller.current.StopZoom(None))
        else:
            if (value > 0): value = int(math.ceil(value*15))
            else: value = int(math.floor(value*15))
            controller.current.rampZoomValue = value
            controller.current.QueueInput(lambda: controller.current.startZoom(controller.current.rampZoomValue))
    def analogRampFocus(value):
        value = value*2-1
        if (value==0):
            controller.current.QueueInput(lambda: controller.current.StopFocus(None))
        else:
            value=int(math.copysign(1,value))
            controller.current.rampFocusValue = value
            controller.current.QueueInput(lambda: controller.current.startFocus(controller.current.rampFocusValue))
    def analogRampPan(value):
        bindables._SetJoystickPan_(0,value)
    def analogRampTilt(value):
        bindables._SetJoystickPan_(1,value)
    def bothDebugOutputValue(value):
        print(value)

    def _selectCamera_(value):
        controller.current.cameras[value].select()
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
            for preset in controller.current.CameraPresets:
                if (preset and preset.isValid() and preset.name==presetName):
                    preset.activatePreset()
                
                    #TODO: figure out of it's preferable to run the whole loop and trigger every matching preset, or just the first match
                    #break
    
    bindablePresets=[]

    bindingCategory = '__CATEGORY__' #append this to the beginning of a key to mark that entry as a category rather than a proper entry
    bindingPresets=bindingCategory+'activate presets' #special category entry for camera presets (processed uniquely)
    bindingPresetsPrefix='preset_' #actual preset bindings saved in the ini start with this
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