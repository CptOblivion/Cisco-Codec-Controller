from Helpers import *

class Camera():
    selected=None
    selectedNum=None
    controller=None
    def __init__(self, number):
        Camera.imageCamAvailable = tk.PhotoImage(file=Assets.getPath('Assets\Button_CamAvailable.png'))
        Camera.imageCamSelected = tk.PhotoImage(file=Assets.getPath('Assets\Button_CamSelected.png'))
        Camera.imageCamNone = tk.PhotoImage(file=Assets.getPath('Assets\Button_CamNone.png'))
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
        if (self.connected): Camera.selectCamera(self)

    def onSelect(self):
        self.selected=True
        self.selectButton.config(image=Camera.imageCamSelected, state='disabled')

    def onDeselect(self):
        self.selected=False
        if (self.connected): self.selectButton.config(image=Camera.imageCamAvailable, state='normal')

    def onDisable(self):
        self.connected=False
        self.onDeselect()
        self.selectButton.config(image=Camera.imageCamNone, state='disabled')
        controller.current.filterPresetsCurrent()
    def onEnable(self):
        self.connected=True
        self.onDeselect()
        controller.current.filterPresetsCurrent()

    def selectCamera(newCamera):
        if ((not Camera.selected) or Camera.selected != newCamera):
            if (Camera.selected):
                Camera.selected.onDeselect()
            Camera.selected=newCamera
            Camera.selectedNum = newCamera.number
            newCamera.onSelect()
            controller.current.OnCameraChange(newCamera.number)