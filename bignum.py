import os

#===========================================================================================
# Show big numbers on the screen (usually top right) to make it easier to see numbers
# on the screen in the backgroudn while filming running tests.
#===========================================================================================
digits = [
"                  @   @@@     @     @@@    @@@     @@   @@@@@   @@@   @@@@@   @@@    @@@          ",
"                  @  @   @   @@    @   @  @   @   @ @   @      @   @      @  @   @  @   @         ",
"                 @   @   @    @    @   @      @   @ @   @      @          @  @   @  @   @         ",
"                 @   @   @    @        @      @  @  @   @@@@   @         @   @   @  @   @         ",
" @@@@@          @    @   @    @       @     @@   @  @       @  @@@@      @    @@@    @@@@         ",
"               @     @   @    @      @        @  @@@@@      @  @   @    @    @   @      @         ",
"               @     @   @    @     @         @     @       @  @   @    @    @   @      @         ",
"         @@   @      @   @    @    @      @   @     @   @   @  @   @    @    @   @  @   @         ",
"         @@   @       @@@     @    @@@@@   @@@      @    @@@    @@@     @     @@@    @@@          ",
"                                                                                                  "]
def ShowBigNum(str):
    global x,y,num_size
    print("\033[s", end="") # Save cursor position

    prevlines = y-1
    if prevlines > 2: prevlines = 2
    flip = False;
    if num_size < 0: flip = True; num_size = -num_size;

    while prevlines > 0:
        # If not at the top, clear a line or two above the number to clear scrolled stuff
        print("\033[%d;%dH "%(y-prevlines,x)+"       "*len(str)*num_size) # position cursor.
        prevlines -= 1

    for line in range (10*num_size):
        if flip:
            digit_line = int(9-line/num_size);
        else:
            digit_line = int(line/num_size);

        linestr = ""
        for cp in range(len(str)):
            if (str[cp] == " "):
                index = 13
            else:
                index = ord(str[cp])-45
                if index < 0 or index >= 14: index = 0
            index = index * 7
            linestr = linestr + digits[digit_line][index:index+7]
        if num_size > 1: linestr = linestr.replace('@', '@'*num_size).replace(' ', ' '*num_size)
        if flip: linestr = linestr[::-1]
        linestr = "\033[%d;%dH"%(y+line,x)+linestr # position cursor.
        print(linestr)
        #print (linestr.replace("@",u"\u2588")) # Print, but use solid block characters instead

    print("\033[u", end="") # restore cursor position

#print("\033[0;97m") # Switch to bright white color


# set where in top right the number should appear, and how may digits to make room for.
def SetPos(right=4,yp=2,size=2):
    global x,y,num_size
    num_size = size
    x = os.get_terminal_size().columns - right*7*size
    y = yp

def MoveCursor(x,y):
    print("\033[%d;%dH"%(y,x),end="")

def ClearScreen():
    print("\033[2J",end="")

# Set default position
SetPos() 