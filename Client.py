import time
from tkinter import *
import tkinter.messagebox as tkMessageBox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	REWIND = 4
	FASTFORWARD = 5
	STOP = 6
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.createWidgets()
		self.connectToServer() #Create socket to CONNECT to Server
		self.frameNbr = 0
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #Create socket to LISTEN from Server
		self.setupMovie()
		self.forwardDone = threading.Event()
		self.rewindDone = threading.Event()
		self.clientClosed = False

	def createWidgets(self):

		print("received: " + str(self.fileName))
		"""Build GUI."""
		# Create Setup button
		self.rewind = Button(self.master, width=10, padx=1.5, pady=1.5)
		self.rewind["text"] = "<<"
		self.rewind["command"] = self.rewindMovie
		self.rewind.grid(row=1, column=1, padx=1.5, pady=1.5)

		self.fast_forward = Button(self.master, width=10, padx=1.5, pady=1.5)
		self.fast_forward["text"] = ">>"
		self.fast_forward["command"] = self.fastForwardMovie
		self.fast_forward.grid(row=1, column=2, padx=1.5, pady=1.5)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=3, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=4, padx=2, pady=2)

		#Create Stop button
		self.stop = Button(self.master, width=10, padx=3, pady=3)
		self.stop["text"] = "Stop"
		self.stop["command"] =  self.stopMovie
		self.stop.grid(row=1, column=5, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master, width=10, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=6, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=10, sticky=W+E+N+S, padx=5, pady=5)
		# self.label.grid(row=0, column=0, columnspan=6, rowspan=2, sticky=N + S + E + W)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
			self.playEvent = threading.Event()

	def noneFunction(self):
		pass
	def stopMovie(self):
		self.sendRtspRequest(self.STOP)
		self.playEvent.set()  # Stop listen RTP packet
		time.sleep(0.1)
		self.state = self.READY
		self.frameNbr = 0
		self.start["text"] = "Play Again"
		self.rewind["command"] = self.noneFunction
		self.fast_forward["command"] = self.noneFunction
		self.pause["command"] = self.noneFunction

	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		time.sleep(0.5)
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

		self.clientClosed = True


	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)

	def rewindMovie(self):
		self.rewindDone.clear()
		self.sendRtspRequest(self.REWIND)
		self.playEvent.set()  # Stop listenRtp threading

		self.rewindDone.wait()  # waiting for receive OK request

		if self.rewindDone.isSet():
			self.state = self.READY
			self.playMovie()

	def fastForwardMovie(self):
		self.forwardDone.clear()
		self.sendRtspRequest(self.FASTFORWARD)
		self.playEvent.set() # Stop listenRtp threading

		self.forwardDone.wait() # waiting for receive OK request

		if self.forwardDone.isSet():
			self.state = self.READY
			self.playMovie()

		# khi call 2 lan fastForwardMovie
		# => tao ra 2 thread moi self.playMovie() to recvRTPpacket
		# => send PAUSE no se chi dung lai 1 thread con thread kia van se chay tiep


	def playMovie(self):
		"""Play button handler."""
		if self.start['text'] == "Play Again":
			self.rewind["command"] = self.rewindMovie
			self.fast_forward["command"] = self.fastForwardMovie
			self.pause["command"] = self.pauseMovie
			self.start["text"] = "Play"

		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()

			#SET EVENT TO FALSE
			# => IF self.playEvent is set => stop
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				# self.rtpSocket.settimeout(2.0)
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
					self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			# except socket.timeout:
			# 	print("Timeout: No data received within 2 seconds")
			# 	# Stop listening upon requesting PAUSE or TEARDOWN
			# 	break
			except:
				if self.playEvent.isSet():
					print("----- playEvent is SET -----")
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		print("Updated Movie !!")
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = 1

			# Write the RTSP request to be sent.
			# request = ...
			request = "SETUP " + str(self.fileName) + "\n " + str(self.rtspSeq) + " \n RTSP/1.0 RTP/UDP " + str(self.rtpPort)

			self.rtspSocket.send(request.encode())
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.SETUP

		elif requestCode == self.STOP:
			self.rtspSeq = self.rtspSeq + 1
			request = "STOP " + "\n " + str(self.rtspSeq)

			self.rtspSocket.send(request.encode("utf-8"))

			print ('-'*60 + "\nSTOP request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.STOP

		elif requestCode == self.REWIND:
			self.rtspSeq = self.rtspSeq + 1
			request = "REWIND " + "\n " + str(self.rtspSeq)

			self.rtspSocket.send(request.encode("utf-8"))

			print ('-'*60 + "\nREWIND request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.REWIND

		# Fastforward request
		elif requestCode == self.FASTFORWARD:
			self.rtspSeq = self.rtspSeq + 1
			request = "FASTFORWARD " + "\n " + str(self.rtspSeq)

			self.rtspSocket.send(request.encode("utf-8"))

			print ('-'*60 + "\nFASTFORWARD request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.FASTFORWARD
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PLAY " + "\n " + str(self.rtspSeq)

			self.rtspSocket.send(request.encode("utf-8"))
			print ('-'*60 + "\nPLAY request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PLAY
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PAUSE " + "\n " + str(self.rtspSeq)
			self.rtspSocket.send(request.encode("utf-8"))
			print ('-'*60 + "\nPAUSE request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PAUSE
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "TEARDOWN " + "\n " + str(self.rtspSeq)
			self.rtspSocket.send(request.encode("utf-8"))
			print ('-'*60 + "\nTEARDOWN request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.TEARDOWN
		else:
			return
		
		# Send the RTSP request using rtspSocket.
		# ...
		
		print('\nData sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						print ("Updating RTSP state...")
						# self.state = ...
						self.state = self.READY
						# Open RTP port.
						#self.openRtpPort()
						print ("Setting Up RtpPort for Video Stream")
						self.openRtpPort()
					elif self.requestSent == self.STOP:
						print ('-'*60 + "\nClient is STOPPING...\n" + '-'*60)

					elif self.requestSent == self.REWIND:
						self.rewindDone.set()
						print ('-'*60 + "\nClient is REWINDING...\n" + '-'*60)

					elif self.requestSent == self.FASTFORWARD:
						self.forwardDone.set()
						print ('-'*60 + "\nClient is FORWARDING...\n" + '-'*60)

					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
						print ('-'*60 + "\nClient is PLAYING...\n" + '-'*60)

					elif self.requestSent == self.PAUSE:
						self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# self.state = ...
						
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...
		self.rtpSocket.settimeout(0.5)
		# Set the timeout value of the socket to 0.5sec
		# ...
		
		try:
			self.rtpSocket.bind((self.serverAddr,self.rtpPort))   # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
			#self.rtpSocket.listen(5)
			print ("Bind RtpPort Success")
		except:
			tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()


