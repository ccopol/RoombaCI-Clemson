''' Roomba_DHTurn_Test.py
Purpose: Synchronize heading of Roomba network using PCO model
	Based off Arduino code from previous semester
IMPORTANT: Must be run using Python 3 (python3)
Last Modified: 5/31/2018
'''
## Import libraries ##
import serial
import time
import RPi.GPIO as GPIO

import Roomba_lib # Make sure this file is in the same directory
import IMU_lib # Make sure this file is in the same directory

## Variables and Constants ##
global Xbee # Specifies connection to Xbee
Xbee = serial.Serial('/dev/ttyUSB0', 115200) # Baud rate should be 57600
# LED pin numbers
yled = 5
rled = 6
gled = 13

# Timing Counter Parameters
data_timer = 0.2
reset_timer = 10

# DH_Turn Parameters
global angle # Heading of Roomba (found from magnetometer)
epsilon = 1.0 # (Ideally) smallest resolution of magnetometer
data_counter = 0 # Data number counter
global desired_heading  # Heading set point for Roomba

## Functions and Definitions ##
''' Prints global variables to monitor
	Increments data_counter
	Will need to include magnetometer data '''
def PrintData(*argv):
	global data_counter
	# Print data to console in MATLAB format
	print(data_counter, *argv, sep=', ', end=';\n')
	data_counter += 1 # Increment data counter

''' Returns Roomba spin amount to achieve desired heading set point
	'''
def DHTurn():
	global angle
	global desired_heading
	global epsilon
		
	thresh_1 = 25 # First threshold value (degrees)
	thresh_2 = 5  # Second threshold value (degrees)
	
	diff = abs(angle - desired_heading)
	# Determine spin speed based on thresholds
	if (diff > thresh_1 and diff < (360 - thresh_1)):
		spin_value = 100 # Move faster when farther away from the set point
	elif (diff > thresh_2 and diff < (360 - thresh_2)):
		spin_value = 50 # Move slower when closer to the set point
	else:
		spin_value = 15 # Move very slow when very close to the set point
		# Reduces oscillations due to magnetometer variation and loop execution rate
	
	# Determine direction of spin
	if desired_heading < epsilon: # if 0 <= desired_heading < epsilon 
		if (angle > (desired_heading + epsilon) and angle < (desired_heading + 180)):
			return -spin_value # Spin Left (CCW)
		elif (angle < (360 + desired_heading - epsilon)): # and angle >= (desired_heading + 180) 
			return spin_value # Spin Right (CW)
		else: # if (360 + desired_heading - epsilon) < angle < (desired_heading + epsilon)
			return 0 # Stop Spinning
	elif desired_heading < 180: # and desired_heading >= epsilon...
		if (angle > (desired_heading + epsilon) and angle < (desired_heading + 180)):
			return -spin_value # Spin Left (CCW)
		elif (angle < (desired_heading - epsilon) or angle >= (desired_heading + 180)):
			return spin_value # Spin Right (CW)
		else: # if (desired_heading - epsilon) < angle < (desired_heading + epsilon)
			return 0 # Stop Spinning
	elif desired_heading < (360 - epsilon):
		if (angle < (desired_heading - epsilon) and angle > (desired_heading - 180)):
			return spin_value # Spin Right (CW)
		elif (angle > (desired_heading + epsilon) or angle <= (desired_heading - 180)):
			return -spin_value # Spin Left (CCW)
		else: # if (desired_heading - epsilon) < angle < (desired_heading + epsilon) 
			return 0 # Stop Spinning
	else: # if desired_heading >= (360 - epsilon)
		if (angle < (desired_heading - epsilon) and angle > (desired_heading - 180)):
			return spin_value # Spin Right (CW)
		elif (angle > (desired_heading + epsilon - 360)): # and (angle <= (desired_heading - 180))
			return -spin_value # Spin Left (CCW)
		else: # if (angle > (desired_heading - epsilon) or angle < (desired_heading + epsilon - 360))
			return 0 # Stop Spinning

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
Roomba = Roomba_lib.Create_2("/dev/ttyS0", 115200)
Roomba.ddPin = 23
GPIO.setup(Roomba.ddPin, GPIO.OUT, initial=GPIO.LOW)
Roomba.WakeUp(131) # Start up Roomba in Safe Mode
# 131 = Safe Mode; 132 = Full Mode (Be ready to catch it!)
Roomba.BlinkCleanLight() # Blink the Clean light on Roomba

if Roomba.Available() > 0: # If anything is in the Roomba receive buffer
	x = Roomba.DirectRead(Roomba.Available()) # Clear out Roomba boot-up info
	print(x) # Include for debugging

print(" ROOMBA Setup Complete")
GPIO.output(yled, GPIO.HIGH) # Indicate within setup sequence
# Initialize IMU
print(" Starting IMU...")
imu = IMU_lib.LSM9DS1_IMU() # Initialize IMU
time.sleep(0.5)
# Calibrate IMU
print(" Calibrating IMU...")
Roomba.Move(0,75) # Start Roomba spinning
imu.CalibrateMag() # Calculate magnetometer offset values
Roomba.Move(0,0) # Stop Roomba spinning
time.sleep(0.5)
imu.CalibrateAccelGyro() # Calculate accelerometer and gyroscope offset values
# Display offset values
print("mx_offset = %f; my_offset = %f; mz_offset = %f"%(imu.mx_offset, imu.my_offset, imu.mz_offset))
print("ax_offset = %f; ay_offset = %f; az_offset = %f"%(imu.ax_offset, imu.ay_offset, imu.az_offset))
print("gx_offset = %f; gy_offset = %f; gz_offset = %f"%(imu.gx_offset, imu.gy_offset, imu.gz_offset))
print(" IMU Setup Complete")
time.sleep(1) # Gives time to read offset values before continuing
GPIO.output(yled, GPIO.LOW) # Indicate setup sequence is complete

if Xbee.inWaiting() > 0: # If anything is in the Xbee receive buffer
	x = Xbee.read(Xbee.inWaiting()).decode() # Clear out Xbee input buffer
	#print(x) # Include for debugging

GPIO.output(yled, GPIO.LOW) # Indicate setup sequence complete

# Main Code #
angle = imu.CalculateHeading() # Get initial heading information
forward = 0
desired_heading = 0
data_base = time.time()
reset_base = time.time()

while True:		
	try:
		# Update heading of Roomba
		angle = imu.CalculateHeading()
		
		spin = DHTurn() # Value needed to turn to desired heading point
		Roomba.Move(forward, spin) # Move Roomba to desired heading point
		
		if spin == 0:
			GPIO.output(yled, GPIO.LOW) # Indicate Roomba is not turning
		else:
			GPIO.output(yled, GPIO.HIGH) # Indicate Roomba is turning
		
		if (time.time() - reset_base) > reset_timer:
			desired_heading += 90
			if desired_heading >= 360:
				desired_heading -= 360
			reset_base += reset_timer
		
		# Print heading data to monitor every second
		if (time.time() - data_base) > data_timer: # After one second
			[mx,my,mz] = imu.ReadMag() # Read magnetometer component values
			angle = imu.CalculateHeading() # Calculate heading
			# Note: angle may not correspond to mx, my, mz
			#[ax,ay,az] = imu.ReadAccel() # Read accelerometer component values
			#[gx,gy,gz] = imu.ReadGyro() # Read gyroscope component values
			
			print("%f, %f, %f, %f, %f;"%(angle,desired_heading,mx,my,mz))
			#PrintData(angle, desired_heading, mx, my, mz)
			data_base += data_timer
				
	except KeyboardInterrupt:
		print('') # print new line
		break # exit while loop

## -- Ending Code Starts Here -- ##
# Make sure this code runs to end the program cleanly
Roomba.Move(0,0) # Stop Roomba movement
Roomba.PlaySMB()
GPIO.output(gled, GPIO.LOW) # Turn off green LED
GPIO.output(yled, GPIO.LOW) # Turn off yellow LED

Roomba.ShutDown() # Shutdown Roomba serial connection
Xbee.close()
GPIO.cleanup() # Reset GPIO pins for next program
