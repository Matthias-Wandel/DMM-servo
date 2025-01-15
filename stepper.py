#!/usr/bin/env python
# Python script for testing with stepper motors against dmm servos.
# Handles stepper driving for comparing stepper motor accuracy vs DMM servos
#
# Also duplicates the job and lift routines for comparative testing.
# Jan 2025

import RPi.GPIO as GPIO
import time, sys, signal

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

line_clock = 0
line_dir = 0
line_enable = 0

STEPS_PER_TURN = 1600

#===========================================================================================
# Set up I/O lines for controlling stepper
#===========================================================================================
def init_motor():
    print("Initializing stepper motor I/O")
    global line_clock, line_dir, line_enable
    # New harness for motor, closest to USB connectors, inside row
    # so that hardware PWM could be used for the clock line.
    line_clock  = 13
    line_dir    = 19
    line_enable = 26

    # Enable line is different for CL stepper and controller
    # High is off for the stepper controller.
    GPIO.setup(line_enable, GPIO.OUT, initial=True)
    GPIO.setup(line_dir,    GPIO.OUT, initial=False)
    GPIO.setup(line_clock,  GPIO.OUT, initial=False)


#===========================================================================================
# Turn on stepper motor enable
#===========================================================================================
def motor_on():
    GPIO.output(line_enable, 0) # enable

#===========================================================================================
# on ending, turn off motor
#===========================================================================================
def motor_off():
    print("Turning off motor")
    GPIO.output(line_enable, 1) # disable
    if hw_pwm:
        print("stop HW pwm also")
        hw_pwm.stop()

def shutdown_func(a,b):
    motor_off()
    sys.exit()


signal.signal(signal.SIGINT, shutdown_func)


#===========================================================================================
# Do steps without ramp
#===========================================================================================
def DoSteps(steps, delay = 3):
    global line_clock, line_dir, line_enable
    duse = delay/2000
    motor_on()

    if steps < 0:
        steps = -steps
        GPIO.output(line_dir, 0)
    else:
        GPIO.output(line_dir, 1)

    for x in range (0,steps):
        GPIO.output(line_clock, True)
        time.sleep(duse)
        GPIO.output(line_clock, False)
        time.sleep(duse)

#===========================================================================================
# Do steps with hardware PWM.
#
#   Install required:
#      sudo pip3 install rpi-hardware-pwm
#      sudo apt-get install pigpiod
#   Must start pigpio deamon:
#      sudo /bin/pigpiod
#===========================================================================================
hw_pwm = False
def DoHwPwm(frequency):
    # If motor's clock is on GPIO13, we can use the hardware PWM
    # Does require running "suiod pigpiod" to start the hardware gpio daemon.
    global hw_pwm
    if not hw_pwm:
        print("Start pigpio")
        import pigpio
        motor_on()
        hw_pwm = pigpio.pi()
        motor_on()

    GPIO_PIN = 13
    DUTY_CYCLE = 50  # 50%
    duty_cycle_value = int(DUTY_CYCLE / 100 * 1_000_000)

    if frequency >= 100:
        print("Do ",frequency,"hz")
        hw_pwm.hardware_PWM(GPIO_PIN, frequency, duty_cycle_value)
    else:
        print("Stop hw PWM")
        hw_pwm.hardware_PWM(GPIO_PIN, 0, 0)
        hw_pwm.stop()
        hw_pwm = False
        motor_off()

#===========================================================================================
# Do steps with ramp up and down
#===========================================================================================
def DoStepsRamp(steps, delay=-1):
    global line_clock, line_dir, line_enable
    #print("StepsRamp:",steps)

    if delay < 0:
        delay = 0.65 # miliseconds -- fastest for old stepper
        #delay = 0.3 # miliseconds.

    duse = delay/1000;
    GPIO.output(line_enable, 0) # enable

    if steps < 0:
        steps = -steps
        GPIO.output(line_dir, 0)
    else:
        GPIO.output(line_dir, 1)

    time.sleep(0.01)

    for x in range (0, steps):
        GPIO.output(line_clock,1)
        duse = delay/2000;
        fromend = min(x*.8, steps-x)
        if fromend < 30: duse = duse * 1.4
        if fromend < 15: duse = duse * 1.8
        GPIO.output(line_clock,0)
        time.sleep(duse)

init_motor()

#===========================================================================================
# If not running as library, some code for doing stuff with the motor
#===========================================================================================
if __name__ == '__main__':

    #===========================================================================================
    # Manually position the motor.
    #===========================================================================================
    def Jog():
        import tty, termios
        #import keyboard # Keyboard module, requires "pip3 install keyboard"

        def get_key():
            #Capture a single keypress in unbuffered mode.
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)

            key = sys.stdin.read(1)  # Read the first byte

            if key == '\x1b':  # If it's an escape character, read more bytes
                key += sys.stdin.read(2)  # multi key escaped characters

            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return key

        # Initialize the position
        global position, laststeps
        position = 0
        laststeps = 0

        def update_position(amount):
            global position, laststeps, STEPS_PER_TURN
            position += amount
            print("Go to deg: %6.2f"%(position))
            newsteps = int(position*STEPS_PER_TURN/360)
            DoStepsRamp(newsteps-laststeps, 1.5)
            laststeps = newsteps


        while True:
            key = get_key()
            print("got:",key.encode('utf-8'))

            if key == '\x1b[5':  # Page Up
                print("page up")
                update_position(30)
            elif key == '\x1b[6':  # Page Down
                print ("page down")
                update_position(-30)

            elif key == '\x1b[A':  # Cursor Up
                print("up")
                update_position(6)
            elif key == '\x1b[B':  # Cursor Down
                print("down")
                update_position(-6)
            elif key == '\x1b[C':  # Cursor Right
                print("right")
                update_position(0.1)
            elif key == '\x1b[D':  # Cursor Left
                print("left")
                update_position(-0.1)

            elif key == 'd':  # whole degree
                update_position(1)
            elif key == 'e':  # whole degree
                update_position(-1)
            elif key == 'q':  # Quit
                print("Exit")
                break
        motor_off()

    #===========================================================================================
    # Behave like the seconds hand of a clock
    #===========================================================================================
    def Clock():
        print("Clock seconds hand test")

        global STEPS_PER_TURN
        motor_on()
        time.sleep(0.5)

        xtra_turns = -1
        second_jumps = True

        laststeps = 0
        for a in range (0,1200):
            newsteps = (a/60.0+a*xtra_turns)*STEPS_PER_TURN
            if second_jumps:
                #DoSteps(-int(newsteps-laststeps),0)
                DoStepsRamp(int(newsteps-laststeps),0.18)
                time.sleep(0.99)
            else:
                DoSteps(int(newsteps-laststeps),10)
                print(newsteps)

            laststeps = newsteps

        dmm.DriveDisable()

    #===========================================================================================
    # Test how fast we can run a fan blade before motor gets overloaded
    #===========================================================================================
    def FanSpeed():
        print("Fan max speed test")
        DoSteps(-1)
        time.sleep(1)
        
        import bignum

        set_speed = 0
        increment_count = 10
        motor_on()
        while True:
            set_speed += 10
            print("Set speed to",set_speed, "RPM")
            freq = int(set_speed * STEPS_PER_TURN / 60)
            DoHwPwm(freq)
            bignum.ShowBigNum("%4d"%(set_speed))
            time.sleep(0.15)
            if set_speed > 1340: time.sleep(0.7)
            if set_speed > 1500: break

        motor_off()



    #===========================================================================================
    # Attempt to lift weight with pulley
    #===========================================================================================
    def WeightLift():
        print("Weight lifting torque test, by turn const speed")
        global STEPS_PER_TURN
        motor_on()
        #time.sleep(1.2)
        lift_turns = 2

        DoStepsRamp(STEPS_PER_TURN*lift_turns, 2)
        time.sleep(1)
        DoStepsRamp(-STEPS_PER_TURN*lift_turns, 1)
        motor_off()

    def WeightHold():
        motor_on()
        time.sleep(15)
        motor_off()

    DoStepsRamp(0) # turns on and leaves on enable line.

    if len(sys.argv) > 1:
        argument = sys.argv[1]
        if argument == "jog": Jog()
        elif argument == "clock": Clock()
        elif argument == "fan": FanSpeed()
        elif argument == "lift": WeightLift()
        elif argument == "hold": WeightHold()
        else:
            print("Argument %s not understood"%(argument))

        sys.exit()
    else:
        print("No command specified")

