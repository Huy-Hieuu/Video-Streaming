import sys
import time
from tkinter import *
from Client import Client

class VideoDashboard:
    def __init__(self, master):
        self.master = master
        self.master.title("Video Dashboard")
        self.master.geometry("400x300")
        self.videoScreen = None
        self.app = None

        # Create a frame to hold the buttons
        self.button_frame = Frame(self.master)
        self.button_frame.grid(row=0, column=0, padx=20, pady=20)

        # Create buttons for videos using grid
        self.video1_button = Button(self.button_frame, text="Video 1", command=self.play_video1)
        self.video1_button.grid(row=0, column=0, padx=10)
        self.video2_button = Button(self.button_frame, text="Video 2", command=self.play_video2)
        self.video2_button.grid(row=0, column=1, padx=10)
        self.video3_button = Button(self.button_frame, text="Video 3", command=self.play_video3)
        self.video3_button.grid(row=0, column=2, padx=10)

    def play_video1(self):
        self.play_video("movie.Mjpeg")  # Replace with the actual filename of video 1

    def play_video2(self):
        self.play_video("movie.Mjpeg")  # Replace with the actual filename of video 2

    def play_video3(self):
        self.play_video("movie.Mjpeg")  # Replace with the actual filename of video 3

    def play_video(self, filename):
        if self.videoScreen is not None and self.app.clientClosed is False:
            print("teardown but still in there")
            self.videoScreen.destroy()
            self.app.exitClient()
            time.sleep(0.5)
        # Call the Client class to play the selected video
        try:
            serverAddr = sys.argv[1]
            serverPort = sys.argv[2]
            rtpPort = sys.argv[3]
        except:
            print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")

        self.videoScreen = Toplevel()
        # Create a new client
        self.app = Client(self.videoScreen, serverAddr, serverPort, rtpPort, filename)
        # app.master.title("RTPClient")
        # self.master.withdraw()  # Hide the dashboard while video is playing

if __name__ == "__main__":
    root = Tk()

    # Create the video dashboard
    video_dashboard = VideoDashboard(root)

    root.mainloop()
