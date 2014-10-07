#!/usr/bin/python
import sys
import requests
import urllib
import json
import os.path
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

# buildings = [{'name':"DemoBuilding",'level':['1','2','3']}, {'name':"COM1",'level':['1','2','3']} , {'name':"COM2", 'level': ['1','2','3']}]

cache_opts = {
	'cache.type': 'file',
	'cache.data_dir': '/tmp/cache/data',
	'cache.lock_dir': '/tmp/cache/lock'
}

class Storage():
	def writeToFile(self, filename, content):
		f = open(filename, 'w')
		f.write(content)
		f.close()
	def isFileExist(self, filename):
		content = ""
		if os.path.isfile(filename) and os.access(filename, os.R_OK):
			return True
		else:
			self.writeToFile(filename, content)  # to recreate a new file
			return False
	def readFromFile(self, filename):
		if self.isFileExist(filename):
			f = open(filename, 'r')
			data = f.read()
			f.close
			return data
	def appendToFile(self, filename, content):
		f = open(filename, 'a')
		f.write(content)  # to append on the end of the file
		f.close()

class MapSync(object):
	def __init__(self):
		self.val = 0
		self.info = []
		self.mapInfo = []
		self.wifiInfo = []
		self.mapNodes = {}
		self.apNodes = {}
		self.fileManager = Storage()
		cache = CacheManager(**parse_cache_config_options(cache_opts))
		self.cache_manager = cache.get_cache('map.php', expire=3600)  #--- get specific cache from cacheManager
		try:
			building_json = self.fileManager.readFromFile("buildinglist.txt") 
			self.buildings = json.loads(building_json)
			print "building loaded"
		except:
			return

	def getMap(self):
		return self.mapNodes
	
	def getNorth(self):
		return self.mapInfo
	
	def getAPNodes(self):
		return self.apNodes
		
	def __extractingLinkToNodes(self, linkToString):
		linkToString = str(linkToString)
		linkToNodes = linkToString.split(",")
		linkToNodes2 = []
		for x in linkToNodes:
			node = ""
			for i in x:
				if i.isdigit():
					node += i
			linkToNodes2.append(node)
	
		return linkToNodes2
		
	def determineNorth(self, info):
		north = str(info['northAt'])
		return north
	
	def extractMapNodes(self):
		for node in self.mapInfo:
			nodeData = {}
			nodeData['name'] = str(node['nodeName'])
			nodeData['x'] = str(node['x'])
			nodeData['y'] = str(node['y'])
			nodeData['linkTo'] = self.__extractingLinkToNodes(node['linkTo'])
			self.mapNodes[str(node['nodeId'])] = nodeData
	
	def extractWifiNodes(self):
		for node in self.wifiInfo:
			nodeData = {}
			nodeData['name'] = str(node['nodeName'])
			nodeData['x'] = str(node['x'])
			nodeData['y'] = str(node['y'])
			nodeData['id'] = node['nodeId']
			macAddr = str(node['macAddr']).upper()
			self.apNodes[macAddr[0:14]] = nodeData
	
	def determineSource(self, building_name, level_value):
		url = 'http://showmyway.comp.nus.edu.sg/getMapInfo.php?Building=' + building_name + "&Level=" + level_value 
		# req = requests.request('GET', 'http://showmyway.comp.nus.edu.sg/getMapInfo.php?Building=DemoBuilding&Level=1')
		req = urllib.urlopen(url)
		source = req.read()
		req.close()
		source = json.loads(source)
		return source

	def separateAllInfos(self, source):
		self.info = source['info']
		self.mapInfo = source['map']
		self.wifiInfo = source['wifi']
		# print "in determineInfos"

	def getFromCache(self, request):
		return self.cache_manager.get(request)

	def reloadAllMaps(self):
		self.fileManager.writeToFile("buildings.txt", "")
		try:
			building_json = self.fileManager.readFromFile("buildinglist.txt") 
			self.buildings = json.loads(building_json)
		except:
			print sys.exc_info()[0]
		self.downloadAllMaps()
				
	def downloadAllMaps(self):
		if not self.fileManager.isFileExist("buildings.txt") or self.fileManager.readFromFile("buildings.txt") == "":
			print "			 downloading map"
			cacheArray = []
			for building in self.buildings:
				buildingName = building['name']
				for level in building['level']:
					source = self.determineSource(buildingName, level)
					self.separateAllInfos(source)
					self.extractMapNodes()  #--- Got the nodes from map
					self.extractWifiNodes()
					cacheArray.append(self.cacheData(buildingName, level))
			self.fileManager.appendToFile("buildings.txt", json.dumps(cacheArray))
		else:
			print "			 loading map from storage"
			array_of_cache = self.fileManager.readFromFile("buildings.txt")
			array_of_cache = json.loads(array_of_cache)
			for cache in array_of_cache:
				self.cache_manager.put(cache['map_name'], cache)

		print "done caching"
		
	def cacheData(self, buildingName, level):
		cache = {}
		cache['map_name'] = buildingName + level
		cache['map'] = self.mapNodes
		cache['wifi'] = self.apNodes
		cache['info'] = self.info
		self.cache_manager.put(buildingName + level, cache)
		return cache
