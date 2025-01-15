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
# Matthias Wandel, January 2025
import time
import tkinter as tk
from tkinter import ttk
import dmmlib as dmm # My little dmm servo library

#----------------------------------------------------------------------------
# Instantiate the user interface window
#----------------------------------------------------------------------------
def CreateWindow():
    global root, sliders_info, current_values, label_ratio
    # Create the main window
    root = tk.Tk()
    root.title("DMM servo tuner.  No controller connected")
    
    # Create a frame for sliders
    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Slider labels and their command IDs and initial values
                    # ID, Initial, Name
    sliders_info = [(0x10, 18,"Overall Gain"),
                    (0x11,  4,"Speed Gain"),
                    (0x12, 24,"Integral Gain"),
                    (0x13,127,"Torque filter const"),
                    (0x14,  8,"Max Speed"),
                    (0x15, 29,"Max Accel")]
    
    # Sliders last known value for detecting change
    current_values = [0]*6
    
    RowNum = i = 0
    for id,initial_pos,labeltext in sliders_info:
    
        # Add slider category labels
        if RowNum == 0 or RowNum == 4:
            t = "PID control" if RowNum==0 else "Additional"
            label = ttk.Label(frame, text=t+" parameters:")
            label.config(font=("Helvetica", 10, "bold"))
            label.grid(row=RowNum, column=1, sticky=tk.W, padx=5, pady=5)
            RowNum += 1
    
        # Slider label (left of slider)
        label = ttk.Label(frame, text=labeltext)
        label.grid(row=RowNum, column=0, sticky=tk.W, padx=5, pady=5)
        label.config(font=("Helvetica", 10))
    
        # Slider
        current_value = tk.IntVar(value=initial_pos)
        slider = ttk.Scale(frame, from_=1, to=127, orient="horizontal", variable=current_value, length=400)
        slider.grid(row=RowNum, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        current_values[i] = initial_pos
    
        # Current value display (right of slider)
        value_label = ttk.Label(frame, text=str(initial_pos), width=3, anchor="e")
        value_label.config(font=("Helvetica", 12, "bold"))
        value_label.grid(row=RowNum, column=2, sticky=tk.W, padx=5, pady=5)
    
        # Update the value display and send new value to the servo controller
        def on_slider_change(event=None, s_num=id, v_label=value_label, var=current_value, index=i):
            value = var.get()
            if value != current_values[index]:
                current_values[index] = value
                v_label.config(text=str(value))
                dmm.SendCommand(s_num, value) # Send to servo controller
    
        slider.bind("<Motion>", on_slider_change)
        slider.bind("<ButtonRelease-1>", on_slider_change)
    
        RowNum += 1
        i += 1
    
    # Show the read back gear ratio
    label = ttk.Label(frame,text="Gear ratio")
    label.grid(row=RowNum, column=0, sticky=tk.W, padx=5, pady=5)
    label.config(font=("Helvetica", 10))
    
    label_ratio = ttk.Label(frame, text="Not connected")
    label_ratio.config(font=("Helvetica", 10, "bold"))
    label_ratio.grid(row=RowNum, column=1, sticky=tk.W, padx=5, pady=5)
    
    # Add a row of action buttons below the sliders
    button_frame = ttk.Frame(root, padding="10")
    button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    for col,l_text,action in [(0,"Drive Reset", ButtonDriveReset),
            (1,"Drive Enable", dmm.DriveEnable), (2,"Drive Disable", dmm.DriveDisable),
            (3,"Motion Start", ButtonStartMotion),     (4,"Motion Stop", ButtonStopMotion)]:
        button = ttk.Button(button_frame, text=l_text, command=action)
        button.grid(row=0, column=col, padx=5, pady=5)

    # Schedule initializing servo.
    root.after(1, InitServo)

#----------------------------------------------------------------------------
# Send all slider parameters to the servo and read gear ratio
#----------------------------------------------------------------------------
def SyncParameters():
    dmm.SendCommand("Read_GearNumber") # we don't set the gear ratio, so read it to know it.

    print("Sending servo parameters")
    for s in range(0,len(sliders_info)):
        dmm.SendCommand(sliders_info[s][0], current_values[s])
    dmm.RecvData()

    # Should have reply for Read_GearNumber by now.
    print("Gear ratio:",dmm.ReplyValues[0x18])
    label_ratio.config(text="4096/"+str(dmm.ReplyValues[0x18]))

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
    SyncParameters()


#----------------------------------------------------------------------------
# Functions for button push actions
#----------------------------------------------------------------------------
def ButtonDriveReset():
    dmm.DriveReset()
    SyncParameters() # Put our parameters back on the servo

def PeriodicMotion():
    # this called periodically after motion start button is pushed.
    global TestMotionActive
    if not TestMotionActive: return
    print("Move to:",TestMotionActive & 0xfffe)
    dmm.SendCommand("Go_Absolute_Pos", TestMotionActive & 0xfffe)
    TestMotionActive ^= 4096
    root.after(1000,PeriodicMotion)
    dmm.RecvData()
    
def ButtonStartMotion():
    global TestMotionActive
    print("Start test motion")
    if TestMotionActive: return # Don't start more than one!
    dmm.SendCommand("Set_Origin")
    dmm.DriveEnable()
    TestMotionActive = 1
    PeriodicMotion()
    
def ButtonStopMotion():
    global TestMotionActive
    TestMotionActive = 0

# Start the Tkinter main window and event loop
dmm.ShowSerialBytes = True
TestMotionActive = 0

CreateWindow()
root.mainloop()

# On mainloop exit, window is closed.  Disable drive to be safe.
dmm.DriveDisable()
