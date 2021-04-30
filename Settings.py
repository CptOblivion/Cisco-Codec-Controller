from Helpers import *
from configparser import ConfigParser
from copy import deepcopy
from Bindings import *
from Debug import *

class Settings():
    iniFilename='CameraController_'+VersionNumber+'.ini' 
    CustomCommandName="Add custom commands below this line (just make sure they're tabbed in a level)"
    Defaults = {
        'Startup':{
            'IPADDRESS': '192.168.1.27',
            'USERNAME':'admin',
            'PASSWORD':'',
            'MuteCodecResponse':'0',
            'printVerbose':'0',
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
    def initializeSettings():
        debug.printVerbose=tk.IntVar()
        debug.printVerbose.set(int(Settings.config['Startup']['PrintVerbose']))
        debug.muteCodecResponse=tk.IntVar()
        debug.muteCodecResponse.set(int(Settings.config['Startup']['MuteCodecResponse']))

        Settings.commandBinds={}
        Settings.commandBindsEmpty={
            'midi':{
                'note': [], #note binds are deviceName, channel, note
                'control':[]}, #control binds are deviceName, channel, CC#
            'controller':{
                'button':[], #button binds are buttonNum
                'axis':[], #axis binds are axisNum, axisType, flip
                'hat':[]}} #hat bindings are hatNum, hatDirection

        for i in range(20): #space for 20 buttons, 20 axes
            Settings.commandBindsEmpty['controller']['button'].append(None)
            Settings.commandBindsEmpty['controller']['axis'].append(None)
        for i in range(4): #4 hats (8 directions each)
            Settings.commandBindsEmpty['controller']['hat'].append([None,None,None,None,None,None,None,None])

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
        Settings.initializeSettings()

    def SaveConfig():
        with open(Settings.iniFilename, 'w') as configfile:
            Settings.config.write(configfile)
            configfile.close()

    def openSettings():
        Settings.unsavedChanges=False
        Settings.bindingConflicts=False
        Settings.unsavedChangesWarning=None
        Settings.saveButton=None
        Settings.comparisonString=None
    def changeMade():
        if (Settings.unsavedChangesWarning):
            if (Settings.SaveBindings(save=False) !=Settings.comparisonString):
                Settings.unsavedChanges=True
                Settings.unsavedChangesWarning.pack(side='right')
                #TODO: check for conflicting bindings
                #if (conflicting bindings check not written yet):
                #   Settings.saveButton.config(text='conflicting bindings!', state='disabled')
                #   Settings.bindingConflictsWarning.pack(side='right')
                #else:
                #   Settings.bindingConflictsWarning.forget()
                #   Settings.saveButton.config(text='save', state='normal')
            else:
                Settings.unsavedChanges=False
                Settings.unsavedChangesWarning.forget()


    def toggleVerboseDebugPrints():
        Settings.config['Startup']['PrintVerbose']=str(debug.printVerbose.get())
        Settings.SaveConfig()
    def toggleMuteCodecPrints():
        Settings.config['Startup']['MuteCodecResponse']=str(debug.muteCodecResponse.get())
        Settings.SaveConfig()
    def SaveBindings(save=True):
        if (save):
            Settings.saveButton.focus_set() #make sure we focus this widget first, calling focusout on currently focused widget

        bindingString = ''
        for command in Settings.tempBinds:
            for child in command.BindingList.winfo_children():
                output = child.makeOutput(command.bindableName)
                if (output):
                    bindingString += output+'\n'
        if (save):
            Settings.parseBindings(bindingString)
            Settings.config['Startup']['Bindings'] = bindingString
            Settings.SaveConfig()
        return bindingString
    def parseBindings(bindingString):
        Settings.commandBinds = deepcopy(Settings.commandBindsEmpty) #maybe unnecessary to deep copy? The source is like six entries so it's fine either way
        lines=bindingString.splitlines()
        bindables.bindablePresets=[]
        for line in lines:
            if line:
                presetName=None

                segments=line.split(',')
                debug.print(line)
                commandIndex = segments[0]

                if (commandIndex.startswith(bindables.bindingPresetsPrefix)):
                    presetName=commandIndex[len(bindables.bindingPresetsPrefix):]
                    commandIndex=bindables.bindingPresets
                    command=(lambda value, presetName=presetName: bindables.activatePreset(value,presetName),
                             bindables.index[bindables.bindingPresets][1])
                    if (not presetName in bindables.bindablePresets):
                        bindables.bindablePresets.append(presetName)
                else:
                    command=bindables.index[commandIndex]

                def addBinding(binding): #TODO: move to root of class
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
                    Settings.commandBinds[bindingDevice][bindingSubdevice].append(addBinding(bindingMidi(midiDevice,midiChannel, inputNumber, command, threshold=threshold)))
                elif (bindingDevice=='controller'):
                    if (bindingSubdevice == 'axis'):
                        axisNum, axisType, axisFlip = segments[2:5]
                        if (len(segments)==6): threshold = float(segments[5])
                        else: threshold=None
                        Settings.commandBinds['controller']['axis'][int(axisNum)] = addBinding(bindingControllerAxis(axisType, int(axisFlip), command, threshold=threshold))
                    elif (bindingSubdevice == 'button'):
                        button = segments[2]
                        Settings.commandBinds['controller']['button'][int(button)] = addBinding(bindingControllerButton(command))
                    elif (bindingSubdevice == 'hat'):
                        hatNum, hatDirection = segments[2:]
                        Settings.commandBinds['controller']['hat'][int(hatNum)][int(hatDirection)] = addBinding(bindingControllerButton(command))
        
        if (hasattr(Settings, 'unsavedChangesWarning')): Settings.unsavedChangesWarning.forget()

class inputRouting():
    settingsListenForInput = None
    def bindCommand(deviceType, deviceSubtype,inputType, contents):
        commandTypeIndex = inputType=='analog' #0 if it's 'button', 1 if it's 'analog'
        if ((commandTypeIndex==1) or inputRouting.settingsListenForInput.commandType[commandTypeIndex]): #TODO: this is a hacky holdover. Rework to a cleaner version of "button can take analog input, analog can't take digital input"
            inputRouting.settingsListenForInput.changeDeviceType(None)
            inputRouting.settingsListenForInput.setDevice(deviceType, deviceSubtype, contents)
            inputRouting.bindListenCancel()
            Settings.changeMade()
    def bindListen(bindingFrame):
        #TODO: bind 'esc' to bindListenCancel() (which should, in turn, unbind esc)
        #TODO: also bind clicking anywhere to cancel
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