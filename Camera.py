
from helpers import *
import settings as s
import main

class Camera():
    selected=None
    selectedNum=None
    controller=None
    def __init__(self, number):
        Camera.imageCamAvailable = tk.PhotoImage(file=Assets.getAsset('Button_CamAvailable.png'))
        Camera.imageCamSelected = tk.PhotoImage(file=Assets.getAsset('Button_CamSelected.png'))
        Camera.imageCamNone = tk.PhotoImage(file=Assets.getAsset('Button_CamNone.png'))
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
        self.triggerBinding = None

    def select(self):
        if (self.connected): Camera.selectCamera(self)

    def onSelect(self):
        self.selected=True
        self.selectButton.config(image=Camera.imageCamSelected, state='disabled')
        if (self.triggerBinding): self.triggerBinding.triggerFeedback(True)

    def onDeselect(self):
        self.selected=False
        if (self.connected):
            self.selectButton.config(image=Camera.imageCamAvailable, state='normal')
            if (self.triggerBinding): self.triggerBinding.triggerFeedback(False)

    def onDisable(self):
        self.connected=False
        self.onDeselect()
        self.selectButton.config(image=Camera.imageCamNone, state='disabled')
        main.current.filterPresetsCurrent()
    def onEnable(self):
        self.connected=True
        self.onDeselect()
        main.current.filterPresetsCurrent()
    def updateTriggerBinding(self):
        #always run this function on camera creation and, after cameras are created, on binding change
        for bindingType in s.Settings.commandBinds['midi']:
            for binding in s.Settings.commandBinds['midi'][bindingType]: #checking both note and command within midi bindings
                if (binding):
                    if (binding.command[0].__name__ == 'selectCamera' + str(self.number)):
                        self.triggerBinding = binding
                        return

    def selectCamera(newCamera):
        if ((not Camera.selected) or Camera.selected != newCamera):
            if (Camera.selected):
                Camera.selected.onDeselect()
            Camera.selected=newCamera
            Camera.selectedNum = newCamera.number
            newCamera.onSelect()
            main.current.OnCameraChange(newCamera.number)