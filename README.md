# Cisco-Codec-Controller

This project is for controlling these cool cameras that my brother and dad have.


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
