# Re-import required modules after code execution state reset
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import threading
import time
import feedparser
import requests
import os
import pygame

# Constants
DEFAULT_ALARM_SOUND = "gentle_pastures.mp3"  # Must exist in the working directory
PODCAST_FILE = "latest_podcast.mp3"

# Initialize Pygame Mixer
pygame.mixer.init()


class AlarmClockApp:
    def __init__(self, master):
        self.master = master
        master.title("Python Alarm Clock")

        self.alarm_time = None
        self.snooze_duration = 5
        self.snooze_end_time = None
        self.rss_feed = None
        self.alarm_thread = None
        self.stop_alarm_flag = False
        self.snoozing = False

        # GUI: Current time
        self.time_label = tk.Label(master, font=("Helvetica", 48))
        self.time_label.pack(pady=10)

        # GUI: Alarm Time Pickers
        picker_frame = tk.Frame(master)
        picker_frame.pack(pady=5)

        self.hour_var = tk.StringVar(value="07")
        self.minute_var = tk.StringVar(value="00")

        self.hour_spinbox = tk.Spinbox(picker_frame, from_=0, to=23, textvariable=self.hour_var, width=5, format="%02.0f")
        self.hour_spinbox.pack(side="left")

        self.minute_spinbox = tk.Spinbox(picker_frame, from_=0, to=59, textvariable=self.minute_var, width=5, format="%02.0f")
        self.minute_spinbox.pack(side="left")

        # GUI: Snooze duration controls
        snooze_frame = tk.Frame(master)
        snooze_frame.pack(pady=5)

        self.snooze_label = tk.Label(snooze_frame, text=f"Snooze: {self.snooze_duration} min")
        self.snooze_label.pack(side="left")

        self.decrease_btn = tk.Button(snooze_frame, text="-", command=self.decrease_snooze)
        self.decrease_btn.pack(side="left")

        self.increase_btn = tk.Button(snooze_frame, text="+", command=self.increase_snooze)
        self.increase_btn.pack(side="left")

        # GUI: RSS feed
        self.rss_entry = tk.Entry(master, width=50)
        self.rss_entry.insert(0, "Optional RSS Feed URL")
        self.rss_entry.pack(pady=5)

        # GUI: Buttons
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        self.set_button = tk.Button(button_frame, text="Set Alarm", command=self.set_alarm)
        self.set_button.pack(side="left", padx=5)

        self.snooze_button = tk.Button(button_frame, text="Snooze", command=self.snooze)
        self.snooze_button.pack(side="left", padx=5)
        self.snooze_button.config(state=tk.DISABLED)

        self.stop_button = tk.Button(button_frame, text="Stop Alarm", command=self.stop_alarm)
        self.stop_button.pack(side="left", padx=5)
        self.stop_button.config(state=tk.DISABLED)

        # GUI: Snooze countdown
        self.countdown_label = tk.Label(master, font=("Helvetica", 14))
        self.countdown_label.pack(pady=5)

        self.update_clock()

    def update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        if self.snoozing and self.snooze_end_time:
            remaining = self.snooze_end_time - datetime.now()
            if remaining.total_seconds() > 0:
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                self.countdown_label.config(text=f"Snoozing… {mins} min {secs} sec left")
            else:
                self.countdown_label.config(text="")
                self.snoozing = False
        self.master.after(1000, self.update_clock)

    def set_alarm(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            now = datetime.now()
            self.alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if self.alarm_time < now:
                self.alarm_time += timedelta(days=1)

            rss = self.rss_entry.get().strip()
            self.rss_feed = rss if rss else None

            self.set_button.config(state=tk.DISABLED)
            self.alarm_thread = threading.Thread(target=self.wait_for_alarm)
            self.alarm_thread.daemon = True
            self.alarm_thread.start()

            messagebox.showinfo("Alarm Set", f"Alarm set for {self.alarm_time.strftime('%H:%M')}")
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter valid hour and minute.")

    def wait_for_alarm(self):
        while datetime.now() < self.alarm_time and not self.stop_alarm_flag:
            time.sleep(1)
        if not self.stop_alarm_flag:
            self.play_alarm()

    def play_alarm(self):
        self.snooze_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        sound_file = DEFAULT_ALARM_SOUND

        if self.rss_feed:
            try:
                feed = feedparser.parse(self.rss_feed)
                audio_url = feed.entries[0].enclosures[0]['href']
                response = requests.get(audio_url, stream=True)
                with open(PODCAST_FILE, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                sound_file = PODCAST_FILE
            except Exception as e:
                print(f"Failed to load podcast: {e}")

        try:
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play alarm sound: {e}")

    def snooze(self):
        self.stop_alarm_flag = True
        pygame.mixer.music.stop()
        self.snooze_end_time = datetime.now() + timedelta(minutes=self.snooze_duration)
        self.alarm_time = self.snooze_end_time
        self.snoozing = True
        self.snooze_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.set_button.config(state=tk.DISABLED)
        self.stop_alarm_flag = False
        self.alarm_thread = threading.Thread(target=self.wait_for_alarm)
        self.alarm_thread.daemon = True
        self.alarm_thread.start()

    def stop_alarm(self):
        self.stop_alarm_flag = True
        pygame.mixer.music.stop()
        self.set_button.config(state=tk.NORMAL)
        self.snooze_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.countdown_label.config(text="")
        self.snoozing = False

    def increase_snooze(self):
        self.snooze_duration += 1
        self.snooze_label.config(text=f"Snooze: {self.snooze_duration} min")

    def decrease_snooze(self):
        if self.snooze_duration > 1:
            self.snooze_duration -= 1
            self.snooze_label.config(text=f"Snooze: {self.snooze_duration} min")


# Run the app
root = tk.Tk()
app = AlarmClockApp(root)
root.mainloop()
