# Final Project: Moving Drone with Keyboard Control
# John Barney and Lucas Nichols
# Date: 4/25/2023
# ENEE 4350.23243 - Spring 2023

## ~~~~~~~~~~~~~~~ Pre-Requisites ~~~~~~~~~~~~~~~ ##
# Step-by-Step: Motion Commander:
# https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_motion_commander/

# Install the following libraries:
# pip install cflib
# pip install keyboard
# pip install pandas

## ~~~~~~~~~~~~~~~ Program ~~~~~~~~~~~~~~~ ##
import logging                                                  # import the logging module for debugging information
import sys                                                      # import the sys module to access interpreter variables
import time                                                     # import the time module for time-related functions
import pandas as pd                                             # import the pandas library for data manipulation and analysis
import warnings                                                 # import warnings to suppress future warnings
from threading import Event                                     # import the Event class from the threading module
import cflib.crtp                                               # import the cflib.crtp module for radio communication with the Crazyflie
from cflib.crazyflie import Crazyflie                           # import the Crazyflie class from the cflib.crazyflie module
from cflib.crazyflie.log import LogConfig                       # import the LogConfig class from the cflib.crazyflie.log module
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie         # import the SyncCrazyflie class from the cflib.crazyflie.syncCrazyflie module
from cflib.positioning.motion_commander import MotionCommander  # import the MotionCommander class from the cflib.positioning.motion_commander module
from cflib.utils import uri_helper                              # import the uri_helper function from the cflib.utils module
import keyboard                                                 # import the keyboard module for keyboard input handling
warnings.simplefilter(action='ignore', category=FutureWarning)

########## Setup #########
# Set the default URI for the Crazyflie drone
URI = uri_helper.uri_from_env(default='radio://0/100/2M/E7E7E7E7E7')

# Set up an event to detect whether a flow deck is attached to the drone
deck_attached_event = Event()

# Set up logging configuration for errors
logging.basicConfig(level=logging.ERROR)

# Create an empty dataframe with the desired column names
df = pd.DataFrame(columns=['x', 'y', 'z', 'roll', 'pitch', 'yaw'])

# Starting position of the drone
position_estimate = [0, 0, 0, 0, 0, 0]


########## Connection #########
# Callback function to check if the flowdeck is attached to the drone
def param_deck_flow(_, value_str):
    value = int(value_str)
    print(value)
    if value:
        deck_attached_event.set()
        print('Deck is attached!')
    else:
        print('Deck is NOT attached!')


########## Position #########
# Callback function to log the drone's position
def log_pos_callback(timestamp, data, logconf):
    global df
    global position_estimate
    position_estimate[0] = data['stateEstimate.x']
    position_estimate[1] = data['stateEstimate.y']
    position_estimate[2] = data['stateEstimate.z']
    position_estimate[3] = data['stateEstimate.roll']
    position_estimate[4] = data['stateEstimate.pitch']
    position_estimate[5] = data['stateEstimate.yaw']

    # Create a dictionary with the values
    values_dict = {
        'x': data['stateEstimate.x'],
        'y': data['stateEstimate.y'],
        'z': data['stateEstimate.z'],
        'roll': data['stateEstimate.roll'],
        'pitch': data['stateEstimate.pitch'],
        'yaw': data['stateEstimate.yaw']
    }

    # Append the values to the dataframe
    df = df.append(values_dict, ignore_index=True)
    df.to_csv('meas.csv')


########## Navigation #########
# Control the drone based on keyboard inputs
def move():
    with MotionCommander(scf) as mc:        # use a MotionCommander object to control the Crazyflie's motion
        print("Press W,A,S,D for horizontal\nShift,Space for vertical\nQ,E for turning\nESC to quit")
        speed = 0.1                         # set the initial speed to 0.1 m/s
        print('Speed set to ', speed)       # print the current speed to the console
        while (1):                          # continue looping until user presses the "esc" key
            if keyboard.is_pressed("w"):    # if the "w" key is pressed, move forward at the current speed
                mc.forward(speed)
            if keyboard.is_pressed("s"):    # if the "s" key is pressed, move backward at the current speed
                mc.back(speed)
            if keyboard.is_pressed("a"):    # if the "a" key is pressed, move left at the current speed
                mc.left(speed)
            if keyboard.is_pressed("d"):    # if the "d" key is pressed, move right at the current speed
                mc.right(speed)
            if keyboard.is_pressed("space"):# if the "space" key is pressed, move up at the current speed
                mc.up(speed)
            if keyboard.is_pressed("shift"):# if the "shift" key is pressed, move down at the current speed
                mc.down(speed)
            if keyboard.is_pressed("q"):    # if the "q" key is pressed, turn left at the current speed
                mc.turn_left(speed)
            if keyboard.is_pressed("e"):    # if the "e" key is pressed, turn right at the current speed
                mc.turn_right(speed)
            if keyboard.is_pressed("esc"):  # if the "esc" key is pressed, stop moving and land the drone
                mc.start_linear_motion(0, 0, 0)
                mc.land(0.5)
                break                       # exit the loop


########## Main Loop #########
if __name__ == '__main__':
    # Initalize the low-level drivers and a new instance of CrazyFlie
    cflib.crtp.init_drivers()
    cf=Crazyflie(rw_cache='./cache')
    try:
        # Set up the SyncCrazyflie object to communicate with the drone
        with SyncCrazyflie(URI, cf) as scf:
            
            # Add a callback function to detect whether a flow deck is attached
            scf.cf.param.add_update_callback(group='deck', name='bcFlow2',cb=param_deck_flow)
            time.sleep(1)
            
            # Configuring logging of the 'x' and 'y' state estimates with a logging period of 10 milliseconds
            logconf = LogConfig(name='Position', period_in_ms=10)

            # Adding the logging variables to the logging configuration
            logconf.add_variable('stateEstimate.x', 'float')
            logconf.add_variable('stateEstimate.y', 'float')
            logconf.add_variable('stateEstimate.z', 'float')
            logconf.add_variable('stateEstimate.roll', 'float')
            logconf.add_variable('stateEstimate.pitch', 'float')
            logconf.add_variable('stateEstimate.yaw', 'float')
            
            # Adding the logging configuration to the logging system of the Crazyflie object
            scf.cf.log.add_config(logconf)

            # Adding a callback function to be executed whenever new log data is received
            logconf.data_received_cb.add_callback(log_pos_callback)

            # Exit condition if drone is not connected properly
            if not deck_attached_event.wait(timeout=5):
                print('No flow deck detected!')
                sys.exit(1)

            # Starting the logging process
            logconf.start()

            # Calling the function to fly
            move()

    except KeyboardInterrupt:
        # Stop logging and disconnect from the Crazyflie
        logconf.stop()
        cf.close_link()
        raise KeyboardInterrupt('User stopped program')
