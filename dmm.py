#!/usr/bin/python3
#
# A collection of various routines I used while testing the DMM servo motors
# Tested with DYN2-T 1A6S-00 sevo controller
#
# Matthias Wandel January 2024
import sys, time, signal
import dmmlib as dmm # Import my serial communications routines.

#===========================================================================================
# When aborting, disable the motor cause it might be going nuts!
#===========================================================================================
def Control_C_Abort(signal, frame):
    print("Abort -- disable drive\n");
    dmm.DriveDisable()
    dmm.RecvData()
    sys.exit(0)

signal.signal(signal.SIGINT, Control_C_Abort)
#===========================================================================================
# Read all the parameters from the controller
#===========================================================================================
def ReadAllParameters():
    for key in range(0,31):
        name = dmm.SendCommandLookup[key]
        if name.startswith("Read_"):
            #print (name)
            dmm.SendCommand(key)
            dmm.RecvData()

    print("Values:",dmm.ReplyValues)

#===========================================================================================
# Read all the parameters from the controller
#===========================================================================================
def ShowDriveStatus():
    dmm.SendCommand("Read_Drive_Status")
    dmm.RecvData()
    DriveStatus = dmm.ReplyValues[0x19]
    if DriveStatus == 14: DriveStatus = "Over Heat"
    if DriveStatus == 46: DriveStatus = "Over Heat"
    if DriveStatus == 6:  DriveStatus = "Lost Phase"
    if DriveStatus == 38: DriveStatus = "Lost Phase"
    if DriveStatus == 32: DriveStatus = "Servo OnPos"
    print("Driver Status:",DriveStatus)

#===========================================================================================
# Plot the torque for a specified number of seconds
#===========================================================================================
def TorquePlot(duration): # Plot torque reading while raising and lowering weight
    endtime = time.time()+duration
    dmm.ShowReplies = False
    while True:
        dmm.ReqTorqCurrent()
        if time.time() > endtime: break
        dmm.RecvData()
        Torque = dmm.ReplyValues[0x1e]
        numchars = int(abs(Torque) / 10)
        if numchars > 100: numchars = 100
        Str = ("+" if Torque > 0 else "-")*numchars
        print("%6d"%(Torque),Str+"##")

#===========================================================================================
# Try some motion in constant speed mode.
#===========================================================================================
def ConstSpeedTest():
    print("Constant speed test")
    dmm.SendCommand("Set_MainGain", 25)
    dmm.SendCommand("Set_SpeedGain", 50)
    dmm.SendCommand("Set_IntGain", 1)
    dmm.SendCommand("Set_TrqCons", 100)
    dmm.SendCommand("Set_HighAccel", 30)
    dmm.SendCommand("Set_HighSpeed", 20)
    dmm.SendCommand("Set_TrqCons", 80)

    dmm.SendCommand("Turn_ConstSpeed", -3000)
    start = time.time()
    stop_sent = False
    while True:
        dmm.ReqMotorSpeed()
        dt = time.time()-start
        if dt > 0.5 and not stop_sent:
            print("Set speed zero")
            dmm.SendCommand("Turn_ConstSpeed", 0)
            stop_sent = True
        if dt > 1: break
        print("t=%5.3f "%(dt), end="")
        dmm.RecvData()

    dmm.SendCommand("Turn_ConstSpeed", 0)
    dmm.RecvData()

#===========================================================================================
# Testing reading back of position
#===========================================================================================
def ReadPositionTest():
    print("Read position test")
    #import bignum
    #bignum.SetPos(6)
    dmm.DriveDisable()
    dmm.ShowReplies = False
    HashLine =  "$#########"*10
    BlankLine = "|---------"*10+"|"

    while True:
        dmm.ReqPosRead()
        time.sleep(0.05)
        dmm.RecvData()
        deg = dmm.ReplyValues[0x1b]*360/65536
        degfrac = int((deg+1000-int(deg+1000))*100)
        hashes = HashLine[:degfrac]+BlankLine[degfrac:]
        print("Deg=%7.2f"%(deg), hashes)
        #bignum.ShowBigNum("%6.2f"%(deg))
        time.sleep(0.055)

#===========================================================================================
# Drive disable, read back position.
#===========================================================================================
def DriveDisable():
    print("Freewheel test, turn motor manually")
    dmm.ShowRepies = True

    dmm.DriveDisable()
    dmm.RecvData()

    while True:
        dmm.RecvData()
        dmm.ReqPosRead()
        time.sleep(0.1)


#===========================================================================================
# Manually position the motor.
#===========================================================================================
def Jog():
    import keyboard # Keyboard module, requires "pip3 install keyboard"

    dmm.SendCommand("Set_MainGain", 10)
    dmm.SendCommand("Set_SpeedGain", 120)
    dmm.SendCommand("Set_IntGain", 12)
    dmm.SendCommand("Set_TrqCons", 127)
    dmm.SendCommand("Set_HighAccel", 5)
    dmm.SendCommand("Set_HighSpeed", 5)
    dmm.RecvData()
    dmm.DriveEnable()

    # Initialize the position
    global position
    position = 0

    def update_position(amount):
        global position
        position += amount
        print("Go to deg: %6.2f"%(position))
        dmm.SendCommand("Go_Absolute_Pos", int(position*16384/360))
        dmm.RecvData()

    # Define key press handlers
    keyboard.on_press_key("d", lambda _: update_position(1))
    keyboard.on_press_key("e", lambda _: update_position(-1))
    keyboard.on_press_key("left", lambda _: update_position(0.1))
    keyboard.on_press_key("right", lambda _: update_position(-0.1))
    keyboard.on_press_key("up", lambda _: update_position(6))
    keyboard.on_press_key("down", lambda _: update_position(-6))
    keyboard.on_press_key("page up", lambda _: update_position(30))
    keyboard.on_press_key("page down", lambda _: update_position(-30))

    # Keep the program running until 'Esc' is pressed
    keyboard.wait('esc')
    dmm.RecvData()
    sys.exit(0)


#===========================================================================================
# Catapulting test, used in December 2024 video.
# Uses different speed and acceleration paramters for
# different part of the motion, as throwing is at maxim um speed, but pickup
# from marble loader needs to proceed gently to not throw marbles.
#===========================================================================================
def Catapult():
    dmm.DriveEnable()
    dmm.SendCommand("Set_MainGain", 30)
    dmm.SendCommand("Set_SpeedGain", 5)
    dmm.RecvData()
    dmm.SendCommand("Set_IntGain", 1)
    dmm.RecvData()
    dmm.SendCommand("Set_TrqCons", 30)
    dmm.SendCommand("Set_HighAccel", 20) # Max allowed acceleration
    dmm.SendCommand("Set_HighSpeed", 20)  # Maximum speed
    dmm.RecvData()
    dmm.SendCommand("Go_Absolute_Pos", 0)
    time.sleep(0.5)

    while True:
        # Clear loading position
        dmm.SendCommand("Set_HighSpeed", 2)  # Maximum speed
        dmm.SendCommand("Go_Absolute_Pos", -1200)
        time.sleep(0.5)
        dmm.RecvData()

        # set parameters for the shot
        dmm.SendCommand("Set_SpeedGain", 6)
        gentle = 1
        if gentle:
            # gentle shot for testing.
            # Move part way up for shorter stroke
            dmm.SendCommand("Set_HighSpeed",6)
            dmm.SendCommand("Go_Absolute_Pos", -6000)
            time.sleep(0.2)
            dmm.SendCommand("Set_HighSpeed", 55)
            dmm.SendCommand("Set_HighAccel", 30)
            dmm.RecvData()
            time.sleep(0.4)

            dmm.SendCommand("Go_Absolute_Pos", -34000)
            time.sleep(0.4)
        else:
            # full power shot
            dmm.SendCommand("Set_HighSpeed",255)
            dmm.SendCommand("Set_HighAccel", 1200)
            dmm.SendCommand("Go_Absolute_Pos", -28000)
            time.sleep(0.2)
        dmm.RecvData()
        print("-----shot done----")

        # Return most of the way
        dmm.SendCommand("Set_HighSpeed",20)
        dmm.SendCommand("Set_HighAccel", 20)
        dmm.SendCommand("Go_Absolute_Pos", -1000)
        time.sleep(0.3)
        dmm.RecvData()

        # Gentle loading stroke
        dmm.SendCommand("Set_HighSpeed",3)

        # Go to loading position
        dmm.SendCommand("Go_Absolute_Pos", 0)
        time.sleep(0.6)
        dmm.RecvData()

#===========================================================================================
# Code I wrote for looking into new acceleration parameter not becoming active until
# a motion is completed.
#===========================================================================================
def BackAndForth():
    print("Back and forth parameter update test")
    time.sleep(0.1)
    dmm.SendCommand("Set_MainGain", 30)
    dmm.SendCommand("Set_SpeedGain", 5)
    dmm.SendCommand("Set_IntGain", 1)
    dmm.SendCommand("Set_TrqCons", 30)
    dmm.SendCommand("Set_HighAccel", 40) # Max allowed acceleration
    dmm.SendCommand("Set_HighSpeed", 100)  # Maximum speed
    dmm.RecvData()
    dmm.DriveEnable()
    dmm.DriveEnable()
    dmm.SendCommand("Go_Absolute_Pos", 0)
    dmm.RecvData()
    time.sleep(0.5)

    while True:
        dmm.SendCommand("Set_HighAccel", 20)
        dmm.SendCommand("Go_Absolute_Pos", 0)
        time.sleep(0.4)
        # If above delay is 0.3 seconds, the previous motion won't be complete
        # and the new acceleration won't become active until a motion has completed
        dmm.SendCommand("Set_HighAccel", 100)
        dmm.SendCommand("Go_Absolute_Pos", 16384)
        time.sleep(0.5)
        dmm.SendCommand("Go_Absolute_Pos", 32768)
        time.sleep(0.5)

#===========================================================================================
# Hold position
#===========================================================================================
def PositionHold():
    print("Hold position test")
    dmm.SendCommand("Set_MainGain", 25)
    dmm.SendCommand("Set_SpeedGain", 50)
    dmm.SendCommand("Set_IntGain", 30)
    dmm.SendCommand("Set_TrqCons", 100)
    dmm.SendCommand("Set_HighAccel", 20)
    dmm.SendCommand("Set_HighSpeed", 20)
    dmm.RecvData()
    dmm.DriveEnable()
    dmm.RecvData()
    dmm.ShowReplies = False
    while True:
        time.sleep(0.08)
        print("Torque: ",end="")
        dmm.ReqTorqCurrent()
        dmm.RecvData()
        Torque = dmm.ReplyValues[0x1e]
        Str = ("+" if Torque > 0 else "-")*int(Torque/10)
        print("%6d"%(Torque),Str+"##")

#===========================================================================================
# Move like the second hand on a clock
#===========================================================================================
def Clock():
    print("Clock seconds hand test")
    dmm.SendCommand("Set_MainGain", 18)
    dmm.SendCommand("Set_SpeedGain", 63)
    dmm.SendCommand("Set_IntGain", 1)
    dmm.SendCommand("Set_TrqCons", 63)
    dmm.SendCommand("Set_HighSpeed", 61)
    dmm.SendCommand("Set_HighAccel", 47)
    dmm.SendCommand("Turn_ConstSpeed", 0)

    dmm.RecvData()
    dmm.DriveEnable()
    dmm.SendCommand("Set_Origin", 20)
    xtra_turns = 0
    #time.sleep(60)

    for a in range (0,1200):
        angle = (a/60.0+a*xtra_turns)*16384
        dmm.SendCommand("Go_Absolute_Pos", int(angle))
        dmm.RecvData()
        time.sleep(0.99)

    dmm.DriveDisable()


#===========================================================================================
# Test encoder accuracy, two motors coupled together
#===========================================================================================
def EncoderAccuracy():
    print("Encoder accuracy test")
    use_stepper = True
    STEPS_PER_TURN=6400
    #dmm.ShowSerialBytes = True

    # Configure both motors
    for id in range(20,22):
        dmm.Controller_ID = id
        print ("Configure controller with id",id)
        dmm.DriveReset()
        time.sleep(0.2)
        dmm.DriveDisable()
        dmm.SendCommand("Set_MainGain", 50)
        dmm.SendCommand("Set_SpeedGain", 30)
        dmm.SendCommand("Set_IntGain", 1)
        dmm.SendCommand("Set_TrqCons", 80)
        dmm.SendCommand("Set_HighAccel", 20)
        dmm.SendCommand("Set_HighSpeed", 20)
        dmm.RecvData()
        dmm.SendCommand("Set_Origin")

    if not use_stepper:
        dmm.Controller_ID = 20
        dmm.DriveEnable()
    else:
        import stepper as stepper

    readings_per_turn = 50
    num_turns = 6
    differences = [0]*(readings_per_turn*num_turns)

    dmm.ShowReplies = False
    old_steps = 0
    for a in range (0,readings_per_turn*num_turns):

        angle = int(((a+1)/readings_per_turn)*360)
        if not use_stepper:
            dmm.SendCommand("Go_Absolute_Pos", int(angle/360*16384))
            dmm.RecvData()
            time.sleep(0.2)

            # Read the driving motor's encoder
            dmm.Controller_ID = 21
            dmm.ReqPosRead()
            dmm.RecvData()
            angle_driver = -dmm.ReplyValues[0x1b]/65536*360
        else:
            abs_steps = int(angle*STEPS_PER_TURN/360)
            dosteps = abs_steps - old_steps
            stepper.DoStepsRamp(-dosteps,0.3)
            old_steps = abs_steps
            angle_driver = angle
            time.sleep(0.3)

        # Read the driven motor's encoder
        dmm.Controller_ID = 20
        dmm.ReqPosRead()
        dmm.RecvData()
        angle_driven = dmm.ReplyValues[0x1b]/65536*360
        diff = angle_driven-angle_driver
        print("%7.2f, %7.2f,   %6.2f"%(angle_driver,angle_driven,diff))
        differences[a] = diff

    print("\nDegree differences results:")
    for a in range (0, readings_per_turn*2):
        for b in range (0, num_turns, 2):
            print ("%6.2f"%(differences[a+b*readings_per_turn]), end=",")
        print("")
    dmm.DriveDisable()


#===========================================================================================
# Test how fast we can run a fan blade before motor gets overloaded
#===========================================================================================
def FanSpeed():
    print("Fan max speed test")
    dmm.SendCommand("Set_MainGain", 2)
    dmm.SendCommand("Set_SpeedGain", 127)
    dmm.SendCommand("Set_IntGain", 1)
    dmm.SendCommand("Set_TrqCons", 127)
    dmm.SendCommand("Set_HighAccel", 20)
    dmm.SendCommand("Set_HighSpeed", 30)
    dmm.SendCommand("Turn_ConstSpeed", 0)
    dmm.RecvData()
    dmm.DriveEnable()

    set_speed = 1500
    increment_count = 10
    max_torque_readings = 0
    decel_mode = False

    torque_avg_num = 0
    torque_avg_sum = 0

    report_str = ""

    dmm.ShowReplies = False
    while True:
        print("RPM:%4d Torque:"%(set_speed),end="")
        dmm.ReqTorqCurrent()
        dmm.RecvData()
        Torque = dmm.ReplyValues[0x1e]
        numchars = int(abs(Torque) / 10)
        if numchars > 100: numchars = 100
        Str = ("+" if Torque > 0 else "-")*numchars
        print("%3d"%(Torque),Str+"##")
        torque_avg_sum += Torque
        torque_avg_num += 1
        increment_count -= 1

        if abs(Torque) >= 700: max_torque_readings += 1
        if max_torque_readings >=8:
            print("Finish test")
            break
 
        if increment_count == 0:
            torque_avg = torque_avg_sum/torque_avg_num
            torque_avg_num = 0
            torque_avg_sum = 0

            res = "Speed %4d average torque %d"%(set_speed, torque_avg)
            print(res)
            report_str += res+"\n"
            if set_speed == 0: break
            increment_count = 7
            if decel_mode:
                dmm.DriveDisable() # Let it idle down to not reverse drive the supply
                set_speed = 0
            else:
                # Reported torque shoots up asymptotically at some point,
                # largely based on supply voltage.
                if set_speed < 2500:
                    set_speed += 50
                else:
                    set_speed += 20
            print("Set speed to",set_speed)
            dmm.SendCommand("Turn_ConstSpeed", -set_speed)

    dmm.DriveDisable()
    #print(report_str)
    ShowDriveStatus()


#===========================================================================================
# Test lifting up 8 lb barbell weight with a pulley to check torque, using constant speed mode
#===========================================================================================
def WeightLift():
    print("Weight lifting torque test, by turn const speed")
    dmm.SendCommand("Set_MainGain", 2)
    dmm.SendCommand("Set_SpeedGain", 127)
    dmm.SendCommand("Set_IntGain", 1)
    dmm.SendCommand("Set_TrqCons", 127)
    dmm.SendCommand("Set_HighAccel", 20)
    dmm.SendCommand("Set_HighSpeed", 30)
    dmm.SendCommand("Turn_ConstSpeed", 0)
    dmm.RecvData()
    dmm.DriveEnable()

    RaiseTime = 14
    print("Raise weight")
    dmm.SendCommand("Turn_ConstSpeed", 24)
    TorquePlot(RaiseTime)
    print("Hold at top")
    dmm.SendCommand("Turn_ConstSpeed", 0)
    TorquePlot(0.5)
    print("Lower Weight")
    dmm.SendCommand("Turn_ConstSpeed", -24)
    TorquePlot(RaiseTime)
    dmm.DriveDisable()
    ShowDriveStatus()

#===========================================================================================
# Test lifting up a 1 kg weight faster speed and acceleration
#===========================================================================================
def WeightLiftPos1Kg(NoSlack):
    print("Weight lifting torque test by go absolute position")

    if NoSlack: # Gentle enough so the rope doesn't go slack
        dmm.SendCommand("Set_MainGain", 5)
        dmm.SendCommand("Set_SpeedGain", 1)
        dmm.SendCommand("Set_IntGain", 2)
        dmm.SendCommand("Set_TrqCons", 127)
        dmm.SendCommand("Set_HighAccel", 4)
        dmm.SendCommand("Set_HighSpeed", 80)
    else:
        dmm.SendCommand("Set_MainGain", 4)
        dmm.SendCommand("Set_SpeedGain", 1)
        dmm.SendCommand("Set_IntGain", 2)
        dmm.SendCommand("Set_TrqCons", 127)
        dmm.SendCommand("Set_HighAccel", 10)
        dmm.SendCommand("Set_HighSpeed", 80)
    
    dmm.SendCommand("Set_Origin")
    dmm.SendCommand("Turn_ConstSpeed", 0)
    dmm.RecvData()
    dmm.DriveEnable()

    dmm.SendCommand("Go_Absolute_Pos",int(16384*2.5))
    TorquePlot(3)
    dmm.SendCommand("Go_Absolute_Pos",0)
    TorquePlot(3)

    dmm.DriveDisable()
    ShowDriveStatus()


#===========================================================================================
# Find port or specify the serial port and motor controller
#===========================================================================================
if len(sys.argv) > 1 and (sys.argv[1] == "find" or sys.argv[1].startswith("COM")):
    dmm.Controller_ID = 1000000000
    if sys.argv[1] == "find":
        ret = dmm.FindController()
        if ret:
            print("DMM controller found at %s, id=%d"%(ret))
        sys.argv.pop(1)
    elif sys.argv[1].startswith("COM"):
        try:
            dmm.OpenSerial(sys.argv[1],0x7f)
            dmm.Controller_ID = dmm.GetDeviceId()
        except:
            print("Port",sys.argv[1],"Does not exist")
            sys.exit(-1)
        sys.argv.pop(1)

    if dmm.Controller_ID == 1000000000:
        print("No DMM controller found")
        sys.exit(-1)

    if len(sys.argv) == 1: sys.exit(0)
else:
    # Default port and device ID.  just change this to whatever it ends up as on your PC
    # so you don't have tp specify it on the command line every time.
    if sys.platform == "win32":
        default_port = "COM5"
    else:
        default_port = "/dev/ttyS0"
    print("use default port %s, DMM driver id %d"%(default_port, 0))
    dmm.OpenSerial(default_port,20)

dmm.ShowReplies = True
dmm.ShowSerialByttes = False
#===========================================================================================
# Decide which sub-program to run
#===========================================================================================
if len(sys.argv) > 1:
    argument = sys.argv[1]
    if argument == "mon": # Used to monitor serial communications by connecting DMM
                          # controller's serial tx to a second serial port's rx.
        print("Monitoring serial")
        while True:  dmm.RecvData()
    elif argument == "readall": ReadAllParameters()
    elif argument == "status": ShowDriveStatus()
    elif argument == "zero": dmm.SendCommand("Set_Origin") # Set origin to zero.
    elif argument == "home": dmm.SendCommand("Go_Absolute_Pos") # Got to zero
    elif argument == "disable": DriveDisable()
    elif argument == "enable": dmm.DriveEnable() # reenable motor drive
    elif argument == "reset": dmm.DriveReset() # reset motor drive (clears error condition)

    elif argument == "speed":   ConstSpeedTest()
    elif argument == "readpos": ReadPositionTest()
    elif argument == "catapult": Catapult()
    elif argument == "jog": Jog()
    elif argument == "bf": BackAndForth()
    elif argument == "hold": PositionHold()
    elif argument == "clock": Clock()
    elif argument == "enc": EncoderAccuracy()
    elif argument == "fan": FanSpeed()
    elif argument == "lift": WeightLift()
    elif argument == "lift1kgf": WeightLiftPos1Kg(False)
    elif argument == "lift1kg":  WeightLiftPos1Kg(True)
    elif argument == "id": print("Device id = ",dmm.GetDeviceId())
    else:
        print("Argument %s not understood"%(argument))

    sys.exit()
else:
    print("No command specified")
