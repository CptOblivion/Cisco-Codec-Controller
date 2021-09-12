from helpers import *
import main

#start the actual program
if __name__ == '__main__':
    if (not hasattr(sys, '_MEIPASS')):
        #in the dev environment, let exceptions happen normally
        print('\n~~~~~ running in dev environment ~~~~~\n\n')
        current = main.Main()
        while True:
            current.main()
    else:
        #in the bundled exe:
        #   * catch all exceptions
        #   * write them to the console and a log file
        #   * exit properly so pyinstaller can clean up temp files
        current = Main()
        while True:
            try:
                current.main()
            except tk.TclError:
                sys.exit('Window closed, quitting')
            except:
                debug.writeErrorLog()
                sys.exit('Error log written, quitting')