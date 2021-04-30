from Helpers import *
from configparser import ConfigParser

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
        Settings.printVerbose=tk.IntVar()
        Settings.printVerbose.set(int(Settings.config['Startup']['PrintVerbose']))
        Settings.muteCodecResponse=tk.IntVar()
        Settings.muteCodecResponse.set(int(Settings.config['Startup']['MuteCodecResponse']))

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

    def toggleVerboseDebugPrints():
        Settings.config['Startup']['PrintVerbose']=str(Settings.printVerbose.get())
        Settings.SaveConfig()
    def toggleMuteCodecPrints():
        Settings.config['Startup']['MuteCodecResponse']=str(Settings.muteCodecResponse.get())
        Settings.SaveConfig()