# Cisco-Codec-Controller

This project is for controlling these cool cameras that my brother and dad have.

*Running the project with Docker (in theory)*
1. Install Docker: https://docs.docker.com/get-docker/
2. In the root directory for this project, build the Docker image: `docker build -t camcontrol1 .`
3. Run the container, attempting to pass in the display: `docker run -ti --rm  -e DISPLAY=$DISPLAY  -v /tmp/.X11-unix:/tmp/.X11-unix:rw  camcontrol1`
4. Probably get error like `python: can't open file 'CameraController.py DummySSH': [Errno 2] No such file or directory`
5. Double check that the working directory in the image looks right with these commands: 
    `docker run -ti camcontrol1 sh` to run the container and open a shell inside it
    `ls` to list the files in the container. Yep, `CameraController.py` is there. Weird!
6. Try to run the program from within the shell in this container: `python CameraController.py DummySSH`
7. Ah dang it doesn't have access to the `$DISPLAY` environment variable, how do I pass that into the container?
8. Return to local shell with `exit`
9. See if there's anything in the `$DISPLAY` environment variable with `echo $DISPLAY`. Hmmm... nope
10. Cry

To install the SSH package, use:
    Windows:
        'py -m pip install paramiko'
        'py -m pip install pygame'

    Mac: (replace X.X with the version number)
        'pythonX.X -m pip install paramiko'
        'pythonX.X -m pip install pygame'

    Linux: (untested)


(at some point in the future) to run locally, clone this repo and run `docker compose` or like `make backend` or something.

**Roadmap** *(not organized)***:**

* nudge focus +- bindings

* editable field for coinfig panel update frequency
* treat midi note on with velocity 0 as note off instead
* more icons for buttons
* rename bindings? icons?
    * on binding name change, make sure to keep track of old names in a dict linked to new names, so we can update old ini files automatically
    * maybe instead of linked to new names, link them to the command instead- that way they'll load into the program as originally intended, and then on ini save be renamed to the new name
* autofocus on recenter?
* get list of prefab commands to include

* more graceful handling of bad ini values

* optional dropdown for preset name in bindings (populate with current list of preset names)
* similar dropdown for midi controller names (with "any" and [current value] also in the list)
* reconnect button (for if codec loses power/internet)
* disable interface if there are no cameras, or when connection is lost

* solve bug with tkinter thread complaints (caused by opening settings from launch screen, and then loading the main program)
    * fallback hacky fix idea: closing settings on the launch screen restarts the whole program (don't use this until all other ideas are exhausted)
    * possibility: instead of erasing the contents of the window, just destroy the whole window and start fresh after ssh connect

* class for each kind of input that directly controls camera, where when one class starts controlling camera all other classes must wait until that one relinquishes control
* button to reset bindings to default (also, a default button on each individual control?)
* when binding change is made, indicate next to save button that there are unsaved changes, also check for conflicts
* more extensive midi CC support:
    * motorized faders, screen feedback (generally, send updates back into controller)
    * endless encoders
    * for absolute inputs, try a mode where the fader/knob has to go to the software position before we set new values (prevent CC snap on moving control after software position changed)
