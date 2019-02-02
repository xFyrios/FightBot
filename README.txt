Installation &c.

1) Run ./phenny - this creates a default config file
2) Edit ~/.config/default.py
3) Run ./phenny - this now runs phenny with your settings

Enjoy!

-- 
To add new functionality, create new modules in fight/ or edit the existing ones. 
This will provide functionality and can tie into the player and monster modules.
If you are creating a new game (ie. player vs player), place a second module in modules/gazelle/
that contains the IRC commands. You can then import the functionality you need from the fight/ folder.

