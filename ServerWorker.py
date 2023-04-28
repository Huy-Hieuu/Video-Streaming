import time
from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    FASTFORWARD = 'FASTFORWARD'
    REWIND = 'REWIND'
    STOP = 'STOP'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""

        # get new socket bc it returns (socket, address)
        #	=> use that socket for RTSP transfer
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)
            if data:
                print("Data received:\n" + data.decode("utf-8"))
                # process this Request
                self.processRtspRequest(data.decode("utf-8"))

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""

        # C: SETUP movie.Mjpeg RTSP/1.0
        # C: CSeq: 1
        # C: Transport: RTP/UDP; client_port= 25000

        # C: PLAY movie.Mjpeg RTSP/1.0
        # C: CSeq: 4
        # C: Session: 123456

        # C: FASTFORWARD
        # C: CSeq: 123

        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)

                # Send RTSP reply
                self.replyRtsp(self.OK_200, seq[1])

                # Get the RTP/UDP port from the last line
                # client_port= 25000
                # split that space and get port
                self.clientInfo['rtpPort'] = request[2].split(' ')[3]
        # process STOP request
        elif requestType == self.STOP:
            self.clientInfo['event'].set() #Stop Sending RTP packet
            time.sleep(0.1)
            print("Processing STOP \n")
            self.state = self.READY
            self.clientInfo['videoStream'].moveToFirstPosition()
            self.replyRtsp(self.OK_200, seq[1])


        # process FASTFORWARD request
        elif requestType == self.REWIND:
            self.clientInfo['event'].set() #stop SEND RTP PACKET
            print("processing REWIND\n")
            self.state = self.READY # IN ORDER TO SWITCH TO PLAY MODE
            self.rewindRtp(40)
            self.replyRtsp(self.OK_200, seq[1])

        # process FASTFORWARD request
        elif requestType == self.FASTFORWARD:
            # neu ben nay giu lai self.clientInfo['event'].set()
            # => client() vua goi da bi set => out
            self.clientInfo['event'].set() #stop SEND RTP PACKET
            print("processing FASTFORWARD\n")
            self.state = self.READY # IN ORDER TO SWITCH TO PLAY MODE
            self.skipRtp(40)
            self.replyRtsp(self.OK_200, seq[1])

        # Process PLAY request
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                # Create a new socket for RTP/UDP
                # Because RTP is sent over UDP => low-latency
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.replyRtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()
                print("THREAD ID: ", self.clientInfo['worker'].ident)

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.replyRtsp(self.OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            self.clientInfo['event'].set()

            self.replyRtsp(self.OK_200, seq[1])

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            # wait for event to be set or if time expires => continue
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                print("<PAUSE SENDING RTP PACKET < isSet() > > !!! \n")
                break

            # print("frame number: " + str(self.clientInfo['videoStream'].frameNbr()) + "\n")
            #
            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()

                # SEND PACKET TO ADDRESS AND PORT OF SELF.RTPSOCKET BEN CLIENT
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber), (address, port))
                    print("SENDING RTP PACKET \n")
                except Exception as e:
                    print("Connection Error \n Video is finished!!!")
                    print("Error: " + str(e) + "\n")
                    break
                # print('-'*60)
                # traceback.print_exc(file=sys.stdout)
                # print('-'*60)

    def skipRtp(self, num_frames_to_skip):
        try:
            self.clientInfo['videoStream'].fastForward(num_frames_to_skip)
        except:
            print("Error in skip packet")

    def rewindRtp(self, num_frames_to_back):
        try:
            self.clientInfo['videoStream'].rewind(num_frames_to_back)
        except:
            print("Error in rewind packet")

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            # print("200 OK")
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
