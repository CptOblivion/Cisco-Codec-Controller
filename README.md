# Cisco-Codec-Controller

This project is for controlling these cool cameras that my brother and dad have.


To install the SSH package, use:
    Windows:
        'py -m pip install paramiko'
        'py -m pip install pygame'

    Mac: (replace X.X with the version number)
        'pythonX.X -m pip install paramiko'
        'pythonX.X -m pip install pygame'

    Linux: (untested)


(at some point in the future) to run locally, clone this repo and run `docker compose` or like `make backend` or something.

\b Roadmap: \b

#TODO: nudge focus +- bindings

#TODO: present camera presets as a grid (column is camera number, row is preset list order)
#TODO: editable field for coinfig panel update frequency
#TODO: treat midi note on with velocity 0 as note off instead
#TODO: more icons for buttons
#TODO: rename bindings? icons?
#   on binding name change, make sure to keep track of old names in a dict linked to new names, so we can update old ini files automatically
# maybe instead of linked to new names, link them to the command instead- that way they'll load into the program as originally intended, and then on ini save be renamed to the new name
#TODO: autofocus on recenter?

#TODO: get list of prefab commands to include

#TODO: more graceful handling of bad ini values

#TODO: optional dropdown for preset name in bindings (populate with current list of preset names)
#TODO: similar dropdown for midi controller names (with "any" and [current value] also in the list)
#TODO: reconnect button (for if codec loses power/internet)
#TODO: disable interface if there are no cameras, or when connection is lost

#TODO: solve bug with tkinter thread complaints (caused by opening settings from launch screen, and then loading the main program)
# fallback hacky fix idea: closing settings on the launch screen restarts the whole program (don't use this until all other ideas are exhausted)
#possibility: instead of erasing the contents of the window, just destroy the whole window and start fresh after ssh connect

#TODO: class for each kind of input that directly controls camera, where when one class starts controlling camera all other classes must wait until that one relinquishes control

#TODO: button to reset bindings to default (also, a default button on each individual control?)
#TODO: when binding change is made, indicate next to save button that there are unsaved changes, also check for conflicts

#TODO: more extensive midi CC support:
#   motorized faders, screen feedback (generally, send updates back into controller)
#   endless encoders
#   for absolute inputs, try a mode where the fader/knob has to go to the software position before we set new values (prevent CC snap on moving control after software position changed)

