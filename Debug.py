
from helpers import *
import traceback
import datetime

#turning this to True will force the UI to always show Camera 2 and 3 as connected
forceCameraConnection = False
#turning this to true will add a bunch of extra debug prints to the console
verbosePrints = False #TODO: safe to delete?
logfileName = 'Error_Log_'+versionNumber+'.txt'


def log(message):
    if ('printVerbose' in globals() and printVerbose.get()):
        print(message)
def printCodec(message):
    if (not muteCodecResponse.get()):
        print(message)
def writeErrorLog():
    #message=sys.exc_info()
    #TODO: properly handle traceback
    print('crash error:')

    with open(debug.logfileName, 'a') as logfile:
        #traceback.print_exception(message[0], message[1], message[2], file=logfile)
        logfile.write('\n\n'+debug.getDateTime()+'\n')
        traceback.print_exc()
        traceback.print_exc(file=logfile)
        logfile.close()
def getDateTime():
    timestamp=datetime.datetime.now()
    return (timestamp.strftime('%y/%m/%d %H:%M:%S'))

class DummySSH():
    UseDummy=False
    dummyPresetData=('* PresetListResult Preset 1 CameraId: 1\n'
                    '* PresetListResult Preset 1 Name: "Fake_preset"\n'
                    '* PresetListResult Preset 1 PresetId: 1\n'
                    '* PresetListResult Preset 2 CameraId: 1\n'
                    '* PresetListResult Preset 2 Name: "Not_A_Real_Preset"\n'
                    '* PresetListResult Preset 2 PresetId: 2\n'
                    '* PresetListResult Preset 3 CameraId: 2\n'
                    '* PresetListResult Preset 3 Name: "Don\'t_Believe_this_Preset"\n'
                    '* PresetListResult Preset 3 PresetId: 3\n'
                    '* PresetListResult Preset 4 CameraId: 3\n'
                    '* PresetListResult Preset 4 Name: "Definitely_Real_Preset"\n'
                    '* PresetListResult Preset 4 PresetId: 4\n'
                    '* PresetListResult Preset 5 CameraId: 1\n'
                    '* PresetListResult Preset 5 Name: "another"\n'
                    '* PresetListResult Preset 5 PresetId: 5\n')
    def __init__(self):

        #populate the initial response with a handful of things to get us started
        self.responseQueue = ('* Camera 1 Connected: True\n'
                              '* Camera 2 Connected: True\n'
                              '* Camera 3 Connected: True\n'
                              )
        for i in range(3):
            self.responseQueue += ('* Camera ' + str(i+1) + ' Position Focus: 4500\n'
                                '* Camera ' + str(i+1) + ' Position Zoom: 0\n'
                                '* Camera ' + str(i+1) + ' Position Pan: 400\n'
                                '* Camera ' + str(i+1) + ' Position Tilt: 60\n'
                                   )
    def recv_ready(self):
        if (self.responseQueue is not None): return True
        return False
    def recv(self, amount):
        response=self.responseQueue.encode('ASCII')
        self.responseQueue = None
        return response
    def send(self, message):
        if ('xCommand Camera Preset List' in message):
            self.addResponse(DummySSH.dummyPresetData)
    def addResponse(self, message):
        if (self.responseQueue is None): self.responseQueue=message
        else: self.responseQueue += message