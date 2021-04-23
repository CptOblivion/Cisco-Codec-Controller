from Helpers import *
from Bindings import *

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
    def __init__(self, parent, title='frame', keepTitle=False,
                 buttonShowTitle='Show Frame', buttonHideTitle='Hide Frame',
                 togglePin='right', toggleCommand = None, contentPadx=3,
                 *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)

        self.open = tk.IntVar()
        self.open.set(0)

        self.ButtonShowText = buttonShowTitle
        self.ButtonHideText = buttonHideTitle
        self.KeepTitle=keepTitle

        self.Titlebar = tk.Frame(self)
        self.Titlebar.pack(fill='x', ipady=2, ipadx=2, padx=3, pady=3)
        #togglePin should be one of the widget.pack() sides
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
    def __init__(self, parent, maxHeight=0, frameConfigureCommand=None, *args, **options):
        #TODO: optional horizontal scrollbar
        tk.Frame.__init__(self, parent, *args, **options)
        self.config(relief='groove', borderwidth = 2)
        self.maxHeight=maxHeight #TODO: implement this

        self.bind('<Enter>', self.bindMouseWheel)
        self.bind('<Leave>', self.unbindMouseWheel)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, width=0, height=0)
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
        self.canvas.configure(width=self.contents.winfo_reqwidth())
        self.canvas.configure(scrollregion = self.canvas.bbox('all'))
        if (self.frameConfigureCommand): self.frameConfigureCommand(self)
    def onCanvasConfigure(self, event):
        #TODO: see above about borderwidth and highlightthickness
        width=event.width #-borderwidth*2 - highlightthickness*2
        self.canvas.itemconfig(self.canvasFrame,  width=width)
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
            #convert string into a valid midi channel (int or 'any')
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
            for binding in controller.current.commandBinds['midi']['note']:
                if (compareCommand()):
                    self.AddBinding(deviceType='midi', deviceSubtype='note', contents=(binding.midiDevice,binding.midiChannel,binding.inputNumber))
            b=0
            for binding in controller.current.commandBinds['controller']['button']:
                if (compareCommand()):
                    self.AddBinding(deviceType='controller', deviceSubtype='button', contents=[b])
                b+=1
            h = 0
            for hat in controller.current.commandBinds['controller']['hat']:
                direction=0
                for binding in hat:
                    if (compareCommand()):
                        self.AddBinding(deviceType='controller', deviceSubtype='hat', contents=[h, direction])
                    direction+=1
                h+=1

        #analog inputs can always be bound to button commands, as long as the threshold is properly set
        for binding in controller.current.commandBinds['midi']['control']:
            if (compareCommand()):
                self.AddBinding(deviceType='midi', deviceSubtype='control', contents=(binding.midiDevice,binding.midiChannel,binding.inputNumber, binding.threshold))
        a=0
        for binding in controller.current.commandBinds['controller']['axis']:
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

class CameraPresetPanel(tk.Frame):
    controller=None
    def __init__(self, parent, index, *args, **options):
        tk.Frame.__init__(self, parent, relief='ridge', borderwidth=2, *args, **options)
        self.index = index

        self.presetEntry=controller.current.CameraPresets[index]

        self.frameName = tk.Frame(self)
        
        self.presetIdLabel = tk.Label(self.frameName)

        validation=self.register(self.renamePreset)
        self.presetNameLabel = tk.Label(self.frameName, text=controller.current.CameraPresets[self.index].name)

        self.presetNameEntry = tk.Entry(self.frameName, validate='key', validatecommand=(validation, '%S'))
        self.presetNameEntry.insert(0,controller.current.CameraPresets[self.index].name)
        self.presetNameEntry.bind('<Return>', lambda event: self.focus())
        self.presetNameEntry.bind('<FocusOut>', self.renamePreset)

        self.presetIdLabel.pack(side='left')
        #self.presetNameLabel.pack(side='left')

        self.frameMain = tk.Frame(self)
        self.cameraId = tk.Label(self.frameMain)
        self.activateButton = tk.Button(self.frameMain, text='activate', command=self.activatePreset)

        #self.cameraId.pack(side='left')
        self.activateButton.pack(side='left')

        self.frameButtons = tk.Frame(self)

        tk.Button(self.frameButtons, text='overwrite', command=self.saveToPreset).pack(side='left')
        tk.Button(self.frameButtons, text='delete', command=self.deletePreset).pack(side='left')
        tk.Button(self.frameButtons, text='v', command=lambda: self.rearrangePreset(1)).pack(side='right')
        tk.Button(self.frameButtons, text='^', command=lambda: self.rearrangePreset(-1)).pack(side='right')
        
        self.frameName.pack(fill='x')
        self.frameMain.pack(fill='x')
        self.updateContents()
        self.SetEditState(controller.current.TogglePresetEdit.state)
        self.filter()
    def updateContents(self):
        self.presetNameEntry.delete(0,'end')
        self.presetNameEntry.insert(0, self.presetEntry.name)
        self.presetNameLabel.config(text=self.presetEntry.name)
        self.presetIdLabel.config(text=self.presetEntry.presetId)
        self.cameraId.config(text='Camera ' + str(self.presetEntry.cameraId))
        self.filter()
    def saveToPreset(self):
        controller.current.shell.send('xCommand Camera Preset Store '
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
            controller.current.shell.send('xCommand Camera Preset Edit PresetId: ' + str(self.presetEntry.presetId)
                        + ' Name: ' + presetName + '\n')
            self.presetNameLabel.config(text=presetName)
    def deletePreset(self):
        controller.current.shell.send('xCommand Camera Preset Remove PresetId: ' + str(self.presetEntry.presetId) +'\n')
        controller.current.CameraPresets[self.index] = None
        self.destroy()
    def rearrangePreset(self, shift):
        self.index=min(36,max(0, self.index+shift))
        controller.current.shell.send('xCommand Camera Preset Edit PresetID: ' + str(self.presetEntry.presetId)+ ' ListPosition: '+ str(self.index) +'\n')
        controller.current.InitializePresetLists()
        #TODO: rearrange list internally, instead of rebuilding the whole list on every change
    def activatePreset(self):
        controller.current.shell.send('xCommand Camera Preset Activate PresetID: ' + str(self.presetEntry.presetId)+'\n')
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

        if (controller.current.PresetsFiltered.get()
            and not controller.current.cameras[self.presetEntry.cameraId].connected):
                self.grid_forget()
        else:
            col=self.presetEntry.cameraId
            row=1
            info = self.grid_info()
            for i in range(1, 36):
                if ((info and info['row']==i and info['column']==col) or not len(self.master.grid_slaves(column=col, row=i))):
                    row=i
                    break
            self.grid(column=col, row=row, sticky='nsew')