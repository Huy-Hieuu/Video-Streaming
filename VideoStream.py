import os
class VideoStream:
	def __init__(self, filename):
		self.frameVector = [{"mixLength": None, "data": None} for _ in range(1000)]
		self.curMaxFrame = 0
		self.filename = filename
		self.file_size = os.path.getsize(filename)
		try:
			self.file = open(filename, 'rb')
		except:
			raise IOError
		self.frameNum = -1

	def moveToFirstPosition(self):
		self.file.seek(0, 0)
		self.frameNum = -1
		print("move to first position")

	def nextFrame(self):
		"""Get next frame."""
		self.frameNum += 1

		#data is binary data type
		if self.frameNum < self.curMaxFrame and self.frameVector[self.frameNum]["data"] is not None:
			print("Data is already read => Need not read again!!!")
			print("Old Data is returned!!, " + str(self.frameVector[self.frameNum]))
			self.file.seek(self.frameVector[self.frameNum]["mixLength"], 1)
			print("frameNumber: " + str(self.frameNum) + " current position: " + str(self.file.tell()) + "\n")

			return self.frameVector[self.frameNum]["data"]

		data = self.file.read(5) # Get the framelength from the first 5 bits
		print("DATA RECEIVED: " + str(data) + "\n")
		framelength = 0
		if data:
			framelength = int(data)
			# Read the current frame
			data = self.file.read(framelength)

		if self.frameNum < self.curMaxFrame and self.frameVector[self.frameNum]["data"] is None: # if it is None => replace None by Data
			self.frameVector[self.frameNum]["data"] = data
			print("Data is assigned!!, " + str(self.frameVector[self.frameNum]) + "\n")

		else:  #or if frameNum >= len(frameVector)
			if framelength == 0:
				print("Error in read frame length")
			self.frameVector[self.frameNum] = {"mixLength": framelength + 5, "data": data}
			print("New frameNum is assigned!!", str(self.frameVector[self.frameNum]) + "\n")
			self.curMaxFrame += 1 #if add new frame => curMaxFrame is increased

		print("mixLength: " + str(self.frameVector[self.frameNum]["mixLength"]))
		print("NEXTFRAME frame number: " + str(self.frameNum) + " current position: " + str(self.file.tell()) + "\n")
		return data
	
	def fastForward(self, num_frames_to_skip):
		"""Skip ahead by a specified number of frames."""
		print("ENTRY IN FASTFORWARD \n")
		for _ in range(num_frames_to_skip):
			data = self.file.read(5) # Get the framelength from the first 5 bytes
			if data: 
				framelength = int(data.decode('utf-8', errors='replace'), 10)
				self.file.seek(framelength, 1) # Skip the current frame by moving the file pointer

				self.frameNum += 1

				if self.frameVector[self.frameNum]["data"] is not None: # if it already read data before
					continue
				self.frameVector[self.frameNum] = {"mixLength": framelength + 5, "data": None} #else update size of frame and header


			print("FASTFORWARD frame number: " + str(self.frameNum) + " current position: " + str(self.file.tell()) + "\n")

	def rewind(self, num_frames_to_back):
		seekPoint = 0
		print("ENTRY IN REWIND \n")
		for _ in range(num_frames_to_back):
			if self.frameNum == -1:
				self.file.seek(0, 0)
				print("REWIND frame number: " + str(self.frameNum) + " current position: " + str(self.file.tell()) + "\n")
				return

			backPos = self.frameVector[self.frameNum]["mixLength"]
			# print("BackPOS value: " + str(backPos))

			seekPoint += backPos
			self.frameNum -= 1

		self.file.seek(-seekPoint, 1)
		print("REWIND frame number: " + str(self.frameNum) + " current position: " + str(self.file.tell()) + "\n")

			
	def isFinished(self):
		return self.file.tell() >= self.file_size - 1

	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	
	