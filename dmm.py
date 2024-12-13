#!/usr/bin/python3
# Communications routines to communicate with DMM servo controller over serial
# followed by routines to use these routines
#
# Teted with DYN2-T 1A6S-00 sevo controller
# Matthias Wandel December 2024
import sys,time
import serial

# requires "pip3 install pyserial" for serial to be enabled.
#ser = serial.Serial("/dev/ttyS0", 38400) # Linux
ser = serial.Serial("COM1", 38400) # Windows, change to port you are using.

ShowSerialBytes = False
ShowEchoReplies = True

Controller_ID = 0x7f;

# Commands sent to the controller (Page 46 of PDF)
SendCommandIds = {
    "Set_Origin":0x00,         "Go_Absolute_Pos":0x01,    "Make_LinearLine":0x02,
    "Go_Relative_Pos":0x03,    "Make_CircularArc":0x04,   "Assign_Drive_ID":0x05,
    "Read_Drive_ID":0x06,      "Set_Drive_Config":0x07,   "Read_Drive_Config":0x08,
    "RegisterRead_Drive_Status":0x09,                     "Turn_ConstSpeed":0x0a,
    "Square_Wave":0x0b,        "Sin_Wave":0x0c,           "SS_Frequency":0x0d,
    "General_Read":0x0e,       "ForMotorDefine":0x0f,     "Set_MainGain":0x10,
    "Set_SpeedGain":0x11,      "Set_IntGain":0x12,        "Set_TrqCons":0x13,
    "Set_HighSpeed":0x14,      "Set_HighAccel":0x15,      "Set_Pos_OnRange":0x16,
    "Set_GearNumber":0x17,     "Read_MainGain":0x18,      "Read_SpeedGain":0x19,
    "Read_IntGain":0x1a,       "Read_TrqCons":0x1b,       "Read_HighSpeed":0x1c,
    "Read_HighAccel":0x1d,     "Read_Pos_OnRange":0x1e,   "Read_GearNumber":0x1f
}
# Make reverse lookup dictionary for the commands
SendCommandLookup = {}
for key in SendCommandIds: SendCommandLookup[SendCommandIds[key]] = key


# Replies from the controller
RecvReplyIds = {
    0x10:"MainGain",   0x11:"SpeedGain",    0x12:"IntGain",
    0x13:"TrqCons",    0x14:"HighSpeed",    0x15:"HighAccel",
    0x16:"Drive_ID",   0x17:"PosOn_Range",  0x18:"GearNumber",
    0x19:"Status",     0x1a:"Config",       0x1b:"AbsPos32",
    0x1c:"??0x1C??",   0x1d:"Speed",        0x1e:"TrqCurrent",
    0x1f:"??0x1F??"
}

#===========================================================================================
# Send a command to the servo controller
#===========================================================================================
def SendCommand(Command, Value):
    if not -1 <= (Value >> 27) <= 0:
        print ("Value is out of 28 bit range")
        return

    if isinstance(Command, str):
        # For clarity of code, but not efficiency,
        # you can also pass the command as a string.
        Command = SendCommandIds[Command]

    global Motor_ID
    CmdToSend = [0]*2
    CmdToSend[0] = Controller_ID
    CmdToSend[1] = 0x80 | Command & 0x1f

    # Send value MSB first
    for ShiftAmount in range (7*3,-7, -7):
        if ShiftAmount:
            if -1 <= (Value >> (ShiftAmount-1)) <= 0:
                continue # Not sending sign extended bits.

        CmdToSend.append(0x80 | (Value >> ShiftAmount) & 0x7f)

    CmdToSend[1] |= (len(CmdToSend)-3) << 5 # Add the two length bits to second byte.

    # Calculate and add checksum byte
    sum = 0
    for b in CmdToSend: sum += b
    CmdToSend.append((sum & 0x7f) | 0x80)

    if ShowSerialBytes: print ("Sending: ",bytes(CmdToSend))

    ser.write(bytes(CmdToSend))

#===========================================================================================
# Decode a command or reply from serial.
# Not doing anything with the reply except print its contents.
#===========================================================================================
def DecodeCmd(Command):
    global RecvReplyIds
    if ShowSerialBytes: print("Decoding: ",Command)

    # Check MSBs in all subsequent bytes is set.
    for a in range (1,len(Command)):
        if not Command[a] & 0x80:
            print("Command format error")
            return

    # Check the checksum
    checksum = 0
    for a in range (0,len(Command)-1):
        checksum += Command[a]

    if checksum & 0x7f != Command[-1] &0x7f:
        print("Checksum error!")
        return;

    DeviceId = Command[0]
    if DeviceId and not ShowEchoReplies: return

    ReplyId = Command[1] & 0x1f
    if DeviceId:
        ReplyString = SendCommandLookup[ReplyId]
        print("Echo:  ",end="")
    else:
        ReplyString = RecvReplyIds[ReplyId]
        print("Reply: ",end="")

    # Decode the value bytes
    Value = Command[2] & 0x7f
    if Value >= 64: Value -= 128
    for B in Command[3:-1]: Value = Value << 7 | (B & 0x7f)

    print("%s(%02x) Value=%d"%(ReplyString, ReplyId,Value))

#===========================================================================================
# Process accumulated serial bytes and decode them.
#===========================================================================================
BytesGot = bytes([])
def RecvData():
    global BytesGot
    start_time = time.time()
    # Wait .05 seconds for any reply that is on its way.
    while time.time() - start_time < 0.05: 
        if ser.in_waiting > 0: # Read available bytes
            data = ser.read(ser.in_waiting)
            BytesGot += data

    ProcessedTo = 0
    for a in range (0, len(BytesGot)-1):
        if BytesGot[a] & 0x80 == 0:
            ResLen = ((BytesGot[a+1] >> 5)&3) + 4
            #print("len ",ResLen,"have:",len(BytesGot)-a)
            if len(BytesGot) >= a+ResLen:
                DecodeCmd(BytesGot[a:a+ResLen]) # Have a complete packet
                a = a+ResLen
                ProcessedTo = a+ResLen

    BytesGot = BytesGot[ProcessedTo:] # Remove bytes just processed.

#===========================================================================================
#===========================================================================================
# Above is code to handle controller packet format.
#
#
# Below is code that uses these routines to stuff I demonstrated in the video.
#===========================================================================================
#===========================================================================================

#===========================================================================================
# Read all the parameters from the controller
#===========================================================================================
def ReadAllParameters():
    global ShowEchoReplies
    ShowEchoReplies = False
    for key in range(0,31):
        name = SendCommandLookup[key]
        if name.startswith("Read_"):
            #print (name)
            SendCommand(key,0)
            RecvData()
    HideEchoReplies = True

#===========================================================================================
# Try some motion in constant speed mode.
#===========================================================================================
def ConstSpeedTest():
    print("Constant speed test")
    SendCommand(SendCommandIds["Turn_ConstSpeed"], 120)
    RecvData()
    time.sleep(1)
    SendCommand(SendCommandIds["Turn_ConstSpeed"], -140)
    RecvData()
    time.sleep(1)
    SendCommand(SendCommandIds["Turn_ConstSpeed"], 0)
    RecvData()

#===========================================================================================
# Testing reading back of position
#===========================================================================================
def ReadPositionTest():
    global ShowEchoReplies
    print("Read position test")
    SendCommand("Turn_ConstSpeed", 5)
    RecvData()
    SendCommand("Set_MainGain", 20)
    RecvData()

    SendCommand("Set_Drive_Config", 0x20) # Set "let Drive free"
    RecvData()

    SendCommand("Read_Drive_Config", 0x20) # Set "let Drive free"
    RecvData()
    # Set to freewheel command is saved but not acted on.

    SendCommand("Set_Origin", 0)# this command also doesn't work.
    RecvData()

    ShowEchoReplies = False
    while True:
        SendCommand(SendCommandIds["General_Read"], 0x1b)
        #SendCommand(SendCommandIds["General_Read"], 0x1e) # Torque current
        RecvData()
        time.sleep(0.1)

#===========================================================================================
# Drive disable, read back position.
#===========================================================================================
def DriveDisable():
    print("Freewheel test, turn motor manually")
    global ShowEchoReplies
    ShowEchoReplies = False

    SendCommand("General_Read", 0x21)
    RecvData()

    while True:
        RecvData()
        SendCommand(SendCommandIds["General_Read"], 0x1b)
        time.sleep(0.1)


#===========================================================================================
# Manually position the motor.
#===========================================================================================
def Jog():
    import keyboard # Keyboard module, requires "pip3 install keyboard"

    # Initialize the position
    global position
    position = 0

    def update_position(amount):
        global position
        position += amount
        print(f"position: {position}")
        SendCommand("Go_Absolute_Pos", position)
        RecvData()

    # Define key press handlers
    keyboard.on_press_key("up", lambda _: update_position(20))
    keyboard.on_press_key("down", lambda _: update_position(-20))
    keyboard.on_press_key("page up", lambda _: update_position(200))
    keyboard.on_press_key("page down", lambda _: update_position(-200))


    # Keep the program running until 'Esc' is pressed
    keyboard.wait('esc')
    SendCommand("Set_Origin", 0)# this command also doesn't work.
    RecvData()
    sys.exit(0)


#===========================================================================================
# Catapulting test.
# Uses different speed and acceleration paramters for
# different part of the motion, as throwing is at maxim um speed, but pickup
# from marble loader needs to proceed gently to not throw marbles.
#===========================================================================================
def Catapult():
    SendCommand("General_Read", 0x20) # Enable
    SendCommand("Set_MainGain", 30)
    SendCommand("Set_SpeedGain", 5)
    RecvData()
    SendCommand("Set_IntGain", 1)
    RecvData()
    SendCommand("Set_TrqCons", 30)
    SendCommand("Set_HighAccel", 20) # Max allowed acceleration
    SendCommand("Set_HighSpeed", 20)  # Maximum speed
    RecvData()
    SendCommand("Go_Absolute_Pos", 0)
    time.sleep(0.5)

    while True:
        # Clear loading position
        SendCommand("Set_HighSpeed", 2)  # Maximum speed
        SendCommand("Go_Absolute_Pos", -1200)
        time.sleep(0.5)
        RecvData()

        # set parameters for the shot
        SendCommand("Set_SpeedGain", 6)
        gentle = 0
        if gentle:
            # gentle shot for testing.
            # Move part way up for shorter stroke
            SendCommand("Set_HighSpeed",6)
            SendCommand("Go_Absolute_Pos", -6000)
            time.sleep(0.2)
            SendCommand("Set_HighSpeed", 55)
            SendCommand("Set_HighAccel", 30)
            RecvData()
            time.sleep(0.4)

            SendCommand("Go_Absolute_Pos", -34000)
            time.sleep(0.4)
        else:
            # full power shot
            SendCommand("Set_HighSpeed",255)
            SendCommand("Set_HighAccel", 1200)
            SendCommand("Go_Absolute_Pos", -28000)
            time.sleep(0.2)
        RecvData()
        print("-----shot done----")

        # Return most of the way
        SendCommand("Set_HighSpeed",20)
        SendCommand("Set_HighAccel", 20)
        SendCommand("Go_Absolute_Pos", -1000)
        time.sleep(0.3)
        RecvData()

        # Gentle loading stroke
        SendCommand("Set_HighSpeed",3)

        # Go to loading position
        SendCommand("Go_Absolute_Pos", 0)
        time.sleep(0.6)
        RecvData()

#===========================================================================================
# Code I wrote for looking into new acceleration parameter not becoming active until
# a motion is completed.
#===========================================================================================
def BackAndForth():
    print("Back and forth parameter update test")
    SendCommand("General_Read", 0x20) # Enable
    time.sleep(0.1)
    SendCommand("Set_MainGain", 30)
    SendCommand("Set_SpeedGain", 5)
    SendCommand("Set_IntGain", 1)
    SendCommand("Set_TrqCons", 30)
    SendCommand("Set_HighAccel", 40) # Max allowed acceleration
    SendCommand("Set_HighSpeed", 100)  # Maximum speed
    RecvData()
    SendCommand("Go_Absolute_Pos", 0)
    time.sleep(0.5)

    while True:
        SendCommand("Set_HighAccel", 20)
        SendCommand("Go_Absolute_Pos", 0)
        time.sleep(0.4)
        # If above delay is 0.3 seconds, the previous motion won't be complete
        # and the new acceleration won't become active until a motion has completed
        SendCommand("Set_HighAccel", 100)
        SendCommand("Go_Absolute_Pos", 16384)
        time.sleep(0.5)
        SendCommand("Go_Absolute_Pos", 32768)
        time.sleep(0.5)


#===========================================================================================
ShowSerialBytes = False
ShowEchoReplies = True

if len(sys.argv) > 1:
    argument = sys.argv[1]
    if argument == "mon": # Used to monitor serial communications by connecting DMM
                          # controller's serial tx to a second serial port's rx.
        print("Monitoring serial")
        while True:  RecvData()
    elif argument == "readall": ReadAllParameters()
    elif argument == "speed":   ConstSpeedTest()
    elif argument == "readpos": ReadPositionTest()
    elif argument == "catapult": Catapult()
    elif argument == "jog": Jog()
    elif argument == "zero": SendCommand("Set_Origin", 0) # Set origin to zero.
    elif argument == "home": SendCommand("Go_Absolute_Pos", 0) # Got to zero
    elif argument == "disable": DriveDisable()
    elif argument == "enable": SendCommand("General_Read", 0x20) # reenable motor drive
    elif argument == "reset": SendCommand("General_Read", 0x1c) # reset  motor drive
    elif argument == "bf": BackAndForth()
    else:
        print("Argument %s not understood"%(argument))

    sys.exit()
else:
    print("No command specified")
