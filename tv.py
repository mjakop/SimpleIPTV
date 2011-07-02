#! /usr/bin/python

# Simple IPTV player written in python using vlc bindings.
#
# Author: Matej Jakop <mjakop at gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import vlc
import time
import keybinder
import sys
from PyQt4 import QtGui, QtCore, QtOpenGL
from datetime import datetime
import hashlib
import json
import os


class Player:

	
	def __init__(self):
		self.p = vlc.MediaPlayer()

	def fullscreen(self):
		self.p.showFullScreen()

	def play(self,url):
		self.p.set_mrl(url)
		self.p.play()
		self.p.video_set_deinterlace("mean")

	def toggle_mute(self):
		self.p.audio_toggle_mute()

	def subtitles(self):
		l_all = self.p.video_get_spu_description()
		l_res = []
		k=0
		for (i,t) in l_all:
			if t.startswith("DVB"):
				name = unicode(t.split("[")[1].split("]")[0])
				l_res.append((k,name))
			k = k+1
		return l_res

	def set_subtitle(self, i):
		if self.p.video_get_spu_count() > 0:
			self.p.video_set_spu(i)
		#pass
	
	def crop(self, d,n):
		if d==None or n==None:
			self.p.video_set_crop_geometry(None)
		else:
			self.p.video_set_crop_geometry(d+":"+n)


class Playlist:

	def __init__(self):
		self.channel_settings = {}
		self.settings_file_name="channel_settings.json"
		self.load_settings_for_channels()

	def get_settings_dir(self):
		path = os.path.dirname(os.path.abspath( __file__ ))+"/"
		return path

	def load_settings_for_channels(self):
		if os.path.exists(self.get_settings_dir()+self.settings_file_name):
			f = open(self.get_settings_dir()+self.settings_file_name,"r")
			self.channel_settings = json.load(f)
			f.close()

	def save_settings_for_channels(self):
		text = json.dumps(self.channel_settings, indent=2)
		f = open(self.get_settings_dir()+self.settings_file_name, 'w')
		f.write(text)
		f.close()
	
	def loadM3U(self,filename):
		self.items = {}
		f = open(filename, 'r')
		last_number = None
		for line in f:
			if line.startswith("#EXTINF"):
        			parts = line.split(",")
				name = parts[1].strip()
				number = int(parts[0].strip().split(":")[1])
				self.items[number] = {"name":name}
				last_number = number
			elif line.startswith("udp://"):
				self.items[last_number]["url"] = line.strip()

	def next(self,number):
		 keys = self.items.keys()
		 index = keys.index(number)
		 if index < len(keys)-1:
		 	return keys[index+1]
		 else:
			return keys[index]

	def prev(self,number):
		 keys = self.items.keys()
		 index = keys.index(number)
		 if index > 0:
		 	return keys[index-1]
		 else:
			return keys[index]

		
	def get(self,number):
		try:
			return self.items[number]
		except:
			return None

	def get_uniq_id(self, number):
		item = self.get(number)
		return hashlib.md5(item["name"]).hexdigest()
		
	def set_channel_setting(self,number,key,value):
		cid = self.get_uniq_id(number)
		if not self.channel_settings.has_key(cid):
			self.channel_settings[cid]={}
		self.channel_settings[cid][key] = value
		self.save_settings_for_channels()

	def get_channel_setting(self, number, key, default):
		cid = self.get_uniq_id(number)
		if not self.channel_settings.has_key(cid):
			return default
		else:
			if not self.channel_settings[cid].has_key(key):
				return default
			else:
				return self.channel_settings[cid][key]	

	def get_channel_name(self, number):
		item = self.get(number)
		if item:
			return str(number)+" - "+unicode(item["name"])
		else:
			return "No channel"

class UIInfo(QtGui.QFrame):

	def __init__(self, master=None):
		QtGui.QFrame.__init__(self, master)
		layout = QtGui.QVBoxLayout()

		self.info_label = QtGui.QLabel("")
		font = QtGui.QFont("Helvetica", 24, QtGui.QFont.Bold)
		self.info_label.setFont(font);


		layout.addWidget(self.info_label)
		self.setLayout(layout)

	def display_text(self, text):
		self.last_text_change = datetime.now()
		self.setFixedHeight(50)
		self.info_label.setText(text)

	def timer_event(self):
		diff_last_change = datetime.now() - self.last_text_change
		diff_last_change = diff_last_change.seconds*1000.0 +diff_last_change.microseconds / 1000.0
		if diff_last_change > 1500.0:
			self.setFixedHeight(0)
		


class UIInterface(QtGui.QMainWindow):


	def __init__(self, master=None):
		QtGui.QMainWindow.__init__(self, master)
  		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		
		self.current_channel = 1
		self.prev_channel_number = 1
		self.channel_number = 0
		self.last_keypress_channel = None
		self.current_crop_mode = 0
		self.crop_modes = [(None,None),("4","3"),("16","9"),("16","10")]

		self.player = Player()
		self.playlist = Playlist()
		self.playlist.loadM3U("siol-mpeg4.m3u")
		self.create_ui()


	def create_ui(self):
		self.Widget = QtGui.QWidget(self)
	        self.setCentralWidget(self.Widget)
		
		self.VideoFrame = QtGui.QFrame()
        	palette = self.VideoFrame.palette()
		palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0,0,0))
        	self.VideoFrame.setPalette(palette)
        	self.VideoFrame.setAutoFillBackground(True)

		self.VBoxLayout = QtGui.QVBoxLayout()
		self.VBoxLayout.setSpacing(0);
		self.VBoxLayout.setMargin(0)
        	self.VBoxLayout.addWidget(self.VideoFrame)

		self.info = UIInfo()
		self.VBoxLayout.addWidget(self.info)

        	self.Widget.setLayout(self.VBoxLayout)


		self.Timer = QtCore.QTimer(self)
		self.connect(self.Timer, QtCore.SIGNAL("timeout()"),self.timer_event)
		self.Timer.start(200)
	

	def display_text(self, text):
		self.info.display_text(text)

	def play(self,number):
		item = self.playlist.get(number)
		self.player.play(item["url"])
		self.display_text(self.playlist.get_channel_name(number))
		self.prev_channel_number = self.current_channel
		self.current_channel = number
		self.selected_subtitles = -1

		self.start_playing_channel = datetime.now()
		#restore saved settings
		self.current_crop_mode = self.playlist.get_channel_setting(number,"crop_mode",0)
		self.change_crop(False, False)

        	if sys.platform == "linux2": # for Linux using the X Server
			self.player.p.set_xwindow(self.VideoFrame.winId())
        	elif sys.platform == "win32": # for Windows
			self.player.p.set_hwnd(self.VideoFrame.winId())
		elif sys.platform == "darwin": # for MacOS
			self.player.p.set_agl(self.VideoFrame.windId())
		self.info.show()

		

	def handle_channel_number_key_press(self,number):
		self.channel_number = int(str(self.channel_number) + str(number))
		if self.channel_number > 999:
			self.channel_number = number
		self.display_text(str(self.channel_number))
		self.last_keypress_channel =  datetime.now()

	def next_channel(self):
		number = self.playlist.next(self.current_channel)
		self.play(number)

	def prev_channel(self):
		number = self.playlist.prev(self.current_channel)
		self.play(number)

	def changeToChannel(self):
		channel = self.playlist.get(self.channel_number)
		if channel != None:
			self.play(self.channel_number)
		self.channel_number = 0
	
	def keyPressEvent(self, event):
		if event.key() == QtCore.Qt.Key_Escape:
			self.clean_and_close()
		elif event.key() >= QtCore.Qt.Key_0 and event.key() <= QtCore.Qt.Key_9:
			self.handle_channel_number_key_press(event.key() - QtCore.Qt.Key_0)
		elif event.key() == QtCore.Qt.Key_P:
			self.prev_channel()
		elif event.key() == QtCore.Qt.Key_N:
			self.next_channel()
		elif event.key() == QtCore.Qt.Key_M:
			self.player.toggle_mute()
		elif event.key() == QtCore.Qt.Key_C:
			self.change_crop()
		elif event.key() == QtCore.Qt.Key_I:
			self.display_info()
		elif event.key() == QtCore.Qt.Key_S:
			self.change_subtitle()		
		elif event.key() == QtCore.Qt.Key_K:
			self.back_to_prev_channel()

	def clean_and_close(self):
		self.close()

	def back_to_prev_channel(self):
		self.play(self.prev_channel_number)

	def change_subtitle(self, use_next=True, display_text=True):
		t = self.player.subtitles()
		if use_next:
			self.selected_subtitles = self.selected_subtitles + 1
		if self.selected_subtitles > len(t)-1:
			self.selected_subtitles = -1
		if self.selected_subtitles == -1:
			if display_text:
				self.display_text("No subtitles")
			self.player.set_subtitle(0)
		else:
			(i,name) = t[self.selected_subtitles]
			self.player.set_subtitle(i)
			if display_text:
				self.display_text("Subtitles: "+name)
		self.playlist.set_channel_setting(self.current_channel,"selected_subtitle", self.selected_subtitles)
			

	def change_crop(self,use_next=True, display_text=True):
		if self.current_crop_mode+1 > len(self.crop_modes)-1:
			self.current_crop_mode = -1
		if use_next:
			self.current_crop_mode = self.current_crop_mode + 1
		d,n = self.crop_modes[self.current_crop_mode]
		if display_text:
			if self.current_crop_mode == 0:
				self.display_text("Crop: Default")
			else:
				self.display_text("Crop: "+d+":"+n)
		self.playlist.set_channel_setting(self.current_channel,"crop_mode", self.current_crop_mode)
		self.player.crop(d,n)

	def display_info(self):
		info_text = self.playlist.get_channel_name(self.current_channel)
		if self.current_crop_mode==0:
			info_text_crop = "(Default)"
		else:
			d,n = self.crop_modes[self.current_crop_mode]
			info_text_crop = "("+str(d)+":"+str(n)+")"	
		self.display_text(info_text+" "+info_text_crop)

	def fullscreen(self):
		self.player.fullscreen()

	def timer_event(self):
		if self.last_keypress_channel:
			diff_key_press = datetime.now() - self.last_keypress_channel
			diff_key_press = diff_key_press.seconds*1000.0 +diff_key_press.microseconds / 1000.0
			if diff_key_press > 1000.0:
				self.changeToChannel()

		if self.start_playing_channel:
			diff_start_playing = datetime.now() - self.start_playing_channel
			diff_start_playing = diff_start_playing.seconds*1000.0 +diff_start_playing.microseconds / 1000.0
			if diff_start_playing > 5000.0:
				try:
					self.selected_subtitles = self.playlist.get_channel_setting(self.current_channel,"selected_subtitle",-1)
					self.change_subtitle(False, False)
					self.start_playing_channel=None
				except:
					pass

		self.info.timer_event()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ui = UIInterface()
    ui.showFullScreen()
    ui.play(1)
    sys.exit(app.exec_())

