
from helpers import *
from configparser import ConfigParser
from copy import deepcopy
from Bindings import *
import debug
from UI import *

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
        Settings.building=True
    def buildBindingsFrame(freshFrame=True):
        if (freshFrame):
            controller.current.SettingsMenu.bindingsList = ScrollFrame(controller.current.SettingsMenu, maxHeight=400)
            UISettingsProxy.changeMade=Settings.changeMade
            UISettingsProxy.commandBinds=Settings.commandBinds
            UISettingsProxy.inputRoutingBindListen=inputRouting.bindListen
        Settings.building=True
        Settings.tempBinds=[]
        i=0
        categoryFrame=None
        categoryEnd=None
        for key in bindables.index:
            if (key.startswith(bindables.bindingCategory)):
                categoryEnd=bindables.index[key]
                title=key[len(bindables.bindingCategory):]
                categoryFrame=ToggleFrame(controller.current.SettingsMenu.bindingsList.contents, title=title, keepTitle=False, buttonShowTitle=title,
                                            buttonHideTitle='collapse', togglePin='left', contentPadx=(30,3),
                                            relief='groove', borderwidth=2)
                categoryFrame.pack(fill='x', expand=True)
                categoryFrame.conflictIcon=tk.Label(categoryFrame.Titlebar)
                categoryFrame.conflictIcon.pack(side='left', before=categoryFrame.expandButton)
                categoryFrame=categoryFrame.contentFrame
                if (key == bindables.bindingPresets):
                    def addNewPreset(frame):
                        newPanel=ControlBindPresetPanel(frame, bindables.bindingPresetsPrefix+'unnamed',
                                                        bindables.index[key], 'unnamed', Settings.tempBinds,
                                                        newBinding=True)
                        newPanel.categoryFrame=categoryFrame
                        newPanel.pack(fill='x', expand=True)
                        Settings.tempBinds.append(newPanel)

                    panelSide=tk.Frame(categoryFrame)
                    panelSide.pack(side='left', fill='y')
                    panelBody=tk.Frame(categoryFrame)
                    panelBody.pack(side='left', fill='x')
                    panelBody.root=categoryFrame.root
                    tk.Button(panelSide, text='+', command=lambda frame=panelBody: addNewPreset(frame)).pack()

                    for pkey in bindables.bindablePresets:
                        Settings.tempBinds.append(ControlBindPresetPanel(panelBody, bindables.bindingPresetsPrefix+pkey,
                                                                bindables.index[key], pkey, Settings.tempBinds))
                        Settings.tempBinds[i].categoryFrame=categoryFrame
                        Settings.tempBinds[i].pack(fill='x', expand=True)
                        i+=1
                    categoryFrame=None
                    categoryEnd=None
            else:
                if(categoryFrame):
                    newPanel=ControlBindPanel(categoryFrame, key, bindables.index[key])
                    newPanel.categoryFrame=categoryFrame
                    if (key==categoryEnd):
                        categoryEnd=categoryFrame=None
                else:
                    newPanel=ControlBindPanel(controller.current.SettingsMenu.bindingsList.contents, key, bindables.index[key])
                Settings.tempBinds.append(newPanel)
                Settings.tempBinds[i].pack(fill='x', expand=True)
                i+=1
        Settings.comparisonString=Settings.generateBindingString()
        Settings.building=False
    def changeMade(changedBinding, removed=False):
        if (Settings.unsavedChangesWarning and not Settings.building):
            if (removed): bindingString=Settings.generateBindingString(ignore=changedBinding)
            else: bindingString=Settings.generateBindingString()
            print(bindingString)
            if (bindingString !=Settings.comparisonString):
                Settings.unsavedChanges=True
                Settings.unsavedChangesWarning.pack(side='right')
                
            else:
                Settings.unsavedChanges=False
                Settings.unsavedChangesWarning.forget()
            for commandFrame in Settings.tempBinds:
                for binding in commandFrame.BindingList.winfo_children():
                    Settings.bindingConflicts=binding.checkConflict(changedBinding, removed=removed)
            if (Settings.bindingConflicts):
                Settings.saveButton.config(text='conflicting bindings!', state='disabled')
            else:
                Settings.saveButton.config(text='save', state='normal')


    def toggleVerboseDebugPrints():
        Settings.config['Startup']['PrintVerbose']=str(debug.printVerbose.get())
        Settings.SaveConfig()

    def toggleMuteCodecPrints():
        Settings.config['Startup']['MuteCodecResponse']=str(debug.muteCodecResponse.get())
        Settings.SaveConfig()

    def resetBindingsButton():
        confirmReset=messagebox.askokcancel('Reset bindings', 'Reset bindings to defaults?')
        if (confirmReset):
            Settings.resetBindings()

    def resetBindings():
        for child in controller.current.SettingsMenu.bindingsList.contents.winfo_children():
            child.destroy()
        Settings.SaveBindings(bindingString=Settings.Defaults['Startup']['Bindings'])
        Settings.buildBindingsFrame(freshFrame=False)

    def SaveBindings(bindingString=None):
        Settings.saveButton.focus_set() #make sure we focus this widget first, calling focusout on currently focused widget
        if (not bindingString): bindingString=Settings.generateBindingString()
        Settings.parseBindings(bindingString)
        Settings.unsavedChangesWarning.forget()
        Settings.unsavedChanges=False
        Settings.comparisonString=bindingString
        Settings.config['Startup']['Bindings'] = bindingString
        Settings.SaveConfig()

    def generateBindingString(ignore=None):
        bindingString = ''
        for command in Settings.tempBinds:
            for child in command.BindingList.winfo_children():
                if (child != ignore):
                    output = child.makeOutput(command.bindableName)
                    if (output):
                        bindingString += output+'\n'
        return bindingString

    def fixBinding(bindingString):
        if bindingString in bindables.iniRename:
            newBindingString = bindables.iniRename[bindingString]
            debug.print('updating old binding "'+bindingString+'" to "'+newBindingString+'"')
            return newBindingString
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
                commandIndex = Settings.fixBinding(segments[0])

                if (commandIndex.startswith(bindables.bindingPresetsPrefix)):
                    presetName=commandIndex[len(bindables.bindingPresetsPrefix):]
                    commandIndex=bindables.bindingPresets
                    if (not presetName in bindables.bindablePresets):
                        bindables.bindablePresets.append(presetName)
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
                    Settings.commandBinds[bindingDevice][bindingSubdevice].append(
                        addBinding(bindingMidi(midiDevice,midiChannel, inputNumber, command, bindingSubdevice, threshold=threshold)))
                elif (bindingDevice=='controller'):
                    if (bindingSubdevice == 'axis'):
                        axisNum, axisType, axisFlip = segments[2:5]
                        if (len(segments)==6): threshold = float(segments[5])
                        else: threshold=None
                        Settings.commandBinds['controller']['axis'][int(axisNum)] = addBinding(
                            bindingControllerAxis(axisType, int(axisFlip), command, threshold=threshold))
                    elif (bindingSubdevice == 'button'):
                        button = segments[2]
                        Settings.commandBinds['controller']['button'][int(button)] = addBinding(
                            bindingControllerButton(command))
                    elif (bindingSubdevice == 'hat'):
                        hatNum, hatDirection = segments[2:]
                        Settings.commandBinds['controller']['hat'][int(hatNum)][int(hatDirection)] = addBinding(
                            bindingControllerButton(command))
        UISettingsProxy.commandBinds=Settings.commandBinds
        for camera in controller.current.cameras:
            if (camera): camera.updateTriggerBinding()
        

class inputRouting():
    settingsListenForInput = None
    def bindCommand(deviceType, deviceSubtype,inputType, contents):
        commandTypeIndex = inputType=='analog' #0 if it's 'button', 1 if it's 'analog'
        if ((commandTypeIndex==1) or inputRouting.settingsListenForInput.commandType[commandTypeIndex]): #TODO: this is a hacky holdover. Rework to a cleaner version of "button can take analog input, analog can't take digital input"
            inputRouting.settingsListenForInput.changeDeviceType(None)
            inputRouting.settingsListenForInput.setDevice(deviceType, deviceSubtype, contents)
            Settings.changeMade(inputRouting.settingsListenForInput)
            inputRouting.bindListenCancel()
    def bindListen(bindingFrame):
        inputRouting.bindListenCancel()
        inputRouting.settingsListenForInput = bindingFrame
        bindingFrame.listenButton.config(relief='sunken')
        controller.current.SettingsMenu.bind('<KeyPress-Escape>', inputRouting.bindListenCancelInput)
        controller.current.SettingsMenu.bind('<Button 1>', inputRouting.bindListenCancelInput)

    def bindListenCancelInput(discard):
        inputRouting.bindListenCancel()
    def bindListenCancel():
        controller.current.SettingsMenu.unbind('<KeyPress-Escape>')
        controller.current.SettingsMenu.unbind('<Button 1>')
        if (inputRouting.settingsListenForInput):
            inputRouting.settingsListenForInput.listenButton.config(relief='raised')
        inputRouting.bindListenCancelSafe()
    def bindListenCancelSafe():
        inputRouting.expectedType=None
        inputRouting.settingsListenForInput = None