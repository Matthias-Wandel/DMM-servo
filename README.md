# DMM-servo
Python programs for controlling DMM servo over rs232 inteface.

This is code designed not to be a universal API, but rather something short and simple
so you can read it, understand it, modify it and extend it for your needs.
I wrote this because there weren't any nice code examples for communicating with DMM servo controllers that I could find online.  Put it on github so hoepfully others will be able to find it.

Also includes my ServoTune program, which, on account of being more interactive, I find much more
conveinent for tuning the servo parameters.

<b>Files:</b>

dmmlib.py    -- Serial communications routines to talking to DMM controller

ServoTune.py -- A GUI program for interactively tuning DMM servo parameters

dmm.py       -- Various routines I used to exerecise the servo in my videos.

bugnum.py    -- Print big numbers on the screen, used in some of my tests

scope.py     -- Graphing part of ServoTune program.


