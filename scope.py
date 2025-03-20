# Scope screen for ServoTune program.
import time
import dmmlib as dmm

# Data storage
time_window = 2  # seconds
samples_per_second = 155  # Samples per second target rate.
# Due to python slowness, its always less than target.
# But a greater limit to how fast we can sample is the DMM servo controller,
# which has a tendency to drop queries if they are sent quickly.
# the serial communications speed should be able to handle 500 position queries
# per second, but sending queries at a rate above about 50 per second causes some
# queries to get dropped.  Very frustrating.
#
# Also, if scope has been running for a while, it starts to get slow.  this
# probably due to the python heap getting more complex over time, slowing
# down python execution.  If you use the scope mode a lot, its a good idea
# to restart ths program frequently.  Python may not have been the best choice
# for implementing something like the scope mode.

value_data = []
time_data = []
requested_times = []
x_origin = 0

aquiring_active = False
print("scope init")

random_avg = 0
def dummy_data():
    # Make dummy data for testing scope
    global random_avg
    import random
    r = random.uniform(-0.1, 0.1)
    random_avg = random_avg*0.95 + r
    return random_avg + r

ReqCount = 0
def update_data(start=False):
    # Called periodically to add data to the graph.
    global aquiring_active, requested_times
    if not aquiring_active:
        unwrapped_plot()
        return

    root.after(int(1000 / samples_per_second), update_data)  # Schedule next update
    dmm.RecvData(0)  # Read serial to get previous position

    numgot = len(dmm.DecodedQueue)
    numnewpos = 0
    if numgot:
        for n in range (0, numgot):
            rx_item = dmm.DecodedQueue[n]
            if rx_item[1] == 0x1b:
                value_data.append(rx_item[2])
                t = requested_times[n]
                if t == 0: print("Zero time!!!") # somehow got out of sync or something!
                time_data.append(t)
                numnewpos += 1
            elif rx_item[1] == 0x10:
                # Main gain reply for syncronization.  Find corresponding dummy timestamp.
                #print("       got mg")
                for k in range (n, len(requested_times)):
                    if requested_times[k] == 0:
                        if k != n:
                            print("DMM ignored Pos requests: ",k-n)
                            requested_times = requested_times[k-n:] # Discard excess timestamps
                        break;


        dmm.DecodedQueue = []

        requested_times = requested_times[numgot:] # don't clear -- may have more replies pending
        if numnewpos: update_plot(numnewpos)

    dmm.ReqPosRead() # Request next position read
    now = time.time() # Remember when request was sent (this has less jitter than received tiem)
    requested_times.append(now)

    global ReqCount
    ReqCount += 1
    if ReqCount & 7 == 0:
        # Send occasional unrelated command to detect when position requests were ignored
        # in order to get back in sync with the timestamps I saved when sending the request
        dmm.SendCommand(0x18)
        requested_times.append(0)
        #print("req mg")


def unwrapped_plot():
    # Updates the graph so that latest point is on the right side of the graph.
    canvas.delete("graph")

    height = canvas.winfo_height()
    x_scale = canvas.winfo_width() / time_window
    y_scale = height / 0x10000
    x_origin = time_data[-1]-time_window

    xo = -1
    for i in range (1, len(value_data)):
        x = x_scale * (time_data[i]-x_origin)
        y =  height/2-(value_data[i]-graph_center_val)*y_scale
        if xo >= 0:
            canvas.create_line(xo,yo,x,y,fill="white", tags="graph", width=2)
        xo = x; yo = y


last_wrap_len = 0
graph_center_val = -1
def update_plot(numgot):
    global x_origin, time_data, value_data, last_wrap_len, graph_center_val
    height = canvas.winfo_height()
    x_scale = canvas.winfo_width() / time_window
    y_scale = height / 0x10000

    if len(value_data) < numgot+2: return

    if graph_center_val == -1: graph_center_val = value_data[0]

    if time_data[-1] > x_origin+time_window:
        x_origin += time_window
        if last_wrap_len:
            # Trim aquired data to just what is visible.
            print("Trim ",last_wrap_len,"points from data", len(time_data), len(value_data), len(requested_times))
            time_data = time_data[last_wrap_len:]
            value_data = value_data[last_wrap_len:]
        last_wrap_len = len(value_data)

        #print("pts to check", len(value_data))
        min_p = 1000000000; max_p = -1000000000
        for p in value_data:
            min_p = min(min_p,p)
            max_p = max(max_p,p)

        graph_center_val = int((min_p+max_p)/2)

    xo = -1
    for n in range(-2-numgot, -1):
        # Calculate where to put new line segment
        x  = x_scale * (time_data[n]-x_origin)

        #offset = value_data[-1] & 0xffff0000
        y =  height/2-(value_data[n]-graph_center_val)*y_scale

        if xo >= 0:
            canvas.create_line(xo,yo,x,y,fill="white", tags="graph", width=2)
        else:
            # Erase slightly ahead of write point so there is a gap
            xe = x_scale * (time_data[-1]-x_origin)
            canvas.create_rectangle(x+2, 0, xe+10, height, fill="gray", outline="")

        xo = x; yo = y


def start_aquring():
    global value_data, time_data, aquiring_active, x_origin, requested_times
    dmm.ShowReplies = False
    dmm.RecvData()
    dmm.DecodedQueue = []
    dmm.SaveDecoded = True

    value_data = []
    time_data = []
    requested_times = []
    x_origin = time.time()

    canvas.delete("graph")
    aquiring_active = True
    update_data(True)
    
    print("scope start")

def stop():
    global aquiring_active
    aquiring_active = False
    dmm.SaveDecoded = False
    print("scope stop")
