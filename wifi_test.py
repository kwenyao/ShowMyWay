import sys
from wifi import Wifi
from ServerSync import MapSync


def getLocation():
# 	inputMap = raw_input("Map: ")
# 	inputLevel = raw_input("Level: ")
	
	#for testing
	inputMap = "COM1"
	inputLevel = 2
	
	location = str(inputMap)+str(inputLevel)
	return location

def main():
	currmap = MapSync()
	wifi = Wifi()
	
	location = getLocation()
	currmap.loadLocation(location)
	
	# print packet
# 	apNodes = packet.get('wifi')
	
	north = currmap.getNorth()
	mapNodes = currmap.getMap()
	apNodes = currmap.getAPNodes()

	coords = wifi.getUserCoordinates(apNodes)
	print coords

if __name__ == "__main__":
	main()