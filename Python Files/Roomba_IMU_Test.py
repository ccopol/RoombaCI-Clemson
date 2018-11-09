''' Roomba_IMU_Test.py
Purpose: Testing communication between Roomba and LSM9DS1 IMU
	Form basis of Roomba code for other tests.
IMPORTANT: Must be run using Python 3 (python3)
Last Modified: 11/9/2018
'''
## Import libraries ##
import serial
import time
import RPi.GPIO as GPIO

import RoombaCI_lib	

## Variables and Constants ##
global Xbee # Specifies connection to Xbee
Xbee = serial.Serial('/dev/ttyUSB0', 115200) # Baud rate should be 115200
# LED pin numbers
yled = 5
rled = 6
gled = 13

data_counter = 0 # Initialize data_counter

move_dict = {
	1: [2.0, 0, 0],
	2: [10.0, 75, 0],
	3: [2.0, 0, 0],
	4: [5.0, 0, 75],
	5: [2.0, 0, 0],
	6: [10.0, 75, 0]
	}

## Functions and Definitions ##
''' Displays current date and time to the screen
	'''
def DisplayDateTime():
	# Month day, Year, Hour:Minute:Seconds
	date_time = time.strftime("%B %d, %Y, %H:%M:%S", time.gmtime())
	print("Program run: ", date_time)

## -- Code Starts Here -- ##
# Setup Code #
GPIO.setmode(GPIO.BCM) # Use BCM pin numbering for GPIO
DisplayDateTime() # Display current date and time

# LED Pin setup
GPIO.setup(yled, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(rled, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(gled, GPIO.OUT, initial=GPIO.LOW)

# Wake Up Roomba Sequence
GPIO.output(gled, GPIO.HIGH) # Turn on green LED to say we are alive
print(" Starting ROOMBA... ")
Roomba = RoombaCI_lib.Create_2("/dev/ttyS0", 115200)
Roomba.ddPin = 23 # Set Roomba dd pin number
GPIO.setup(Roomba.ddPin, GPIO.OUT, initial=GPIO.LOW)
Roomba.WakeUp(131) # Start up Roomba in Safe Mode
# 131 = Safe Mode; 132 = Full Mode (Be ready to catch it!)
Roomba.BlinkCleanLight() # Blink the Clean light on Roomba

if Roomba.Available() > 0: # If anything is in the Roomba receive buffer
	x = Roomba.DirectRead(Roomba.Available()) # Clear out Roomba boot-up info
	#print(x) # Include for debugging

print(" ROOMBA Setup Complete")
GPIO.output(yled, GPIO.HIGH) # Indicate within setup sequence
# Initialize IMU
print(" Starting IMU...")
imu = RoombaCI_lib.LSM9DS1_IMU() # Initialize IMU
time.sleep(0.5)
# Calibrate IMU
print(" Calibrating IMU...")
#Roomba.Move(0,75) # Start Roomba spinning
#imu.CalibrateMag() # Calculate magnetometer offset values
#Roomba.Move(0,0) # Stop Roomba spinning
#time.sleep(0.5)
imu.CalibrateAccelGyro() # Calculate accelerometer and gyroscope offset values
# Display offset values
#print("mx_offset = {:f}; my_offset = {:f}; mz_offset = {:f}".format(imu.mx_offset, imu.my_offset, imu.mz_offset))
print("ax_offset = {:f}; ay_offset = {:f}; az_offset = {:f}".format(imu.ax_offset, imu.ay_offset, imu.az_offset))
print("gx_offset = {:f}; gy_offset = {:f}; gz_offset = {:f}".format(imu.gx_offset, imu.gy_offset, imu.gz_offset))
print(" IMU Setup Complete")
time.sleep(1) # Gives time to read offset values before continuing
GPIO.output(yled, GPIO.LOW) # Indicate setup sequence is complete

if Xbee.inWaiting() > 0: # If anything is in the Xbee receive buffer
	x = Xbee.read(Xbee.inWaiting()).decode() # Clear out Xbee input buffer
	#print(x) # Include for debugging

# Main Code #

basetime = time.time()
basetime_offset = (1/64)
Roomba.Move(0,0)

Roomba.StartQueryStream(41,42,43,44) # Start query stream with specific sensor packets
datafile = open("IMU_Data_Test1.txt", "w") # Open a text file for storing data
	# Will overwrite anything that was in the text file previously
time_base = time.time()

for i in range(1, len(move_dict.keys())+1):
	[movetime_offset, forward, spin] = move_dict[i] # Read values from dictionary
	Roomba.Move(forward, spin)
	movetime_base = time.time()
	while (time.time() - movetime_base) < movetime_offset:
		if Roomba.Available() > 0: # If data comes in from the Roomba
			# Retrieve data values (Happens every ~1/64 seconds)
			data_time = time.time() - time_base # Time that data is received
			[r_speed,l_speed,l_counts,r_counts] = Roomba.ReadQueryStream(41,42,43,44) # Read Roomba data stream
			[ax,ay,az] = imu.ReadAccel() # Read accelerometer component values
			[gx,gy,gz] = imu.ReadGyro() # Read gyroscope component values
			
			# Write data values to a text file
			datafile.write("{0:.6f}, {1:.6f}, {2:.6f}, {3:.6f}, {4:.6f}, {5:.6f}, {6:.6f}, {7}, {8}, {9}, {10}\n".format(data_time, ax, ay, az, gx, gy, gz, l_speed, r_speed, l_counts, r_counts))
			
		# End if Roomba.Available() > 0
		
	# End while (time.time() - movetime_base) < movetime_offset
	
# End for i in range(1, len(move_dict.keys())+1)

Roomba.Move(0,0) # Stop Roomba movement
Roomba.PauseQueryStream() # Pause Query Stream before ending program
if Roomba.Available() > 0:
	x = Roomba.DirectRead(Roomba.Available()) # Clear out residual Roomba data
	#print(x) # Include for debugging purposes

## -- Ending Code Starts Here -- ##
# Make sure this code runs to end the program cleanly
Roomba.PlaySMB()
datafile.close()
GPIO.output(gled, GPIO.LOW) # Turn off green LED

Roomba.ShutDown() # Shutdown Roomba serial connection
Xbee.close()
GPIO.cleanup() # Reset GPIO pins for next program
