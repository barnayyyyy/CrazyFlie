import logging
import sys
import time
import warnings
from threading import Event

import cflib.crtp
import pandas as pd
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper

warnings.simplefilter(action='ignore', category=FutureWarning)

# Set the default URI for the Crazyflie drone
URI = uri_helper.uri_from_env(default='radio://0/100/2M/E7E7E7E7E7')

# Set the default height for the drone and a limit for how far it can move
DEFAULT_HEIGHT = 0.5
BOX_LIMIT = 0.5

# Set up an event to detect whether a flow deck is attached to the drone
deck_attached_event = Event()

# Set up logging configuration for errors
logging.basicConfig(level=logging.ERROR)

# Initialize a global variable to store position estimates
position_estimate = [0, 0, 0, 0, 0, 0]

# create an empty dataframe with the desired column names
df = pd.DataFrame(columns=['x', 'y', 'z', 'roll', 'pitch', 'yaw'])

# Define a parameter callback function to detect whether a flow deck is attached to the drone
def param_deck_flow(name, value_str):
    value = int(value_str)
    print(value)
    if value:
        # If a flow deck is detected, set the deck_attached_event flag to True
        deck_attached_event.set()
        print('Deck is attached!')
    else:
        print('Deck is NOT attached!')

# Define a function to take off
def take_off_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(3)
        mc.stop()

# Drone moves in all 4 coordinates axes
def move_linear_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.back(0.5)
        time.sleep(1)
        mc.left(0.5)
        time.sleep(1)
        mc.right(0.5)
        time.sleep(1)

# flying through hulahoop code
def HulaHoop(scf):
    with MotionCommander(scf, 0.6) as mc:                               # Starting height
        speed = 0.5                                                     # m/s
        sleep = 0.5                                                     # seconds
        turn = 90                                                       # degrees/second
        time.sleep(sleep)
        mc.forward(0.95,speed)
        time.sleep(sleep)
        mc.down(0.275,speed)
        time.sleep(sleep)
        mc.turn_right(85,turn)
        time.sleep(sleep)
        mc.forward(1.5,speed)
        time.sleep(sleep)
        mc.up(0.75,speed)
        time.sleep(sleep)
        mc.forward(0.5,speed)
        time.sleep(sleep)
        mc.land(speed)
        time.sleep(sleep)

# talking to the drone while flying
def log_pos_callback(timestamp, data, logconf):
    global df
    global position_estimate
    position_estimate[0] = data['stateEstimate.x']
    position_estimate[1] = data['stateEstimate.y']
    position_estimate[2] = data['stateEstimate.z']
    position_estimate[3] = data['stateEstimate.roll']
    position_estimate[4] = data['stateEstimate.pitch']
    position_estimate[5] = data['stateEstimate.yaw']

    # create a dictionary with the values
    values_dict = {
        'x': data['stateEstimate.x'],
        'y': data['stateEstimate.y'],
        'z': data['stateEstimate.z'],
        'roll': data['stateEstimate.roll'],
        'pitch': data['stateEstimate.pitch'],
        'yaw': data['stateEstimate.yaw']
    }

    # append the values to the dataframe
    df = df.append(values_dict, ignore_index=True)
    df.to_csv('meas.csv')

# Initialize the Crazyflie drivers
if __name__ == '__main__':
    cflib.crtp.init_drivers()

    # Set up the SyncCrazyflie object to communicate with the drone
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        # Add a callback function to detect whether a flow deck is attached
        scf.cf.param.add_update_callback(group='deck', name='bcFlow2', cb=param_deck_flow)
        time.sleep(1)

        # Configuring logging of the 'x' and 'y' state estimates with a logging period of 10 milliseconds
        logconf = LogConfig(name='Position', period_in_ms=10)

        # Adding the 'stateEstimate.x' and 'stateEstimate.y' variables to the logging configuration
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

        # Waiting for a flow deck to be attached within 5 seconds, otherwise exiting with an error message
        if not deck_attached_event.wait(timeout=5):
            print('No flow deck detected!')
            sys.exit(1)

        # Starting the logging process
        logconf.start()

        ##### FLYING COMMAND #####
        # Calling the functions to fly
        # take_off_simple(scf)
        move_linear_simple(scf)
        # HulaHoop(scf)

        # Stopping the logging process after the take-off is complete
        logconf.stop()
