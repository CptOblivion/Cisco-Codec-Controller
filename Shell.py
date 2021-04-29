import paramiko
import re
from Debug import *
from Camera import *
from Settings import *
from UI import *

class Shell():
    StartPhraseCamera = ' Camera '
    StartPhrasePan = 'Position Pan: '
    StartPhraseTilt = 'Position Tilt: '
    StartPhraseZoom = 'Position Zoom: '
    StartPhraseFocus = 'Position Focus: '
    StartPhraseBrightnessLevel = 'Brightness Level: '
    StartPhraseWhitebalanceLevel = 'Whitebalance Level: '
    StartPhraseGammaLevel = 'Gamma Level: '
    StartPhraseFocusMode = 'Focus Mode: '
    StartPhraseBrightnessMode = 'Brightness Mode: '
    StartPhraseWhitebalanceMode = 'Whitebalance Mode: '
    StartPhraseGammaMode = 'Gamma Mode: '
    StartPhrasePresetResult = 'PresetListResult Preset '
    StartPhrasePresetStoreResult = 'PresetStoreResult'
    StartPhrasePresetDefinedResult=re.compile('.*Preset .* Defined: .*')
    StartPhrasePresetDescriptionResult=re.compile('.*Preset .* Description: .*')
    StartPhraseCameraConnected=re.compile('.*Camera .* Connected: .*')

    def setup():
        Shell.ssh=paramiko.SSHClient()
        Shell.ssh.load_system_host_keys()
        Shell.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    def connect(hostname='', username='', password=''):
        try:
            Shell.ssh.connect(hostname=hostname,
                                username=username,
                                password=password)
        except paramiko.ssh_exception.BadAuthenticationType:
            #TODO: feedback in main window
            print('\n\nusername or password mismatch!')
        except paramiko.ssh_exception.NoValidConnectionsError:
            print('\n\ninvalid connection at address ',Settings.config['Startup']['IPADDRESS'])
        except TimeoutError:
            print('\n\nSSH timeout! No device found.')
        except:
            #TODO: 
            print("Unhandled Connection Exception:", sys.exc_info()[0])
        else:
            return True
        return False

    def __init__(self, controller):
        self.controller=controller

        self.actualShell=Shell.ssh.invoke_shell()
    def recv_ready(self):
        return self.actualShell.recv_ready()
    def send(self, message):
        self.actualShell.send(message)
    def recv(self):
        return self.actualShell.recv(9999)
    def checkResponses(self):
        if (self.actualShell.recv_ready()):
            out=self.actualShell.recv(9999).decode('ascii')
            #if (Settings.printVerbose.get()):debug.printCodec('vvvv')
            Responses = out.splitlines()


            StartPhraseCamera = 'Camera '

            for ResponseLine in Responses:
                debug.printCodec('>>' + ResponseLine)
                #TODO: turn all these calls into a more general function
                #TODO: get the camera number referred to in ResponseLine (if applicable), check if it's the current camera
                #TODO: handling for bad inputs (EG newline missing)
                if (ResponseLine.startswith('*')):
                    if (Shell.StartPhraseCamera in ResponseLine):
                        sIndex=ResponseLine.rfind(Shell.StartPhraseCamera) + len(Shell.StartPhraseCamera)
                        cameraNumber = int(ResponseLine[sIndex])
                    if (ResponseLine=='** end'):
                        #skip all the other checks if this line is just the end command confirmation
                        None
                    elif (Shell.StartPhrasePan in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhrasePan) + len(Shell.StartPhrasePan)
                        value = int(ResponseLine[sIndex:])
                        self.controller.cameras[cameraNumber].position[0]=value
                        self.controller.LabelPan.config(text = 'Pan: ' + str(value))
                        self.controller.PanningDone()

                    elif (Shell.StartPhraseTilt in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseTilt) + len(Shell.StartPhraseTilt)
                        value = int(ResponseLine[sIndex:])
                        self.controller.cameras[cameraNumber].position[1]=value
                        self.controller.LabelTilt.config(text = 'Tilt: ' + str(value))
                        self.controller.TiltingDone()
                    
                    elif (Shell.StartPhraseZoom in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseZoom) + len(Shell.StartPhraseZoom)
                        value = int(ResponseLine[sIndex:])
                        self.controller.cameras[cameraNumber].position[2]=value
                        self.controller.LabelZoom.config(text = 'Zoom: ' + str(value))
                        self.controller.ZoomingDone()
                    
                    elif (Shell.StartPhraseFocus in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseFocus) + len(Shell.StartPhraseFocus)
                        value = int(ResponseLine[sIndex:])
                        self.controller.cameras[cameraNumber].position[3]=value
                        self.controller.LabelFocus.config(text = 'Focus: ' + str(value))
                        self.controller.FocusingDone()
                    
                    elif (Shell.StartPhraseBrightnessLevel in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseBrightnessLevel) + len(Shell.StartPhraseBrightnessLevel)
                        self.controller.cameras[cameraNumber].brightnessValue.set(int(ResponseLine[sIndex:]))
                    
                    elif (Shell.StartPhraseWhitebalanceLevel in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseWhitebalanceLevel) + len(Shell.StartPhraseWhitebalanceLevel)
                        self.controller.cameras[cameraNumber].whitebalanceValue.set(int(ResponseLine[sIndex:]))
                            
                    elif (Shell.StartPhraseGammaLevel in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseGammaLevel) + len(Shell.StartPhraseGammaLevel)
                        self.controller.cameras[cameraNumber].gammaValue.set(int(ResponseLine[sIndex:]))

                    elif (Shell.StartPhraseFocusMode in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseFocusMode) + len(Shell.StartPhraseFocusMode)
                        self.controller.cameras[cameraNumber].focusManual.set(ResponseLine[sIndex:]=='Auto')

                    elif (Shell.StartPhraseBrightnessMode in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseBrightnessMode) + len(Shell.StartPhraseBrightnessMode)
                        self.controller.cameras[cameraNumber].brightnessManual.set(ResponseLine[sIndex:]=='Auto')

                    elif (Shell.StartPhraseWhitebalanceMode in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseWhitebalanceMode) + len(Shell.StartPhraseWhitebalanceMode)
                        self.controller.cameras[cameraNumber].whitebalanceManual.set(ResponseLine[sIndex:]=='Auto')
                    
                    elif (Shell.StartPhraseGammaMode in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhraseGammaMode) + len(Shell.StartPhraseGammaMode)
                        self.controller.cameras[cameraNumber].gammaManual.set(ResponseLine[sIndex:]=='Auto')

                    elif (Shell.StartPhrasePresetStoreResult in ResponseLine):
                        sIndex = ResponseLine.rfind(Shell.StartPhrasePresetStoreResult) + len(Shell.StartPhrasePresetStoreResult)
                        self.controller.InitializePresetLists()

                    elif (Shell.StartPhrasePresetResult in ResponseLine):
                        SplitString = ResponseLine.split()
                        i=0
                        while i < len(SplitString):
                            if (SplitString[i] == 'PresetListResult' and SplitString[i+1] == 'Preset'):
                                PresetIndex = int(SplitString[i+2])
                                if (self.controller.CameraPresets[PresetIndex] == None):
                                    self.controller.CameraPresets[PresetIndex] = CameraPresetPanel(
                                        self.controller.Frame_PresetsContainer.contents, PresetIndex)
                                    debug.print('added preset at index ' + str(PresetIndex))
                                i+=2
                            elif (SplitString[i] == 'Name:'):
                                nameString = SplitString[i+1]
                                i+=2
                                while i < len(SplitString): #keep adding to name until the end of the line
                                    nameString += ' ' + SplitString[i]
                                    i+= 1
                                self.controller.CameraPresets[PresetIndex].setContents(
                                    name = nameString[1:len(nameString)-1]) #trim quotes
                                debug.print('added name "' + self.controller.CameraPresets[PresetIndex].name
                                            + '" at index ' + str(PresetIndex))
                                i+=1
                            elif (SplitString[i] == 'CameraId:'):
                                self.controller.CameraPresets[PresetIndex].setContents(cameraId = int(SplitString[i+1]))
                                debug.print('added cameraId ' + str(self.controller.CameraPresets[PresetIndex].cameraId)
                                            + ' at index ' + str(PresetIndex))
                                i+=1
                            elif (SplitString[i] == 'PresetId:'):
                                self.controller.CameraPresets[PresetIndex].setContents(presetId = int(SplitString[i+1]))
                                debug.print('added Id ' + str(self.controller.CameraPresets[PresetIndex].presetId)
                                            + ' at index ' + str(PresetIndex))
                                i+=1
                            i+=1

                    elif (Shell.StartPhrasePresetDefinedResult.match(ResponseLine)):
                        if (ResponseLine.find('True') > 0):
                            iStart=ResponseLine.find('Preset ')+7
                            iEnd=ResponseLine.find(' Defined')
                            presetIndex=int(ResponseLine[iStart:iEnd])
                            self.controller.CamerasPresets[presetIndex]=CameraPresetPanel(
                                self.controller.Frame_PresetsContainer.contents, presetIndex, cameraId=0)
                            self.controller.shell.send(
                                'xStatus Preset '+str(presetIndex)+' Description\n')

                    elif (Shell.StartPhrasePresetDescriptionResult.match(ResponseLine)):
                        iStart=ResponseLine.find('Preset ')+7
                        iEnd=ResponseLine.find(' Description')
                        presetIndex=int(ResponseLine[iStart:iEnd])

                        iStart=ResponseLine.find('"')
                        iEnd=ResponseLine.rfind('"')

                        if (iStart > 0):
                            description=ResponseLine[iStart+1:iEnd]
                            if (self.controller.CamerasPresets[presetIndex]):
                                self.controller.CamerasPresets[presetIndex].setContents(name=description)

                    elif (Shell.StartPhraseCameraConnected.match(ResponseLine)):
                        sIndex = ResponseLine.find(': ')+2
                        boolConnected = ResponseLine[sIndex:] == 'True'
                            
                        #debug: force UI to think cameras 2 and 3 are always connected
                        if (debug.forceCameraConnection and (2 <= cameraNumber <= 3)): boolConnected = True

                        self.controller.CameraAvailable(cameraNumber, boolConnected)
                        if (Camera.selected is None):
                            self.controller.cameras[cameraNumber].select()
                        debug.print('Camera ' + str(cameraNumber) + ' Status: ' + str(boolConnected))
            #if (Settings.printVerbose.get()):debug.printCodec('^^^^')