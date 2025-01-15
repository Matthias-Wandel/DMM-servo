#!/usr/bin/python3
# Communications routines to communicate with DMM servo controller over serial
#
# Tested with DYN2-T 1A6S-00 sevo controller
#
# Matthias Wandel Jauary 2024
import sys, time
import serial  # Requires "pip3 instll pyserial" for serial to be enabled.

# Commands sent to the controller (Page 46 of PDF)
SendCommandIds = {
    "Set_Origin":0x00,         "Go_Absolute_Pos":0x01,    "Make_LinearLine":0x02,
    "Go_Relative_Pos":0x03,    "Make_CircularArc":0x04,   "Assign_Drive_ID":0x05,
    "Read_Drive_ID":0x06,      "Set_Drive_Config":0x07,   "Read_Drive_Config":0x08,
    "Read_Drive_Status":0x09,                     "Turn_ConstSpeed":0x0a,
    "Square_Wave":0x0b,        "Sin_Wave":0x0c,           "SS_Frequency":0x0d,
    "General_Read":0x0e,       "ForMotorDefine":0x0f,     "Set_MainGain":0x10,
    "Set_SpeedGain":0x11,      "Set_IntGain":0x12,        "Set_TrqCons":0x13,
    "Set_HighSpeed":0x14,      "Set_HighAccel":0x15,      "Set_Pos_OnRange":0x16,
    "Set_GearNumber":0x17,     "Read_MainGain":0x18,      "Read_SpeedGain":0x19,
    "Read_IntGain":0x1a,       "Read_TrqCons":0x1b,       "Read_HighSpeed":0x1c,
    "Read_HighAccel":0x1d,     "Read_Pos_OnRange":0x1e,   "Read_GearNumber":0x1f
}

DMM_GENERAL_READ = 0x0e

# Make reverse lookup dictionary for the commands
SendCommandLookup = {}
for key in SendCommandIds: SendCommandLookup[SendCommandIds[key]] = key

# Replies from the controller
RecvReplyIds = {
    0x00:"[0]", 0x01:"[1]", 0x02:"[2]", 0x03:"[3]", 0x04:"[4]", 0x04:"[5]",
    0x06:"[6]", 0x07:"[7]", 0x08:"[8]", 0x08:"[9]", 0x0A:"[A]", 0x0B:"[B]",
    0x0C:"[C]", 0x0D:"[D]", 0x0E:"[E]", 0x0F:"[F]",
    0x10:"MainGain",   0x11:"SpeedGain",    0x12:"IntGain",
    0x13:"TrqCons",    0x14:"HighSpeed",    0x15:"HighAccel",
    0x16:"Drive_ID",   0x17:"PosOn_Range",  0x18:"GearNumber",
    0x19:"Status",     0x1a:"Config",       0x1b:"AbsPos32",
    0x1c:"??0x1C??",   0x1d:"Speed",        0x1e:"TrqCurrent",
    0x1f:"??0x1F??"
}

# Array of values read back.
# Initialize to 1 billion, which can't be returned by servo in 4 7-bit bytes.
ReplyValues = [1000000000]*32
ReplysDecoded = 0

#===========================================================================================
# Send a command to the servo controller
#===========================================================================================
def SendCommand(Command, Value=0):
    global ShowSerialBytes

    if not -1 <= (Value >> 27) <= 0:
        print ("Value is out of 28 bit range")
        return

    if isinstance(Command, str):
        # For clarity of code, but not efficiency,
        # you can also pass the command as a string.
        Command = SendCommandIds[Command]

    CmdToSend = [0]*2
    CmdToSend[0] = Controller_ID
    CmdToSend[1] = 0x80 | Command & 0x1f

    if Command >= 0x10 and Command <= 0x14:
        if Value < 1 or Value > 127:
            print("Error: Motion gain parameter outside valid range")

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
SingleByteReplies = [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,    0x19, 0x1a]
def DecodeCmd(Command):
    global RecvReplyIds, ShowSerialBytes

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
    if DeviceId == 0x7f and not ShowEchoReplies:
        # If devicd ID has not been set yet (still zero), it will echo everything
        # you send to it.  Once its programmed to nonzero value, it will echo
        # only echo stuff not addressed to it, but not stuff that it handles,
        # including stuff sent to the "everybody" device ID 0x7f.
        #
        # Unfortunately, this makes it ambiguous if you have multiple devices
        # chained together via serial because then you have to address the devices
        # by their own IDs, and you can't easily identify if what comes back is an
        # actual reply or an eco because it didn't match any device ID.
        # Whereas a device addressed with 0x7f as the ID will change the ID in
        # the reply to its own ID.
        return

    ReplyId = Command[1] & 0x1f
    if ShowReplies:
        if DeviceId == 0x7f:
            ReplyString = SendCommandLookup[ReplyId]
            print("Echo:  ",end="")
        else:
            ReplyString = RecvReplyIds[ReplyId]
            print("     Reply: ",end="")

    # Decode the value bytes
    Value = Command[2] & 0x7f
    if Value >= 64: Value -= 128
    for B in Command[3:-1]: Value = Value << 7 | (B & 0x7f)

    if ReplyId in SingleByteReplies:
        # Control parameters are only in range 1-127, so treat as unsigned byte.
        Value = Value & 127

    if ShowReplies: print("%s(%02x) Value=%d"%(ReplyString, ReplyId,Value))

    global ReplyValues, ReplysDecoded

    if DeviceId != 0x7f:
        ReplyValues[ReplyId] = Value
        ReplysDecoded += 1

#===========================================================================================
# Process accumulated serial bytes and decode them.
#===========================================================================================
BytesGot = bytes([])
def RecvData():
    global BytesGot
    start_time = time.time()
    # Wait 20 ms for any reply that is on its way.
    while time.time() - start_time < 0.02:
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
# Request device ID and wait for a reply.
# Used to verify that a controller is connected to the opened serial port.
#===========================================================================================
def GetDeviceId():
    ReplyValues[0x16] = 1000000000 # Invlid return value.
    SendCommand("Read_Drive_ID")
    RecvData()
    if ReplyValues[0x16] == 1000000000: RecvData() # Wait again in case it took longer
    id = ReplyValues[0x16]
    return id


#===========================================================================================
# Scan thru COM9 to COM1 (descending) to find the first port that gets a reply from
# an attached DMM controller
#===========================================================================================
def FindController():
    global ser
    if sys.platform == "win32":
        scan_range = range(9,1,-1)
        prefix = "COM"
    else:
        scan_range = range(0,5)
        prefix = "/dev/ttyS"

    for x in scan_range:
        port = prefix+str(x)
        try:
            OpenSerial(port)
        except:
            # Port doesn't exist
            continue
        print("Trying port:",port)

        id = GetDeviceId()
        if id == 1000000000:
            # No reply from DMM controller on this serial port.
            print("No reply from controller")
            ser.close()
        else:
            ID = id
            # Leave serial port open.
            print("Controller present")
            return port, id
    ser = False
    return False

#===========================================================================================
# Misc commands
#===========================================================================================
# Drive on/off/reset
def DriveEnable(): SendCommand(DMM_GENERAL_READ, 0x20) # re-engage motor drive
def DriveDisable():SendCommand(DMM_GENERAL_READ, 0x21) # Disable drive (freewheel)
def DriveReset():  SendCommand(DMM_GENERAL_READ, 0x1c) # reset motor drive to clear overloading condition

# Request read of pos, torque or speed.
# Return values will be stored in ReplyValues[n] at 0x1b, 0x1d and 0x1e
# after calling RecvData()
def ReqPosRead():     SendCommand(DMM_GENERAL_READ, 0x1b) # Position, at [0x1b]
def ReqTorqCurrent(): SendCommand(DMM_GENERAL_READ, 0x1e) # Torque current, at [0x1d]
def ReqMotorSpeed():  SendCommand(DMM_GENERAL_READ, 0x1d) # Read motor speed, at [0x1e]


# requires "pip3 instll pyserial" for serial to be enabled.
def OpenSerial(port="COM7",ID=0x7f):
    global ser, Controller_ID, ShowSerialBytes, ShowEchoReplies, ShowReplies
    Controller_ID = ID
    ShowSerialBytes = False
    ShowEchoReplies = True
    ShowReplies = True

    ser = serial.Serial(port, 38400)
