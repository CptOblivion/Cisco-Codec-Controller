
from helpers import *
import bindings
import camera as c
import settings as s
import main

iconWarning=None
class Icons():
    init=False
    def load():
        if (not Icons.init):
            Icons.iconWarning=tk.PhotoImage(file=Assets.getAsset('Icon_Warning.png'))
            #TODO: resize to current pixel height of a row of text

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
        self.contentFrame.root=self
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
            self.contentFrame.pack(ipady=2, ipadx=2, padx=self.contentPadx, pady=3, fill='both', expand=True)
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

class BindingFrame(tk.Frame):
    conflicts={}
    #class to hold an individual keybind within a control
    labelUnassignedDevice = 'select device'
    labelUnassignedSubdevice = 'select input type'

    class ParsedEntry(tk.Entry):
        #subclass of entry to display, adjust, and error check binding inputs
        def __init__(self, parent, parentBinding, rules, initialValue, range=None, **args):
            tk.Entry.__init__(self, parent, **args)
            self.variable=tk.StringVar(self)
            self.bind('<FocusIn>', self.selectAll)
            self.rules=rules
            self.range=range
            self.bindingFrame=parentBinding
            
            self.config(textvariable=self.variable)
            self.bind('<FocusOut>', self.onChange)
            if (initialValue is not None): self.insert(0,initialValue)

        def selectAll(self, event):
            self.selection_range(0,'end')

        def onChange(self, event):
            if (self.rules=='int'): self.rulesInt(self.get())
            elif (self.rules=='midi'): self.rulesMidi(self.get())
            elif (self.rules=='midiString'): self.rulesMidiString(self.get())
            s.Settings.changeMade(self.bindingFrame)

        def rulesMidi(self, input):
            #convert string into a valid midi channel (int or 'any')
            if (input != 'any'):
                input = self._rulesInt(input)
                if input == None:
                    input = 'any'
                    valid=False
                    self.variable.set(input)
                    return False
            return True
        def rulesMidiString(self, input):
            if (input != 'any'):
                input = self._rulesString(input)
                if input == None:
                    input = 'any'
                    self.variable.set(input)
                    return False
            return True
        def rulesInt(self, input):
            #convert string into an int (or 0, if it's not a valid int)
            input = self._rulesInt(input)
            if (input == None):
                if(self.range): self.variable.set(self.range[0])
                else: self.variable.set(0)
                return False

            if (self.range and self.range[0] < input < self.range[1]):
                input = max(self.range[0], min(self.range[1], input))
                self.variable.set(input)
                return False
            return True
        def _rulesInt(self, input):
            #helper function to parse a string as int or None
            try: return int(input)
            except: return None
        def _rulesString(self, input):
            if (input == ''): return None
            return input

    def __init__(self, parent, command, deviceType=None, deviceSubtype=None, contents=None, **options):
        tk.Frame.__init__(self, parent, **options)
        self.deviceType=tk.StringVar(self)
        self.deviceType.set(BindingFrame.labelUnassignedDevice)
        self.deviceSubtype = tk.StringVar(self)
        self.deviceSubtype.set(BindingFrame.labelUnassignedSubdevice)
        self.deviceTypeLast = None
        self.deviceSubtypeLast = None
        Icons.load()
        #(button, analog) each is true or false
        self.commandType=(command[1]=='button' or command[1]=='both', command[1]=='analog' or command[1]=='both')

        self.contents=None

        self.titlebar = tk.Frame(self)
        if True:
            self.conflictIcon=tk.Label(self.titlebar)
            self.listenButton = tk.Button(self.titlebar, text='listen for input',
                                          command=lambda:s.InputRouting.bindListen(self))
            self.deviceTypeLabel = tk.OptionMenu(self.titlebar, self.deviceType, BindingFrame.labelUnassignedDevice,
                                                 'controller', 'midi', command=self.changeDeviceType)
            self.deviceSubtypeLabel = tk.OptionMenu(self.titlebar, self.deviceSubtype,
                                                    BindingFrame.labelUnassignedSubdevice, command=self.changeDeviceSubtype)
            
            self.conflictIcon.pack(side='left')
            self.listenButton.pack(side='left')
            self.deviceTypeLabel.pack(side='left', padx=(5,3))
            tk.Button(self.titlebar, text='X', command=self.destroySelf).pack(side='right')
        self.body=tk.Frame(self)
        self.titlebar.pack(fill='x', padx=2, pady=2)
        self.body.pack(fill='x', padx=2, pady=2)
        self.setDevice(deviceType, deviceSubtype, contents)

    def destroySelf(self):
        s.Settings.changeMade(self, removed=True)
        self.destroy()
    def compareBind(self, binding):
        if (self.contents and binding.contents and self.deviceType.get()==binding.deviceType.get() and
            self.deviceSubtype.get()==binding.deviceSubtype.get()):
            if (self.deviceType.get() == 'controller'):
                #button and axis number are both stored in contents[0]
                if (self.contents[0].get() == binding.contents[0].get()):
                    return True
            elif (self.deviceType.get()=='midi'):
                #if either device is 'any' the devices match, and same for the channel
                #but check the cc or note number first, since if that doesn't match the whole thing won't be a match
                if ((self.contents[1].get() == binding.contents[1].get()) and
                    (self.contents[0].get()=='any' or binding.contents[0].get()=='any' or
                        self.contents[0].get()==binding.contents[0].get())):
                    return True
        return False

    def addConflict(self, binding):
        if (binding != self):
            if (self not in BindingFrame.conflicts):
                BindingFrame.conflicts[self]=[]
            if (binding not in BindingFrame.conflicts[self]):
                BindingFrame.conflicts[self].append(binding)
            self.conflictIcon.config(image=Icons.iconWarning)
            self.master.root.conflictIcon.config(image=Icons.iconWarning)
            if (self.master.root.categoryFrame):
                self.master.root.categoryFrame.root.conflictIcon.config(image=Icons.iconWarning)
    def removeConflict(self, binding):
        if (binding != self):
            if (self in BindingFrame.conflicts):
                if (binding in BindingFrame.conflicts[self]):
                    BindingFrame.conflicts[self].remove(binding)
                    if (len(BindingFrame.conflicts[self])==0):
                        del BindingFrame.conflicts[self]
                        self.conflictIcon.config(image='')
                        frameClear=True
                        for child in self.master.winfo_children():
                            if (child in BindingFrame.conflicts):
                                frameClear=False
                                break
                        if (frameClear):
                            self.master.root.conflictIcon.config(image='')
                            if (self.master.root.categoryFrame):
                                frameClear=True
                                for child in self.master.root.categoryFrame.winfo_children():
                                    if (self.master.root.conflictIcon.cget('image') !=''):
                                        frameClear=False
                                        break
                                if (frameClear):
                                    self.master.root.categoryFrame.root.conflictIcon.config(image='')

    def checkConflict(self, changedBinding, removed=False):
        if (changedBinding != self):
            if (self.compareBind(changedBinding)):
                if (removed):
                    self.removeConflict(changedBinding)
                    changedBinding.removeConflict(self)
                else:
                    self.addConflict(changedBinding)
                    changedBinding.addConflict(self)
            else:
                self.removeConflict(changedBinding)
                changedBinding.removeConflict(self)

        return(len(BindingFrame.conflicts)>0)

    #versions of changeMade with different amounts of inputs
    #   (that will be discarded, and pass self along to s.Settings.changeMade
    #instead of making a bunch of the same lambda to discard inputs
    def changeMade0(self):
        s.Settings.changeMade(self)
    def changeMade1(self, value):
        s.Settings.changeMade(self)
    def changeDeviceType(self, deviceType):
        if (self.deviceTypeLast != deviceType):
            s.Settings.changeMade(self)
            self.setDevice(deviceType, None)
    def changeDeviceSubtype(self, deviceSubtype):
        if (self.deviceSubtypeLast != deviceSubtype):
            s.Settings.changeMade(self)
            self.setDevice(self.deviceType.get(), deviceSubtype)
    def setDevice(self, deviceType, deviceSubtype, contents=None):
        if (self.deviceTypeLast != deviceType or self.deviceSubtypeLast != deviceSubtype):
            if (deviceType == None or deviceType == BindingFrame.labelUnassignedDevice):
                self.deviceType.set(BindingFrame.labelUnassignedDevice)
                self.deviceSubtypeLabel.forget()
            else:
                self.deviceType.set(deviceType)
                self.deviceSubtypeLabel.pack(side='left', padx=(10,3)) #TODO: test if this breaks the layout on assigning and then unassigning a bind
                if (deviceSubtype == None or deviceSubtype== BindingFrame.labelUnassignedSubdevice):
                    self.deviceSubtype.set(BindingFrame.labelUnassignedSubdevice)
                else:
                    self.deviceSubtype.set(deviceSubtype)

            self.deviceTypelast=self.deviceType.get()
            self.deviceSubtypeLast=self.deviceSubtype.get()
            self.contents=[]

            for child in self.body.winfo_children():
                child.destroy()

            #populate the subtype menu
            if (deviceType == 'midi'):
                #TODO: make this bit a general function
                self.deviceSubtypeLabel['menu'].delete(0,'end')
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(
                    label='note', command=lambda: self.changeDeviceSubtype('note'))
                self.deviceSubtypeLabel['menu'].add_command(
                    label='control', command=lambda: self.changeDeviceSubtype('control'))
            elif (deviceType=='controller'):
                self.deviceSubtypeLabel['menu'].delete(0,'end')
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(
                    label='button', command=lambda: self.changeDeviceSubtype('button'))
                if (self.commandType[0]): self.deviceSubtypeLabel['menu'].add_command(
                    label='hat', command=lambda: self.changeDeviceSubtype('hat'))
                self.deviceSubtypeLabel['menu'].add_command(label='axis', command=lambda: self.changeDeviceSubtype('axis'))

            #populate the inputs
            if (deviceSubtype != None and deviceSubtype != self.labelUnassignedSubdevice):
                if (deviceType == 'midi'):
                    #midi contents: midi device (int or None), midi channel (int or None), control number (int), threshold
                    #TODO: figure out if we can get tooltips going (or just add a descriptor text like 'leave blank for any'

                    if (contents==None): contents=(None,None)
                    self.contents=[None, None, None]

                    tk.Label(self.body, text='channel: ').pack(side='left', padx=2, pady=2)
                    self.contents[0]= BindingFrame.ParsedEntry(self.body, self, 'midi',contents[0], width=3)
                    self.contents[0].pack(side='left', padx=2, pady=2)

                    tk.Label(self.body, text='index: ').pack(side='left', padx=2, pady=2)
                    self.contents[1]= BindingFrame.ParsedEntry(self.body, self, 'int',contents[1], width=3)
                    self.contents[1].pack(side='left', padx=2, pady=2)

                    if (deviceSubtype == 'control'):
                        self.contents[2] = tk.DoubleVar(self.body)
                        if (len(contents)==3 and contents[2]): self.contents[2].set(contents[2])
                        else: self.contents[2].set(bindings.Bindables.thresholdDefaultMidiCC)
                        tk.Label(self.body, text='threshold').pack(side='left', padx=2, pady=2)
                        tk.Scale(self.body, variable=self.contents[2], from_=0, to_=1, digits=3, resolution=0.01,
                                 orient='horizontal', command=self.changeMade1).pack(side='left', padx=2, pady=2)

                elif (deviceType == 'controller'): 
                    if (deviceSubtype == 'axis'):
                        #axisNumber, axisType, axisFlip, threshold
                        if (contents == None): contents = [None, None, None, None]
                        self.contents = [None, None, None, None]
                        tk.Label(self.body, text='axis: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= BindingFrame.ParsedEntry(self.body, self, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)
                        
                        tk.Label(self.body, text='type: ').pack(side='left', padx=2, pady=2)
                        self.contents[1]= tk.StringVar(self.body)
                        if (contents[1]): self.contents[1].set(contents[1])
                        else: self.contents[1].set('stick')
                        tk.OptionMenu(self.body, self.contents[1],'stick','trigger').pack(side='left', padx=2, pady=2)
                        
                        self.contents[2] = tk.IntVar(self.body)
                        if (contents[2]): self.contents[2].set(contents[2])
                        else: self.contents[2].set(1)
                        tk.Checkbutton(self.body, variable=self.contents[2], text='invert', onvalue=-1, offvalue=1
                                       , command=self.changeMade0).pack(side='left', padx=2, pady=2)

                        self.contents[3] = tk.DoubleVar(self.body)
                        if (contents[3] is not None): self.contents[3].set(contents[3])
                        else: self.contents[3].set(bindings.Bindables.thresholdDefaultController)
                        tk.Label(self.body, text='threshold').pack(side='left', padx=2, pady=2)
                        tk.Scale(self.body, variable=self.contents[3], from_=0.01, to_=1, digits=3, resolution=0.01,
                                 orient='horizontal', command=self.changeMade1).pack(side='left', padx=2, pady=2)

                    elif (deviceSubtype == 'button'):
                        #buttonNumber
                        if (contents == None): contents = [None]
                        self.contents=[None]
                        
                        tk.Label(self.body, text='button: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= BindingFrame.ParsedEntry(self.body, self, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)

                    elif (deviceSubtype == 'hat'):
                        #hatNumber, hatDirection
                        if (contents == None): contents = [None, None]
                        self.contents=[None, None]

                        tk.Label(self.body, text='hat number: ').pack(side='left', padx=2, pady=2)
                        self.contents[0]= BindingFrame.ParsedEntry(self.body, self, 'int',contents[0], width=3)
                        self.contents[0].pack(side='left', padx=2, pady=2)
                        
                        tk.Label(self.body, text='hat direction (clockwise, 0 is up): ').pack(
                            side='left', padx=2, pady=2)
                        self.contents[1]= BindingFrame.ParsedEntry(
                            self.body, self, 'int',contents[1], range=(0,7), width=3)
                        self.contents[1].pack(side='left', padx=2, pady=2)
                elif (deviceType == 'keyboard'):
                    None
    def getSubtypeString(self):
        return self.deviceType + '_' + self.deviceSubtype
    def makeOutput(self, commandAddress):
        if (self.contents and self.deviceSubtype.get() != BindingFrame.labelUnassignedSubdevice):
            if(self.deviceType.get() == 'midi'):
                midiChannel, inputNumber, threshold = self.contents

                outstring= commandAddress + ',midi.'+ self.deviceSubtype.get() + \
                    ',' + midiChannel.get() + ',' + inputNumber.get()
                if (threshold is not None and threshold.get() != bindings.Bindables.thresholdDefaultMidiCC):
                    outstring += ','+str(threshold.get())
                return outstring
        
            elif(self.deviceType.get() == 'controller'):
                if (self.deviceSubtype.get() == 'axis'):
                    axisNum, axisType, axisFlip, threshold = self.contents
                    outstring= commandAddress + ',controller.axis,'+axisNum.get() + ',' + \
                        axisType.get() + ',' + str(axisFlip.get())
                    if (threshold.get() != bindings.Bindables.thresholdDefaultController):
                        outstring += ','+str(threshold.get())
                    return outstring
                elif (self.deviceSubtype.get() == 'button'):
                    buttonNum=self.contents[0]
                    return commandAddress+',controller.button,'+buttonNum.get()
                elif (self.deviceSubtype.get() == 'hat'):
                    hatNum, hatDirection = self.contents
                    return commandAddress+',controller.hat,'+hatNum.get()+','+hatDirection.get()
        return None
        
class ControlBindPanel(ToggleFrame):
    #class to hold several keybinds that all point to the same command
    def __init__(self, parent, bindableName, command, **options):
        title=bindableName.replace('_', ' ')
        ToggleFrame.__init__(self, parent, title=title, keepTitle=True, buttonShowTitle = 'show',
                             buttonHideTitle='hide', togglePin='left', relief='groove', borderwidth=1)
        Icons.load()
        self.bindableName = bindableName
        self.command = command
        self.categoryFrame=None
        #self.config(highlightbackground='black', highlightthickness=1)
        
        self.conflictIcon=tk.Label(self.Titlebar)
        self.conflictIcon.pack(side='left', before=self.expandButton)
        frameBody = tk.Frame(self.contentFrame)
        if True:
            frameSidebar=tk.Frame(frameBody)
            self.BindingList = tk.Frame(frameBody, relief='sunken', borderwidth=2)
            self.BindingList.root=self
            tk.Button(frameSidebar, text='add', command=self.AddBinding).pack(padx=2,pady=3)
            frameSidebar.pack(side='left', fill='y', padx=2, pady=2)
            self.BindingList.pack(side='left', fill='x', expand=True)

        frameBody.pack(padx=3,pady=3, fill='both', expand=True)

        def compareCommand():
            if (not binding):
                return False
            command=binding.command
            if (self.bindableName.startswith(bindings.Bindables.bindingPresetsPrefix)):
                command=self.bindableName[len(bindings.Bindables.bindingPresetsPrefix):]
                if (binding.bindablePreset==command):
                    return True
            elif (command==bindings.Bindables.index[self.bindableName]): return True
            return False

         #digital inputs can only be bound to button commands, or commands that handle their own input
        if (command[1]=='button' or command[1]=='both'):
            for binding in s.Settings.commandBinds['midi']['note']:
                if (compareCommand()):
                    self.AddBinding(deviceType='midi', deviceSubtype='note',
                                    contents=(binding.midiChannel,binding.inputNumber))
            b=0
            for binding in s.Settings.commandBinds['controller']['button']:
                if (compareCommand()):
                    self.AddBinding(deviceType='controller', deviceSubtype='button', contents=[b])
                b+=1
            h = 0
            for hat in s.Settings.commandBinds['controller']['hat']:
                direction=0
                for binding in hat:
                    if (compareCommand()):
                        self.AddBinding(deviceType='controller', deviceSubtype='hat', contents=[h, direction])
                    direction+=1
                h+=1

        #analog inputs can always be bound to button commands, as long as the threshold is properly set
        for binding in s.Settings.commandBinds['midi']['control']:
            if (compareCommand()):
                self.AddBinding(deviceType='midi', deviceSubtype='control',
                                contents=(binding.midiChannel,binding.inputNumber, binding.threshold))
        a=0
        for binding in s.Settings.commandBinds['controller']['axis']:
            if (compareCommand()):
                self.AddBinding(deviceType='controller', deviceSubtype='axis',
                                contents=[a, binding.type,binding.flip, binding.threshold])
            a+=1

    def AddBinding(self, deviceType=None, deviceSubtype=None, contents=None):
        newBinding=BindingFrame(self.BindingList, self.command, relief='ridge', borderwidth=2, deviceType=deviceType,
                     deviceSubtype=deviceSubtype, contents=contents)
        newBinding.pack(fill='x', padx=2, pady=2)
        s.Settings.changeMade(newBinding)

class ControlBindPresetPanel(ControlBindPanel):
    def __init__(self, parent, bindableName, command, presetName, bindsList, newBinding=False, **options):
        ControlBindPanel.__init__(self, parent, bindableName,command,**options)
        def updateCommandName(newText):
            self.bindableName=bindings.Bindables.bindingPresetsPrefix+newText
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
            for binding in self.BindingList.winfo_children():
                s.Settings.changeMade(binding, removed=True)
            self.destroy()

        tk.Button(self.Titlebar, text='X', command=deleteButton).pack(side='left')
        if (newBinding):
            self.toggle()
            self.title.focus_set()
            self.title.selection_range(0,'end')
            self.AddBinding()

class CameraPresetPanel(tk.Frame):
    lastTriggerBinding=[None,None,None,None,None,None,None,None]
    activePresets=[None,None,None,None,None,None,None,None]
    controller=None
    def __init__(self, parent, index, cameraId=None, *args, **options):
        tk.Frame.__init__(self, parent, relief='ridge', borderwidth=2, *args, **options)
        
        self.triggerBinding = None
        self.index = index
        self.presetId=None #for global presets, index and presetID are identical and immutable
        if (cameraId == 0): self.presetId=index
        self.cameraId=cameraId #set to 0 for Cameras instead of Camera
        self.name=None
        #self.listPosition=index

        self.frameName = tk.Frame(self)
        
        self.presetIdLabel = tk.Label(self.frameName)

        validation=self.register(CameraPresetPanel.validatePresetName)
        self.presetNameLabel = tk.Label(self.frameName, text=self.name)
        self.nameChangeNotification=tk.Label(self, text=('Global Preset names\n'
                                                         'cannot be changed\n'
                                                         'overwrite to apply'))

        #TODO: just do away with the name label for global presets?
        self.presetNameEntry = tk.Entry(self.frameName, validate='key', validatecommand=(validation, '%S'))
        self.presetNameEntry.bind('<Return>', lambda event: self.focus())
        self.presetNameEntry.bind('<FocusOut>', self.renamePreset)

        self.presetIdLabel.pack(side='left')
        #self.presetNameLabel.pack(side='left')

        self.frameMain = tk.Frame(self)
        self.activateButton = tk.Button(self.frameMain, text='activate', command=self.activatePreset)

        self.activateButton.pack(side='left', fill='x', expand=True)

        self.frameButtons = tk.Frame(self)

        tk.Button(self.frameButtons, text='overwrite', command=self.saveToPreset).pack(side='left')
        tk.Button(self.frameButtons, text='delete', command=self.deletePreset).pack(side='left')
        if (cameraId==None or cameraId>0):
            #TODO: in-program rearranging of global presets? (may require moving and recording camera positions several times)
            #alternately, store preset order in ini? (just a mapping of presetId to list index?)
            tk.Button(self.frameButtons, text='v', command=lambda: self.rearrangePreset(1)).pack(side='right')
            tk.Button(self.frameButtons, text='^', command=lambda: self.rearrangePreset(-1)).pack(side='right')
        
        self.frameName.pack(fill='x')
        self.frameMain.pack(fill='x', expand=True)
        self.updateContents()
        self.SetEditState(main.current.TogglePresetEdit.state)
        self.filter()
    def updateTriggerBinding(self):
        if (self.triggerBinding): self.triggerBinding.triggerFeedback(False)
        if (self.name):
            for bindingType in s.Settings.commandBinds['midi']:
                for binding in s.Settings.commandBinds['midi'][bindingType]:
                    if (binding.bindablePreset == self.name):
                        #todo: maybe we should have a list of triggerBindings in case multiple ones are bound?
                        print(self.name)
                        self.triggerBinding=binding
                        return
        self.triggerBinding=None

    def updateContents(self):
        self.presetNameEntry.delete(0,'end')
        if (self.name):
            self.presetNameEntry.insert(0, self.name)
            self.presetNameLabel.config(text=self.name)
        if (self.presetId):
            self.presetIdLabel.config(text=self.presetId)
        self.filter()
        self.updateTriggerBinding()

    def saveToPreset(self):
        self.triggerFeedback()
        if (self.cameraId):
            main.current.shell.send('xCommand Camera Preset Store '
                        + 'PresetId: ' + str(self.presetId)
                        + ' CameraId: '+ str(self.cameraId)
                        + ' ListPosition: ' + str(self.index)
                        + ' Name: ' + self.presetNameEntry.get() + '\r')
        else:
            if (self.presetNameEntry.get() != ''):
                self.name= self.presetNameEntry.get()
            main.current.shell.send('xCommand Preset Store PresetId: '
                                          + str(self.presetId) + ' Type:Camera Description: "'+self.name+'"\n')

    def validatePresetName(newValue):
        return not ' ' in newValue

    def renamePreset(self, event):
        if (self.cameraId):
            presetName=self.presetNameEntry.get()
            if (presetName):
                main.current.shell.send('xCommand Camera Preset Edit PresetId: ' + str(self.presetId)
                            + ' Name: ' + presetName + '\n')
                self.presetNameLabel.config(text=presetName)
        elif (self.cameraId == 0):
            self.nameChangeNotification.pack(side='bottom')
            #print('cannot rename global presets, please overwrite to save name!')
            #TODO: popup confirming if user wants to overwrite preset

    def deletePreset(self):
        if (self.cameraId == 0):
            main.current.shell.send('xCommand Preset Clear PresetId:' + str(self.presetId) +'\n')
            main.current.CamerasPresets[self.index] = None
            self.grid_forget()
            for preset in main.current.CamerasPresets:
                if (preset): preset.filter()
        else:
            main.current.shell.send('xCommand Camera Preset Remove PresetId: ' + str(self.presetId) +'\n')
            main.current.CameraPresets[self.index] = None
        self.destroy()

    def rearrangePreset(self, shift):
        if (self.cameraId):
            currentIndex=self.grid_info()['row']
            newIndex=min(36,max(1, currentIndex+shift))
            if (newIndex > 0):
                targetWidget=self.master.grid_slaves(newIndex, self.cameraId)
                if (len(targetWidget)):
                    targetWidget=targetWidget[0]
                    oldIndex=self.index
                    self.index=targetWidget.index
                    targetWidget.index=oldIndex
                    self.grid(column=self.cameraId, row=newIndex, sticky='nsew')
                    targetWidget.grid(column=self.cameraId, row=currentIndex, sticky='nsew')

            main.current.shell.send('xCommand Camera Preset Edit PresetID: ' + str(self.presetId)+
                                          ' ListPosition: '+ str(self.index) +'\n')

    def activatePreset(self):
        self.triggerFeedback()
        if (self.cameraId):
            main.current.shell.send('xCommand Camera Preset Activate PresetID: ' + str(self.presetId)+'\n')
        else:
            main.current.shell.send('xCommand Preset Activate PresetID: ' + str(self.presetId)+'\n')

    def triggerFeedback(self):
        #TODO: track the last trigger in each column, call lastTrigger.triggerBinding.triggerFeedback(False)
        if (CameraPresetPanel.lastTriggerBinding[self.cameraId]):
            CameraPresetPanel.lastTriggerBinding[self.cameraId].triggerBinding.triggerFeedback(False)
        if (self.triggerBinding):
            self.triggerBinding.triggerFeedback(True)
            CameraPresetPanel.lastTriggerBinding[self.cameraId] = self
            CameraPresetPanel.activePresets[self.cameraId] = self.name
        else:
            CameraPresetPanel.lastTriggerBinding[self.cameraId] = None
            CameraPresetPanel.activePresets[self.cameraId] = None


    def SetEditState(self, unlock):
        if (unlock):
            self.frameButtons.pack(fill='x')
            self.presetNameLabel.forget()
            self.presetNameEntry.pack(side='left')

        else:
            self.frameButtons.forget()
            self.presetNameEntry.forget()
            self.presetNameLabel.pack(side='left')
            if (self.cameraId == 0 and self.name):
                self.presetNameEntry.delete(0,'end')
                self.presetNameEntry.insert(0,self.name)
                self.nameChangeNotification.forget()
    
    def filter(self):
        if (self.isValid()):
            if (self.cameraId > 0 and (main.current.PresetsFilteredConnected.get()
                 and not main.current.cameras[self.cameraId].connected)
                or (main.current.PresetsFilteredCurrent.get()
                    and c.Camera.selectedNum!=self.cameraId)):
                    self.grid_forget()
            else:
                col=self.cameraId
                row=1
                info = self.grid_info()
                searchEnd=36
                if (self.cameraId==0):
                    searchEnd=16
                for i in range(1, searchEnd):
                    if ((info and info['row']==i and info['column']==col) or not len(self.master.grid_slaves(column=col, row=i))):
                        row=i
                        break
                self.grid(column=col, row=row, sticky='nsew')

    def isValid(self):
        return(self.cameraId is not None and self.presetId is not None)

    def setContents(self, presetId=None, cameraId=None, name=None):
        if (presetId is not None):
            self.presetId=presetId
        if (cameraId is not None):
            self.cameraId=cameraId
        if (name is not None):
            name=name.replace(' ','_')
            self.name=name
        self.updateContents()
        if (self.presetId is not None and self.name is not None and
            CameraPresetPanel.activePresets[self.cameraId] == self.name):
            self.triggerFeedback()

class ConfigSlider(tk.Frame):
    def __init__(self, parent, command=None, from_=0, to_=1):
        tk.Frame.__init__(self,parent)
        self.contentFrame=tk.Frame(self)
        self.command=command
        self.from_=from_
        self.to_=to_
        if True:
            self.scale=tk.Scale(self.contentFrame, from_=from_, to_=to_, orient='horizontal')
            self.scale.bind('<ButtonPress-1>', self.onMouseDown)
            self.scale.bind('<ButtonRelease-1>', self.onMouseUp)

            tk.Button(self.contentFrame,text='<', command=self.decrement).pack(side='left')
            self.scale.pack(side='left', fill='x')
            tk.Button(self.contentFrame,text='>', command=self.increment).pack(side='left')

        self.contentFrame.pack(fill='both')
    def setVariable(self, variable):
        self.variable=variable
        self.scale.config(variable=variable)
    def onMouseDown(self, event):
        self.scale.config(variable=None)
    def onMouseUp(self, event):
        self.scale.config(variable=self.variable)
        if (self.command and self.variable):
            self.command(self.variable.get())
    def decrement(self):
        if (self.variable):
            self.variable.set(max(self.from_, self.variable.get()-1))
            if (self.command): self.command(self.variable.get())
    def increment(self):
        if (self.variable):
            self.variable.set(min(self.to_, self.variable.get()+1))
            if (self.command): self.command(self.variable.get())