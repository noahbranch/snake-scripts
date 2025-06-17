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
import vlc

# Constants
DEFAULT_ALARM_SOUND = os.path.join(os.path.dirname(__file__), "gentle_pastures.mp3")  # Now reads from alarm-clock folder
PODCAST_FILE = "latest_podcast.mp3"

# Initialize Pygame Mixer
pygame.mixer.init()


class AlarmClockApp:
    def __init__(self, master):
        self.master = master
        master.title("Alarm Clock")
        master.config(bg="black")

        self.alarm_time = None
        self.snooze_duration = 5
        self.snooze_end_time = None
        self.rss_feed = None
        self.alarm_thread = None
        self.stop_alarm_flag = False
        self.snoozing = False

        # GUI: Current time
        self.time_label = tk.Label(master,
            font=("Consolas", 48, "bold"),  # Monospace font
            fg="#00FF00",                   # Green color
            bg="black")
        self.time_label.pack(pady=10)

        # GUI: Alarm Time Pickers
        picker_frame = tk.Frame(master, bg="black")
        picker_frame.pack(pady=5)
        self.picker_frame = picker_frame  # Save reference for hiding

        self.hour_var = tk.StringVar(value="07")
        self.minute_var = tk.StringVar(value="00")

        self.hour_spinbox = tk.Spinbox(
            picker_frame, from_=0, to=23, textvariable=self.hour_var, width=5, format="%02.0f",
            font=("Consolas", 16), fg="#00FF00", bg="black", insertbackground="#00FF00"
        )
        self.hour_spinbox.pack(side="left")

        self.minute_spinbox = tk.Spinbox(
            picker_frame, from_=0, to=59, textvariable=self.minute_var, width=5, format="%02.0f",
            font=("Consolas", 16), fg="#00FF00", bg="black", insertbackground="#00FF00"
        )
        self.minute_spinbox.pack(side="left")

        # Label to show next alarm time
        self.next_alarm_label = tk.Label(master, font=("Consolas", 16), fg="#00FF00", bg="black")
        self.next_alarm_label.pack(pady=5)
        self.next_alarm_label.pack_forget()  # Hide initially

        # Controls frame for hiding/showing
        self.controls_frame = tk.Frame(master, bg="black")
        self.controls_frame.pack(pady=5)

        # GUI: Snooze duration controls
        snooze_frame = tk.Frame(self.controls_frame, bg="black")
        snooze_frame.pack(pady=5)

        self.snooze_label = tk.Label(snooze_frame, text=f"Snooze: {self.snooze_duration} min",
                                     font=("Consolas", 12), fg="#00FF00", bg="black")
        self.snooze_label.pack(side="left")

        self.decrease_btn = tk.Button(snooze_frame, text="-", command=self.decrease_snooze,
                                      font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.decrease_btn.pack(side="left")

        self.increase_btn = tk.Button(snooze_frame, text="+", command=self.increase_snooze,
                                      font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.increase_btn.pack(side="left")

        # GUI: RSS feed
        self.rss_entry = tk.Entry(self.controls_frame, width=50,
                                  font=("Consolas", 12), fg="#00FF00", bg="black", insertbackground="#00FF00")
        self.rss_entry.insert(0, "")
        self.rss_entry.pack(pady=5)

        # GUI: Buttons
        button_frame = tk.Frame(self.controls_frame, bg="black")
        button_frame.pack(pady=5)

        self.set_button = tk.Button(button_frame, text="Set Alarm", command=self.set_alarm,
                                   font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.set_button.pack(side="left", padx=5)

        self.snooze_button = tk.Button(button_frame, text="Snooze", command=self.snooze,
                                       font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.snooze_button.pack(side="left", padx=5)
        self.snooze_button.config(state=tk.DISABLED)

        self.stop_button = tk.Button(button_frame, text="Stop Alarm", command=self.stop_alarm,
                                     font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.stop_button.pack(side="left", padx=5)
        self.stop_button.config(state=tk.DISABLED)

        self.cancel_button = tk.Button(button_frame, text="Cancel Alarm", command=self.cancel_alarm,
                                      font=("Consolas", 12), fg="#00FF00", bg="black", activebackground="#222")
        self.cancel_button.pack(side="left", padx=5)
        self.cancel_button.config(state=tk.DISABLED)
        self.stop_button.pack_forget()  # Hide stop button initially

        # GUI: Snooze countdown
        self.countdown_label = tk.Label(master, font=("Consolas", 14), fg="#00FF00", bg="black")
        self.countdown_label.pack(pady=5)

        # Hide controls timer
        self.hide_controls_after = 10_000  # 10 seconds in ms
        self.hide_controls_job = None
        self.alarm_is_set = False
        self.master.bind("<Button-1>", self.on_screen_click)

        self.update_clock()

    def hide_controls(self):
        self.controls_frame.pack_forget()

    def show_controls(self):
        self.controls_frame.pack(pady=5)
        self.reset_hide_controls_timer()

    def reset_hide_controls_timer(self):
        if self.hide_controls_job:
            self.master.after_cancel(self.hide_controls_job)
        if self.alarm_is_set:
            self.hide_controls_job = self.master.after(self.hide_controls_after, self.hide_controls)

    def on_screen_click(self, event):
        if self.alarm_is_set and not self.controls_frame.winfo_ismapped():
            self.show_controls()

    def update_clock(self):
        now = datetime.now().strftime("%H:%M")
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
            self.cancel_button.config(state=tk.NORMAL)
            self.stop_button.pack_forget()
            self.cancel_button.pack(side="left", padx=5)
            self.alarm_thread = threading.Thread(target=self.wait_for_alarm)
            self.alarm_thread.daemon = True
            self.alarm_thread.start()

            self.alarm_is_set = True
            self.hide_controls()  # Hide controls except time
            self.reset_hide_controls_timer()

            # Hide time pickers and show next alarm label
            self.picker_frame.pack_forget()
            self.next_alarm_label.config(text=f"Next alarm: {self.alarm_time.strftime('%H:%M')}")
            self.next_alarm_label.pack(pady=5)
            
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter valid hour and minute.")

    def wait_for_alarm(self):
        while datetime.now() < self.alarm_time and not self.stop_alarm_flag:
            time.sleep(1)
        if not self.stop_alarm_flag:
            self.play_alarm()

    def play_alarm(self):
        self.snooze_button.config(state=tk.NORMAL)
        self.cancel_button.pack_forget()
        self.stop_button.pack(side="left", padx=5)
        self.stop_button.config(state=tk.NORMAL)
        sound_file = DEFAULT_ALARM_SOUND
        use_vlc = False

        if self.rss_feed:
            try:
                feed = feedparser.parse(self.rss_feed)
                audio_url = feed.entries[0].enclosures[0]['href']
                self.vlc_player = vlc.MediaPlayer(audio_url)
                self.vlc_player.play()
                use_vlc = True
            except Exception as e:
                print(f"Failed to stream podcast: {e}")

        if not use_vlc:
            try:
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.set_volume(0.1)
                pygame.mixer.music.play()
                self.alarm_volume = 0.1
                self.volume_increase_thread = threading.Thread(target=self.increase_alarm_volume)
                self.volume_increase_thread.daemon = True
                self.volume_increase_thread.start()
            except Exception as e:
                messagebox.showerror("Playback Error", f"Could not play alarm sound: {e}")

    def snooze(self):
        self.stop_alarm_flag = True
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player = None
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
        self.hide_controls()  # Hide controls again after snooze
        self.reset_hide_controls_timer()

    def increase_alarm_volume(self):
        while self.alarm_volume < 1.0 and pygame.mixer.music.get_busy():
            time.sleep(10)
            self.alarm_volume = min(1.0, self.alarm_volume + 0.1)
            pygame.mixer.music.set_volume(self.alarm_volume)

    def stop_alarm(self):
        self.stop_alarm_flag = True
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player = None
        pygame.mixer.music.stop()
        self.set_button.config(state=tk.NORMAL)
        self.snooze_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.stop_button.pack_forget()
        self.cancel_button.pack_forget()
        self.countdown_label.config(text="")
        self.snoozing = False
        self.alarm_is_set = False
        self.show_controls()  # Show controls again
        if self.hide_controls_job:
            self.master.after_cancel(self.hide_controls_job)
            self.hide_controls_job = None
        # Reset alarm volume
        self.alarm_volume = 0.1
        # Show time pickers and hide next alarm label
        self.next_alarm_label.pack_forget()
        self.picker_frame.pack(pady=5)

    def cancel_alarm(self):
        self.stop_alarm_flag = True
        self.set_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.snooze_button.config(state=tk.DISABLED)
        self.countdown_label.config(text="")
        self.snoozing = False
        self.alarm_is_set = False
        self.show_controls()  # Show controls again
        if self.hide_controls_job:
            self.master.after_cancel(self.hide_controls_job)
            self.hide_controls_job = None
        # Reset alarm volume
        self.alarm_volume = 0.1
        # Show time pickers and hide next alarm label
        self.next_alarm_label.pack_forget()
        self.picker_frame.pack(pady=5)

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
