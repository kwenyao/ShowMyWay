from wifi_trilateration.wifi import Wifi
from UserInteraction import Voice
from arduino_communication import SerialCommunicator
import constants
import math
import messages
import time

class Guide():
	def __init__(self):		
		### OBJECTS ###
		self.wifi = Wifi()
		self.voiceOutput = Voice()
		self.serial = SerialCommunicator()
		
		### CLASS ATTRIBUTES ###
		self.prevBearing = 0
		self.prevStairSensor = 0
		self.stairSensor = 0
		self.headSensor = 0
		self.bearingFaced = 0
		self.stepDetected = 0
		self.lastUpdatedTime = 0
		self.lastInstructionTime = 0
		
		### FLAGS ###
		self.isStairsDetected = False
		self.isUpStairs = False
		self.isDownStairs = False
		self.onPlatform = False

		### COUNTERS ###
		self.stepsOnPlatform = 0
		
	##########################################
	# Functions called by Navigation
	##########################################
	def updateCoordinates(self, currCoor, north, apNodes, bearingToFace):
		self.receiveDataFromArduino()
		imuCoor = self.updateIMUCoor(currCoor, north, bearingToFace)
		print "                                    current coor is ",
		print imuCoor
		# wifiCoor = self.wifi.getUserCoordinates(apNodes)
		# newCoor = self.estimateCurrentPosition(imuCoor, wifiCoor, north)
		# return newCoor
		return imuCoor
		
	def warnUser(self):
		self.warnHeadObstacle()
		self.warnStairs()
		self.guideAlongStairs()
		
	def userReachedNode(self, node):
		message = messages.NODE_REACHED_TEMPLATE.format(node = node['name'])
		print message
		self.voiceOutput.say(message)
	
	def checkBearing(self, bearingToFace, currCoor, nextCoor):
		bearingOffset = int(abs(bearingToFace - self.bearingFaced))
		if bearingOffset > constants.ORIENTATION_DEGREE_ERROR:
			if bearingToFace < self.bearingFaced:
				if bearingOffset > 180 : 
					message = messages.TURN_TEMPLATE.format(direction = "right", angle = (360 - bearingOffset))
				else :
					message = messages.TURN_TEMPLATE.format(direction = "left", angle = bearingOffset)
			else:
				if bearingOffset > 180 : 
					message = messages.TURN_TEMPLATE.format(direction = "left", angle = 360 - bearingOffset)
				else :
					message = messages.TURN_TEMPLATE.format(direction = "right", angle = bearingOffset)
			print message
			self.voiceOutput.say(message)
			
		else: #guide user to walk straight
			if (time.time() - self.lastInstructionTime) >= constants.INSTRUCTIONS_FREQUENCY:
				distToNextNode = math.sqrt((nextCoor[0] - currCoor[0]) ** 2 +
										   (nextCoor[1] - currCoor[1]) ** 2)
				stepsToNextNode = int((distToNextNode/100) / (constants.STEP_LENGTH)) #changed dist from cm to meters 
				message = messages.WALK_FORWARD_TEMPLATE.format(steps = stepsToNextNode)
				print message
				self.voiceOutput.say(message)
				self.lastInstructionTime = time.time()
		self.prevBearing = self.bearingFaced # Why?!?!
	
	def destinationReached(self):
		message = messages.DESTINATION_REACHED
		print message
		self.voiceOutput.say(message)
		
	##########################################
	# Helper Functions
	##########################################
	
	def receiveDataFromArduino(self):
		dataReceived = self.serial.serialRead()
		dataSplited = dataReceived.split(' ')
		dataFiltered = []
		for i in range(len(dataSplited)):
			if dataSplited[i] != "":
				dataFiltered.append(dataSplited[i])
		self.headSensor = float(dataFiltered[0])
		self.stairSensor = float(dataFiltered[1])
		self.bearingFaced = float(dataFiltered[2])
		self.stepDetected = float(dataFiltered[3])
	
	def updateIMUCoor(self, currCoor, north, bearingToFace):
		if (self.stepDetected == 1 and 
			abs(self.bearingFaced - self.prevBearing) < constants.WALKING_DEGREE_ERROR/2 and 
			self.isStairsDetected == False):
			print "current bearing to faced is " + str(bearingToFace),
			print "current north is " + str(north)
			print "x increment is " + str(int(constants.STEP_LENGTH * 100 * math.sin((bearingToFace - north) /180.0 * math.pi)))
			imu_new_x = int ((currCoor[0] + constants.STEP_LENGTH * 100 *
						 math.sin((bearingToFace - north) /180.0 * math.pi)))
			imu_new_y = int ((currCoor[1] + constants.STEP_LENGTH * 100 *
						 math.cos((bearingToFace - north) / 180.0 * math.pi)))
			return [imu_new_x, imu_new_y]
		else:
			if (self.stepDetected == 1 and abs(self.bearingFaced - self.prevBearing) >= constants.WALKING_DEGREE_ERROR/2):
				print "steps detected but not taken due to turn being made"
			if (self.stepDetected == 1 and self.isStairsDetected == True):
				print "steps detected but not taken due to stairs detected."
			return currCoor
		
	def estimateCurrentPosition(self, imuCoor, wifiCoor, north):
		currCoor = []
		timeElapsed = time.time() - self.lastUpdatedTime
		approx_x_travelled = (timeElapsed * constants.USER_SPEED * 
							  math.sin((self.bearingFaced - north) / 180.0 * math.pi))
		approx_y_travelled = (timeElapsed * constants.USER_SPEED * 
							  math.cos((self.bearingFaced - north) / 180.0 * math.pi))
	
		if (approx_x_travelled+currCoor[0] <= wifiCoor[0] ):
			if (approx_y_travelled+currCoor[1] <= wifiCoor[1]):
				currCoor[0] = (imuCoor[0] + wifiCoor[0])/2
				currCoor[1] = (imuCoor[1] + wifiCoor[1])/2
		else:
			currCoor = imuCoor
		self.lastUpdatedTime = time.time()
		return currCoor
		
	def warnHeadObstacle(self):
		if self.headSensor != 0:
			message = messages.HEAD_OBSTACLE_TEMPLATE.format(distance = self.headSensor)
			print message
			self.voiceOutput.say(message)
	
	def warnStairs(self):
		
		if self.stairSensor - self.prevStairSensor > constants.STAIR_LIMIT:
			if self.isUpStairs:
				self.isStairsDetected ^= True
				self.isUpStairs ^= True
				self.onPlatform = True #set to check if user is on platform
			else:
				self.isStairsDetected ^= True
				self.isDownStairs ^= True
			self.voiceOutput.say(messages.DOWN_STAIRS)
		elif self.stairSensor - self.prevStairSensor < -constants.STAIR_LIMIT:
			print self.stairSensor, 
			print " lalalalalalalal ",
			print self.prevStairSensor, 
			print " ",
			print constants.STAIR_LIMIT
			if self.isDownStairs:
				self.isStairsDetected ^= True
				self.isDownStairs ^= True
				self.onPlatform = True #set to check if user is on platform
			else:
				self.isStairsDetected ^= True
				self.isUpStairs ^= True
			self.voiceOutput.say(messages.UP_STAIRS)
		self.prevStairSensor = self.stairSensor
	
	def guideAlongStairs(self):
		if self.stepDetected == 0:
			if (self.isStairsDetected is False) and not (self.isUpStairs and self.isDownStairs):
				#not on stairs
				return
			elif (self.isStairsDetected is True) and self.isUpStairs:
				message = messages.TAKE_ONE_STEP_TEMPLATE.format(direction = "up")
				print "                                           take one step up carefully"
				self.voiceOutput.say(message)
			elif (self.isStairsDetected is True) and self.isDownStairs:
				message = messages.TAKE_ONE_STEP_TEMPLATE.format(direction = "down")
				print "                                           take one step down carefully"
				self.voiceOutput.say(message)
			return
		else:
			#user taking a step
			if self.stepsOnPlatform:
				self.stepsOnPlatform += 1
			if self.stepsOnPlatform >= constants.MAX_ON_PLATFORM_STEPS: #user is not on platform
				self.onPlatform  = False
				self.stepsOnPlatform = 0
			return

		