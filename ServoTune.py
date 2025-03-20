#!/usr/bin/python3
#
# Dynamic DMM Servo parameter tuning program.
#
# This tool updates the servo as soon as a slider is moved so the effect of a
# parameter change is immediatly noticeable.  DMM already provides a windows
# application for doing this, but it doesn't update the servo as the slider
# is moved.  I wrote this program to make tuning more convenient and better
# show the effect of parameter changes in a YouTube video.
#
# Matthias Wandel, January-March 2025
import time
import tkinter as tk
from tkinter import ttk
import dmmlib as dmm # My little dmm servo library
import scope

sliders = [0]*31
slider_value_labels = [0]*31
DriveStatus = -1
#----------------------------------------------------------------------------
# Instantiate the user interface window
#----------------------------------------------------------------------------
def CreateWindow():
    global root, sliders_info, current_values, label_ratio, label_status
    # Create the main window
    root = tk.Tk()
    root.title("DMM servo tuner.  No controller connected")


    # Configure grid
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=0)
    root.rowconfigure(1, weight=1)
    root.rowconfigure(2, weight=0)


    # Create a frame for sliders
    slider_frame = ttk.Frame(root, padding="10")
    slider_frame.grid(row=0, column=0, sticky="nswe")

    # Slider labels and their command IDs and initial values
    #                ID, Initial, Name
    sliders_info = [(-1, 1, "PID control parameters:"),
                    (0x10, 50,"Overall Gain"),
                    (0x11, 10,"Speed Gain"),
                    (0x12, 10,"Integral Gain"),
                    (-1, 0, "Torque filter constant:"),
                    (0x13,127,""),
                    (-1, 1, "S-curve parameters:"),
                    (0x14,  80,"Max Speed"),
                    (0x15, 29,"Max Accel")]

    # Sliders last known value for detecting change
    current_values = [0]*31

    RowNum = i = 0
    for id,initial_pos,labeltext in sliders_info:

        if id == -1: # its a label line
            label = ttk.Label(slider_frame, text=labeltext)
            if initial_pos: label.config(font=("Helvetica", 12, "bold"))
            else: label.config(font=("Helvetica", 10))
            label.grid(row=RowNum, column=0, columnspan = 2, sticky=tk.W, padx=5, pady=5)
            RowNum += 1
            continue

        # Slider label (left of slider)
        label = ttk.Label(slider_frame, text=labeltext)
        label.grid(row=RowNum, column=0, sticky=tk.W, padx=5, pady=5)
        label.config(font=("Helvetica", 10))

        # Slider
        current_value = tk.IntVar(value=initial_pos)
        slider = ttk.Scale(slider_frame, from_=1, to=127, orient="horizontal", variable=current_value, length=300)
        slider.grid(row=RowNum, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        current_values[id] = initial_pos
        sliders[id] = slider

        # Current value display (right of slider)
        value_label = ttk.Label(slider_frame, text=str(initial_pos), width=3, anchor="e")
        value_label.config(font=("Helvetica", 12, "bold"))
        value_label.grid(row=RowNum, column=2, sticky=tk.W, padx=5, pady=5)
        slider_value_labels[id] = value_label

        # Update the value display and send new value to the servo controller
        def on_slider_change(Event=None, s_num=id, var=current_value):
            value = var.get()
            if value != current_values[s_num]:
                current_values[s_num] = value
                slider_value_labels[s_num].config(text=str(value))
                print("send new value")
                dmm.SendCommand(s_num, value) # Send to servo controller

        slider.bind("<Motion>", on_slider_change)
        slider.bind("<ButtonRelease-1>", on_slider_change)

        RowNum += 1
        i += 1

    # Show the read back gear ratio
    label = ttk.Label(slider_frame,text="Gear ratio")
    label.grid(row=RowNum, column=0, sticky=tk.W, padx=5, pady=5)
    label.config(font=("Helvetica", 10))

    label_ratio = ttk.Label(slider_frame, text="Not connected")
    label_ratio.config(font=("Helvetica", 10, "bold"))
    label_ratio.grid(row=RowNum, column=1, sticky=tk.W, padx=5, pady=5)

    RowNum += 1

    # Show the status
    label = ttk.Label(slider_frame,text="Status")
    label.grid(row=RowNum, column=0, sticky=tk.W, padx=5, pady=5)
    label.config(font=("Helvetica", 10))

    label_status = ttk.Label(slider_frame, text="Not connected")
    label_status.config(font=("Helvetica", 10, "bold"))
    label_status.grid(row=RowNum, column=1, sticky=tk.W, padx=5, pady=5)

    # Add a row of action buttons below the sliders
    button_frame = ttk.Frame(root, padding="10")
    button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

    btnlist = [(0,0,"Drive Reset", ButtonDriveReset),
               (0,1,"Drive Enable", dmm.DriveEnable),
               (0,2,"Drive Disable", dmm.DriveDisable),
               (0,3,"Read all", ReadAllParameters),
               (1,0,"Motion Start", ButtonStartMotion),
               (1,1,"Motion Stop", ButtonStopMotion)]

    for brow, col, l_text,action in btnlist:
        button = ttk.Button(button_frame, text=l_text, command=action)
        button.grid(row=brow, column=col, padx=5, pady=5)

    #------------------------------------------------------------

    # Right side - Scope canvas
    scope_frame = tk.Frame(root)
    scope_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

    scope_frame.rowconfigure(0, weight=0)
    scope_frame.rowconfigure(1, weight=1)
    scope_frame.rowconfigure(2, weight=0)
    scope_frame.columnconfigure(0, weight=1)

    scope_label_top = tk.Label(scope_frame, text="Scope")
    scope_label_top.config(font=("Helvetica", 10, "bold"))
    scope_label_top.grid(row=0, column=0, sticky="ew")

    canvas = tk.Canvas(scope_frame, bg="gray")
    canvas.grid(row=1, column=0, padx = 5, sticky="nsew")

    # Add a row of action buttons below the scope
    scope_button_frame = ttk.Frame(root, padding="10")
    scope_button_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))

    btnlist = [(0,"Scope start", scope.start_aquring),
               (1,"Scope stop", scope.stop)]

    for col,l_text,action in btnlist:
        button = ttk.Button(scope_button_frame, text=l_text, command=action)
        button.grid(row=0, column=col, padx=5, pady=5)

    #------------------------------------------------------------

    # Schedule initializing servo.
    root.after(1, InitServo)

    scope.canvas = canvas # Share it with scope module
    scope.root = root

#----------------------------------------------------------------------------
# Decode drive status
#----------------------------------------------------------------------------
def ShowDriveStatus(status=-1):
    global DriveStatus
    if status == -1:
        if dmm.ReplyValues[0x19] == 1000000000:
            status = -1
        else:
            status = dmm.ReplyValues[0x19]

    if status == DriveStatus: return; # unchanged
    DriveStatus = status

    if status == -1:
        sstr = "Not connected to controller"
    else:
        # The "Busy" and "Frewheel" bits of the status don't fully amke sense to me
        # how they are reported, but I'm just printing what its supposed to say.
        sstr = "Busy, " if status & 1 else "OnPos, "
        sstr += "Freewheel, " if status & 2 else "Engaged, "

        # The error starus bits typically go to "lost phase" or "overheat"
        # When the servo is overloaded and gives up.
        sstr += ["Ok","Lost phase","Overcurrent","Overheat","CRC error","?5?", "?6?","?7?"][(status >> 2)&7]
        sstr += ",  in S-curve" if status & 0x20 else ""

    label_status.config(text=sstr)

#----------------------------------------------------------------------------
# Send all slider parameters to the servo and read gear ratio
#----------------------------------------------------------------------------
def SendAllParameters():
    print("Sending servo parameters")
    print(current_values)
    for s in range(0,len(sliders_info)):
        id = sliders_info[s][0]
        if id > 0:
            dmm.SendCommand(sliders_info[s][0], current_values[id])
    dmm.RecvData()

#----------------------------------------------------------------------------
# Read servo motion parameters and set sliders to them.
#----------------------------------------------------------------------------
def ReadAllParameters():
    print("Read all parameters")
    # Request all parameters.
    dmm.RecvData() # Clear out received stuff so far.

    ParmsGet = ["Drive_Status","MainGain","SpeedGain","IntGain","TrqCons","HighSpeed","HighAccel","GearNumber"]
    for p in ParmsGet: dmm.SendCommand("Read_"+p) # request parameters

    dmm.ReplyValues = [1000000000]*32 # Erase previous decoded replies
    time.sleep(0.15) # Need to wati a bit for all the replies to be ready.
    dmm.RecvData() # decode all the replies from serial.

    ReplyIds = [0x10,0x11,0x12, # MainGain, SpeedGain, IntGain
                0x13,0x14,0x15, # TrqConst, HighSpeed, HighAccel
                0x18, 0x19] # Gear ratio, Drive Status

    for s in ReplyIds:
        recvd = dmm.ReplyValues[s]
        if recvd == 1000000000:
            print("Did not get %02x"%(s))
            continue
        elif s == 0x18: # Gear ratio
            label_ratio.config(text="4096/"+str(recvd))
            continue
        if s == 0x19: # Drive status
            ShowDriveStatus(recvd)
            continue
        sliders[s].set(recvd)
        slider_value_labels[s].config(text=str(recvd))
        current_values[s] = recvd

#----------------------------------------------------------------------------
# Initialize the servo control parameters after the window is up.
#----------------------------------------------------------------------------
def InitServo():
    ret = dmm.FindController()
    if not ret:
        # No controller found.
        import tkinter.messagebox
        tk.messagebox.showwarning(title="Servo tuner", message="No DMM controller found", parent=root)
        return
    root.title("DMM servo tuner.  Connected %s, ID=%d"%(ret))

    #SendAllParameters()

    ReadAllParameters()

#----------------------------------------------------------------------------
# Functions for button push actions
#----------------------------------------------------------------------------
def ButtonDriveReset():
    dmm.DriveReset()
    TestMotionActive = 0
    dmm.ReplyValues = [1000000000]*32 # Erase previous decoded replies
    time.sleep(0.2)
    dmm.ReqDriveStatus()
    SendAllParameters() # Put our parameters back on the servo
    dmm.RecvData(0.1)
    ShowDriveStatus()

def PeriodicMotion():
    # this called periodically after motion start button is pushed.
    global TestMotionActive
    if not TestMotionActive: return
    #print("Move to:",TestMotionActive & 0xfffe)
    dmm.SendCommand("Go_Absolute_Pos", TestMotionActive & 0xfffe)
    dmm.RecvData()
    TestMotionActive ^= 4096
    root.after(1200,PeriodicMotion)
    dmm.RecvData()
    ShowDriveStatus()

def ButtonStartMotion():
    global TestMotionActive
    print("Start test motion")

    dmm.ReqDriveStatus() # Update drive status (in case that prevents test motion)
    dmm.RecvData(0.1)
    ShowDriveStatus()

    if TestMotionActive: return # Don't start more than one!
    #dmm.SendCommand("Set_Origin")
    dmm.DriveEnable()
    TestMotionActive = 1
    PeriodicMotion()

def ButtonStopMotion():
    global TestMotionActive
    TestMotionActive = 0
    dmm.ReqDriveStatus()
    dmm.RecvData(0.1)
    ShowDriveStatus()

# Start the Tkinter main window and event loop
dmm.ShowSerialBytes = True
TestMotionActive = 0

CreateWindow()
root.mainloop()

# On mainloop exit, window is closed.  Disable drive to be safe.
dmm.DriveDisable()
