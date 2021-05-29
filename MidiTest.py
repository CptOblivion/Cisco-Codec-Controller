import pygame.midi
from Helpers import *
from Debug import *

class midiDebug():
    def __init__(self):
        self.loadControls()
        self.notes={}
        self.outDevice=self.outputDevicesMidis[3]
        for i in range(121):
            self.outDevice.note_on(i, velocity=0, channel=0)
        
    def loadControls(self):
        pygame.midi.init()
        self.refreshInputDevicesMidi()

    def refreshInputDevicesMidi(self):
        debug.print('midi devices:')
        self.inputDevicesMidis = []
        self.inputDevicesMidiNames = []
        self.outputDevicesMidis = []
        print('count:',pygame.midi.get_count())
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            debug.print(info)
            print(i, info)
            if (info[2]==1):
                self.inputDevicesMidis.append(pygame.midi.Input(i))
            else:
                self.inputDevicesMidis.append(None)
            if (info[3]==1):
                self.outputDevicesMidis.append(pygame.midi.Output(i))
            else:
                self.outputDevicesMidis.append(None)
            self.inputDevicesMidiNames.append(str(pygame.midi.get_device_info(i)[1], 'utf-8'))
    def main(self):
        for device in self.inputDevicesMidis:
            if (device and device.poll()):
                for event in device.read(1024):
                    event = event[0] #strip the timing component, we don't need it
                    channel = event[0] & 0b00001111 #just the 0x1s place
                    command = event[0] & 0b11110000 #just the 0x10s place
                    note=event[1]
                    vel=event[2]
                    if (vel>0):
                        if (not note in self.notes):
                            self.notes[note]=[False, False, False, False]
                        color=0
                        for i in range(len(self.notes[note])):
                            color+= self.notes[note][i]*pow(2,i)
                        color+=1
                        if (color==16): color=0
                        print(color)
                        bits=[int(color & 0b0001),
                              int((color & 0b0010)/2),
                              int((color & 0b0100)/4),
                              int((color & 0b1000)/8)]
                        print(bits)
                        self.notes[note]=bits
                        self.outDevice.note_on(note, velocity=self.getColor(self.notes[note]),
                                               channel=channel)

                    print('channel:', channel, 'command:', command, 'note:', note, 'vel:',vel)
    def getColor(self,bits):
        #r=0,1
        #g=4,5
        #2,3,6 should be 0
        return (bits[0]+bits[1]*2+bits[2]*16+bits[3]*32)
if __name__ == '__main__':
    program=midiDebug()
    while(True):
        program.main()