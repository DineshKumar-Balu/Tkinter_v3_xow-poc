import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import pytesseract
from PIL import Image, ImageTk
from datetime import datetime, timedelta
import re
import subprocess
import platform
import pandas as pd
import customtkinter
import vlc
import os
import platform
import tempfile
import sys

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg-v1", "bin", "ffmpeg.exe")
    else:
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg-v1", "bin", "ffmpeg.exe")
    
    return ffmpeg_path


if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = os.path.join(os.path.dirname(__file__), "Tesseract-OCR", "tesseract.exe")
else:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def extract_timestamp(frame, x=0, y=0, w=1000, h=100):
    try:
        timestamp_crop = frame[y:y+h, x:x+w]
        timestamp_grey = cv2.cvtColor(timestamp_crop, cv2.COLOR_BGR2GRAY)
        _, timestamp_thresh = cv2.threshold(timestamp_grey, 127, 255, cv2.THRESH_BINARY)
        candidate_str = pytesseract.image_to_string(timestamp_thresh, config='--psm 6')
        
        regex_str = r'Date:\s(\d{4}-\d{2}-\d{2})\sTime:\s(\d{2}:\d{2}:\d{2}\s(?:AM|PM))\sFrame:\s(\d{2}:\d{2}:\d{2}:\d{2})'
        match = re.search(regex_str, candidate_str)
        
        if match:
            date_str, time_str, frame_str = match.groups()
            return date_str, time_str, frame_str
    except Exception as e:
        print(f"Error extracting timestamp: {e}")
    return None, None, None

def get_video_timestamp(video_path, frame_position):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return extract_timestamp(frame)
    return None, None, None

def get_initial_time(video_path):
    date_str, time_str, _ = get_video_timestamp(video_path, 0)
    return time_str if time_str else "00:00:00 AM"

def get_video_end_time(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    date_str, time_str, _ = get_video_timestamp(video_path, frame_count - 1)
    cap.release()
    return time_str if time_str else "00:00:00 AM"

def parse_time(time_str):
    """Parses a time string into a datetime object, handling multiple formats."""
    time_str = time_str.strip()  # Remove any leading or trailing whitespace
    
    formats = ['%I:%M:%S %p', '%H:%M:%S']  # Define possible time formats
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            print(f"Successfully parsed '{time_str}' using format '{fmt}' to {parsed_time}")
            return parsed_time
        except ValueError as e:
            print(f"Failed to parse '{time_str}' with format '{fmt}': {e}")
            continue
    
    print(f"Error parsing time '{time_str}' with all formats")
    return None

def time_to_seconds(time_str):
    try:
        # Parsing the 12-hour format with AM/PM
        time_obj = datetime.strptime(time_str, '%I:%M:%S %p')
        # Convert to 24-hour time
        total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        
        # Adjust for PM times (12 PM to 11:59 PM)
        if time_str.endswith('PM') and time_obj.hour != 12:
            total_seconds += 12 * 3600  # Add 12 hours for PM times
        
        # Handle the special case for 12 AM (midnight)
        if time_str.endswith('AM') and time_obj.hour == 12:
            total_seconds -= 12 * 3600  # Subtract 12 hours for midnight (12 AM)
            
    except ValueError:
        raise ValueError(f"Time format not recognized: {time_str}")
    
    return total_seconds


def seconds_to_time(seconds):
    return str(timedelta(seconds=seconds))

def encode_video(input_path, output_path):
    try:
        ffmpeg_path = get_ffmpeg_path()
        print(f"path to ffmpeg ------> {ffmpeg_path}")
        command = [
            ffmpeg_path,
            '-y',
            '-i', input_path,
            '-c:v', 'libx265',
            '-crf', '23', 
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", "Failed to encode video with ffmpeg.")



def trim_video(file_path, start_time, end_time, initial_time_str):
    start_time_sec = time_to_seconds(start_time)
    end_time_sec = time_to_seconds(end_time)
    initial_time_sec = time_to_seconds(initial_time_str)
    
    start_time_sec -= initial_time_sec
    end_time_sec -= initial_time_sec
    
    if start_time_sec >= end_time_sec:
        messagebox.showerror("Time Error", "Start time must be before end time.")
        return None

    # Output directory in a safe location
    output_dir = os.path.join(os.getenv('USERPROFILE'), "Documents", "trimmed_videos")
    os.makedirs(output_dir, exist_ok=True)  

    
    trimmed_file = os.path.join(output_dir, os.path.basename(file_path).replace('.mp4', '_trimmed.mp4'))
    print(f"Trimmed video path: {trimmed_file}")

    # Get the FFmpeg path
    ffmpeg_path = get_ffmpeg_path()

    trim_command = [
        ffmpeg_path,
        '-y',
        '-i', file_path,
        '-ss', str(start_time_sec),
        '-to', str(end_time_sec),
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'ultrafast',
        '-c:a', 'aac',
        '-strict', 'experimental',
        trimmed_file
    ]

    print(f"Running command: {' '.join(trim_command)}")

    try:
        result = subprocess.run(trim_command, check=True, capture_output=True, text=True)
        print("FFmpeg output:", result.stdout)
        print("FFmpeg error (if any):", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with error: {e.stderr}")
        messagebox.showerror("Error", "Failed to trim video.")
        return None
    except PermissionError as e:
        print(f"PermissionError: {str(e)}")
        messagebox.showerror("Permission Denied", "You do not have the required permissions to execute this operation.")
        return None

    return trimmed_file

class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XOW-POC")
        
        self.capture = None
        self.video_path = None
        self.initial_time_str = "00:00:00"
        self.end_time_str = "00:00:00"
        self.video_ended_displayed=False 
        self.tree = None
    

        self.setup_gui()

    def setup_gui(self):  

        # Set up grid layout
        # root.grid_rowconfigure(0, weight=1)
        # root.grid_columnconfigure(0, weight=0)  # Container 1 width depends on its content
        # root.grid_columnconfigure(1, weight=1)  # Container 2 will expand to fill the remaining space
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()
        # Left container
        self.left_container = tk.Frame(root,bg="grey",highlightbackground="black",highlightthickness=1)  # Fixed width
        self.left_container.pack(side=tk.LEFT,fill=tk.Y)  # Sticky to vertical axis

        # left_label container
        self.lable_frame=tk.Frame(self.left_container,bg="grey")
        self.lable_frame.pack(side=tk.TOP,pady=(0, 10))
        
        # left Button video & upload
        self.button_container=tk.Frame(self.left_container,bg="grey")
        self.button_container.pack(side=tk.TOP,pady=(0, 10))

        # left Search button 
        self.search_container=tk.Frame(self.left_container,bg="grey")
        self.search_container.pack(side=tk.TOP,pady=(0, 10))

        # left trim container
        self.trim_container=tk.Frame(self.left_container,bg="grey")
        self.trim_container.pack(side=tk.TOP,pady=(0, 10))

        # Right container 
        self.right_container=tk.Frame(root,bg="white",highlightbackground="black",highlightthickness=1)
        self.right_container.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)  

        # right_video container
        self.canvas = tk.Canvas(self.right_container, width=600, height=550,bg="white")
        self.canvas.pack(side=tk.TOP,fill=tk.X)  # Expand to fill available space

        # right slider container 
        self.slider_container=tk.Frame(self.right_container,bg="white")
        self.slider_container.pack(side=tk.TOP,fill=tk.BOTH)
        

        # right button container
        self.r_button_container=tk.Frame(self.right_container,bg="white")
        self.r_button_container.pack(side=tk.TOP)

        # right jump_container
        self.jump_container=tk.Frame(self.right_container,bg="white")
        self.jump_container.pack(side=tk.TOP)

        # right search table
        self.table_container=tk.Frame(self.right_container,bg="white")
        self.table_container.pack(side=tk.TOP,fill=tk.BOTH)
        

        # label
        self.label = tk.Label(self.lable_frame, text="Upload a video file to extract timestamp.",bg="grey")
        self.label.pack(side=tk.TOP)

        # Select Video Button
        self.select_video_button = customtkinter.CTkButton(self.button_container, text="Upload Video", command=self.select_video)
        self.select_video_button.pack(side=tk.LEFT,pady=5,padx=5)

        # Upload CSV/Excel Button
        self.upload_button = customtkinter.CTkButton(self.button_container, text="Upload File", command=self.upload_file)
        self.upload_button.pack(side=tk.LEFT,pady=5,padx=5)

        # Setup Excel input widgets
        self.column_entry = tk.Entry(self.search_container)   
        self.column_entry.pack(side=tk.TOP,pady=(0, 10))
        self.column_entry.insert(0, "Enter Fields :")  # Example default value
        self.column_entry.config(fg='gray')  # Set the text color to gray
        self.column_entry.bind("<KeyRelease>", self.update_column_suggestions)
        self.column_listbox = tk.Listbox(self.search_container)
        self.column_listbox.pack(side=tk.TOP,pady=(0, 10))
        self.column_listbox.bind("<<ListboxSelect>>", self.select_column)

        # Setup Excel or CSV input attributes
        self.value_entry = tk.Entry(self.search_container)
        self.value_entry.pack(side=tk.TOP,pady=(0, 10))
        self.value_entry.insert(0, "Enter value :")  # Example default value
        self.value_entry.config(fg='gray')  # Set the text color to gray
        self.value_listbox = tk.Listbox(self.search_container)
        self.value_listbox.pack(side=tk.TOP,pady=(0, 10))
        self.value_listbox.bind("<<ListboxSelect>>", self.select_value)

        # Bind the update_value_suggestions method to the value entry box
        self.value_entry.bind("<KeyRelease>", self.update_value_suggestions)
        self.value_entry.bind("<KeyRelease>", self.update_val_suggestions)

        # search button
        self.date_time_text = tk.Text(self.search_container, height=10, width=50)
        self.search_button = customtkinter.CTkButton(self.search_container, text="Search",font=("Helvetica", 13, "bold"), command=self.search_value, fg_color="#4681f4", hover_color="#4681f4")
        self.search_button.pack(side=tk.TOP,pady=(0, 10))

        # Bind events for search entries
        # self.value_entry.bind("<KeyRelease>", self.update_value_suggestions)
        self.column_entry.bind('<FocusIn>',self.on_entry_click)
        self.column_entry.bind('<FocusOut>',self. on_focusout) 
        self.value_entry.bind('<FocusIn>',self.on_entry_click_val)
        self.value_entry.bind('<FocusOut>',self. on_focusout_val) 

        # Trim Entry Widgets
        self.start_label = tk.Label(self.trim_container, text="Trim", bg="grey")
        self.start_label.pack(side=tk.TOP,pady=(0, 10))

        self.start_entry = tk.Entry(self.trim_container)
        self.start_entry.insert(0, "Start Time :")
        self.start_entry.config(fg='gray')
        self.start_entry.pack(side=tk.TOP,pady=(0, 10))

        self.end_entry = tk.Entry(self.trim_container)
        self.end_entry.insert(0, "End Time :")
        self.end_entry.config(fg='gray')
        self.end_entry.pack(side=tk.TOP,pady=(0, 10))

        # Bind events for trimming entries
        self.start_entry.bind('<FocusIn>', self.on_trim_click)
        self.start_entry.bind('<FocusOut>', self.on_trim)
        self.end_entry.bind('<FocusIn>', self.on_trim_click_val)
        self.end_entry.bind('<FocusOut>', self.on_trim_val)

        # Trim Button
        self.trim_button = customtkinter.CTkButton(self.trim_container, text="Trim and Download Video", command=self.trim_and_download, fg_color="#008080")
        self.trim_button.pack(side=tk.TOP)

        # Video Progress Bar (Below video display)
        self.progress_value = tk.DoubleVar()
        self.progress_slider = tk.Scale(self.slider_container, variable=self.progress_value, from_=0, to=100, orient="horizontal",command=self.seek)
        self.progress_slider.pack(side=tk.TOP,fill=tk.BOTH)
        self.progress_slider.configure(state="disabled")

        self.slider_in_use = False


        # initial time display
        self.initial_time_label = tk.Label(self.r_button_container, text="Initial Time :", font=("Helvetica", 12),bg="white")
        self.initial_time_label.pack(side=tk.LEFT,pady=5,padx=10)

        # Skip Button backward
        self.skip_backward_button = customtkinter.CTkButton(self.r_button_container, text="Skip -5s", command=self.skip_backward)
        self.skip_backward_button.pack(side=tk.LEFT,pady=5,padx=10)

        # Create a Tkinter button to play/pause the video
        self.play_button = customtkinter.CTkButton(self.r_button_container, text="Play", command=self.play_video, fg_color="yellow", text_color="black", hover_color="yellow")
        self.play_button.pack(side=tk.LEFT,pady=5,padx=10)


        # end time display
        self.end_time_label = tk.Label(self.r_button_container, text="End Time :", font=("Helvetica", 12),bg="white")
        self.end_time_label.pack(side=tk.RIGHT,pady=5,padx=10)

        # skip button forward
        self.skip_forward_button = customtkinter.CTkButton(self.r_button_container, text="Skip +5s", command=self.skip_forward)
        self.skip_forward_button.pack(side=tk.RIGHT,pady=5,padx=10)

        # Jump Time Entry
        self.jump_time_entry = ttk.Entry(self.jump_container)
        self.jump_time_entry.pack(side=tk.LEFT,pady=10,padx=10)

        # Jump Time Button
        self.jump_time_button = customtkinter.CTkButton(self.jump_container, text="Jump Time", command=self.jump_to_time)
        self.jump_time_button.pack(side=tk.LEFT,pady=5,padx=10)

        # Frame for search table
        self.results_frame = tk.Frame(self.table_container)
        self.results_frame.pack()


       # Define VLC library path
        vlc_path = os.path.join(os.getcwd(), "VLC", "libvlc.dll")

        # Verify if VLC library exists and set environment variable
        if os.path.exists(vlc_path):
            print(f"VLC DLL found at: {vlc_path}")
            os.environ['PYTHON_VLC_LIB_PATH'] = vlc_path  # Set environment variable for VLC
        else:
            print("VLC DLL not found!")
            raise FileNotFoundError(f"Could not find VLC DLL at {vlc_path}")

        # Initialize VLC instance and player
        self.vlc_instance = vlc.Instance()  # Create VLC instance
        if self.vlc_instance is None:
            print("Failed to initialize VLC instance.")
            raise Exception("VLC instance initialization failed.")
        else:
            print("VLC instance initialized successfully.")
            self.player = self.vlc_instance.media_player_new()  # Create VLC media player



        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=0)
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(1, weight=0)


        # Start updating the progress bar
        self.update_progress()

        

    def on_trim_click(self, event):
        if self.start_entry.cget('fg') == 'gray':
            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, '')
            self.start_entry.config(fg='black')

    def on_trim(self, event):
        if self.start_entry.get() == '':
            self.start_entry.insert(0, "Start Time :")
            self.start_entry.config(fg='gray')

    def on_trim_click_val(self, event):
        if self.end_entry.cget('fg') == 'gray':
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, '')
            self.end_entry.config(fg='black')

    def on_trim_val(self, event):
        if self.end_entry.get() == '':
            self.end_entry.insert(0, "End Time :")
            self.end_entry.config(fg='gray')

    def trim_and_download(self):
        if not self.video_path:
            messagebox.showerror("Error", "No video selected.")
            return

        start_time = self.start_entry.get()
        end_time = self.end_entry.get()

        trimmed_file = trim_video(self.video_path, start_time, end_time, self.initial_time_str)
        if trimmed_file:
            messagebox.showinfo("Success", f"Trimmed video saved as {trimmed_file}")

    def update_time_entries(self, start_time, end_time):
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, start_time)
        self.start_entry.config(fg='black')

        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, end_time)
        self.end_entry.config(fg='black')
    
    
    def on_entry_click(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.column_entry.cget('fg') == 'gray':
            self.column_entry.delete(0, "end")  # delete all the text in the entry
            self.column_entry.insert(0, '')  # Insert blank for user input
            self.column_entry.config(fg='black')  # Set the text color to black

    def on_focusout(self,event):
        if self.column_entry.get() == '':
            self.column_entry.insert(0, "Enter Fields :")
            self.column_entry.config(fg='gray')

    def on_entry_click_val(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.value_entry.cget('fg') == 'gray':
            self.value_entry.delete(0, "end")  # delete all the text in the entry
            self.value_entry.insert(0, '')  # Insert blank for user input
            self.value_entry.config(fg='black')  # Set the text color to black

    def on_focusout_val(self,event):
        if self.value_entry.get() == '':
            self.value_entry.insert(0, "Enter value :")
            self.value_entry.config(fg='gray')
        
    
    # for trim entry        
    def on_trim_click(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.start_entry.cget('fg') == 'gray':
            self.start_entry.delete(0, "end")  # delete all the text in the entry
            self.start_entry.insert(0, '')  # Insert blank for user input
            self.start_entry.config(fg='black')  # Set the text color to black

    def on_trim(self,event):
        if self.start_entry.get() == '':
            self.start_entry.insert(0, "Start Time :")
            self.start_entry.config(fg='gray')

    def on_trim_click_val(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.end_entry.cget('fg') == 'gray':
            self.end_entry.delete(0, "end")  # delete all the text in the entry
            self.end_entry.insert(0, '')  # Insert blank for user input
            self.end_entry.config(fg='black')  # Set the text color to black

    def on_trim_val(self,event):
        if self.end_entry.get() == '':
            self.end_entry.insert(0, "End Time :")
            self.end_entry.config(fg='gray')
        

    def select_video(self):
        self.video_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 files", "*.mp4")])
        if self.video_path:
            self.initial_time_str = get_initial_time(self.video_path)
            self.end_time_str = get_video_end_time(self.video_path)
            self.capture = cv2.VideoCapture(self.video_path)  # Initialize capture object
            media = self.vlc_instance.media_new(self.video_path)
            self.player.set_media(media)
            self.player.set_hwnd(self.canvas.winfo_id())
            # self.play_video()
            self.extract_times()
        else:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            # self.play_video()


    def initialize_player(self):
        # Initialize your video player here
        # This is a placeholder; replace with actual initialization code
        class Player:
            def play(self):
                print("Video playing...")
            def pause(self):
                print("Video paused...")
        return Player()

    def play_video(self):
        print("Play button clicked")
        if self.video_path:
            self.player.play()
            # Use configure instead of config
            self.play_button.configure(text="Pause", command=self.pause_video)
            
    def pause_video(self):
        print("Pause button clicked")
        self.player.pause()
        # Use configure instead of config
        self.play_button.configure(text="Play", command=self.play_video)

        
    
    def jump_to_time(self):
        if self.capture is None:
            messagebox.showerror("Error", "No video selected.")
            return

        # Get jump time and calculate jump seconds
        jump_time_str = self.jump_time_entry.get()
        jump_seconds = time_to_seconds(jump_time_str)
        print("Hii ----> jump seconds:", jump_seconds)

        # Convert initial time to seconds
        initial_seconds = time_to_seconds(self.initial_time_str)
        
        # Debugging: check if jump and initial seconds are calculated correctly
        print(f"Jump Seconds: {jump_seconds}, Initial Seconds: {initial_seconds}")

        fps = self.capture.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            messagebox.showerror("Error", "Failed to get video frame rate.")
            return

        # Calculate target seconds
        target_seconds = max(0, jump_seconds - initial_seconds)

        # Debug prints to identify issues
        print(f"Jump Time: {jump_time_str}")
        print(f"Initial Time: {self.initial_time_str}")
        print(f"Target Seconds: {target_seconds}")

        # Get total frames and duration
        total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration_seconds = total_frames / fps

        # Ensure target seconds don't exceed total duration
        if target_seconds > total_duration_seconds:
            target_seconds = total_duration_seconds

        # Calculate frame position
        frame_position = int(target_seconds * fps)

        if frame_position >= total_frames:
            frame_position = total_frames - 1
        elif frame_position < 0:
            frame_position = 0

        # Debugging information for better tracking
        print(f"Total Duration: {total_duration_seconds}")
        print(f"Frame Position: {frame_position}")

        # Set the frame to the correct position
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = self.capture.read()
        if ret:
            timestamp = extract_timestamp(frame)
            if timestamp:
                print(f"Timestamp: {timestamp}")
            else:
                print("No timestamp found.")
        else:
            print("Failed to read frame.")

        # Set the player time (in milliseconds for FFmpeg)
        self.player.set_time(int(target_seconds * 1000))



        
    def skip_forward(self):
            if self.capture is None:
                messagebox.showerror("Error", "No video selected.")
                return

            current_time = self.player.get_time() / 1000
            jump_seconds = 5
            new_time = current_time + jump_seconds
            self.player.set_time(int(new_time * 1000))
    
    def skip_backward(self):
        if self.capture is None:
            messagebox.showerror("Error", "No video selected.")
            return

        current_time = self.player.get_time() / 1000
        jump_seconds = 5
        new_time = max(current_time - jump_seconds, 0)
        self.player.set_time(int(new_time * 1000))


    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx; *.xls *.csv")])
        if not file_path:
            return

        try:
            if file_path.endswith('.xlsx'):
                self.excel_data = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xls'):
                self.excel_data = pd.read_excel(file_path, engine='xlrd')
            elif file_path.endswith('.csv'):
                self.excel_data = pd.read_csv(file_path, engine='python')
            else:
                raise ValueError("Unsupported file format. Please select a valid Excel file.")

            self.column_suggestions = list(self.excel_data.columns)
            self.value_suggestions = {
                col: self.excel_data[col].dropna().unique().tolist() for col in self.excel_data.columns
            }

            # Clear existing listbox items
            self.column_listbox.delete(0, tk.END)
            self.value_listbox.delete(0, tk.END)
            self.date_time_text.delete(1.0, tk.END)  # Clear text widget

            # Populate column_listbox with column names
            for column in self.column_suggestions:
                self.column_listbox.insert(tk.END, column)

            # Inform user that the file was uploaded successfully
            messagebox.showinfo("Success", "uploaded  file successfully. Select a column from the list.")

        except ValueError as ve:
            messagebox.showerror("Error", f"Failed to process the file: {ve}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read the Excel file: {str(e)}")


    def seek(self, value):
        if self.capture:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            frame_position = int(float(value) * fps)
            total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_position < 0:
                frame_position = 0
            elif frame_position >= total_frames:
                frame_position = total_frames - 1
            
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            self.play_video()         

    def search_value(self):
            column_name = self.column_entry.get()
            value = self.value_entry.get()

            if column_name in self.excel_data.columns:
                filtered_df = self.excel_data[self.excel_data[column_name] == value]

                # Create Treeview widget only when search button is clicked
                self.tree = ttk.Treeview(self.results_frame, columns=("QR CODE", "Name", "Company Name", "Phone", "Email", "DATE AND TIME"), show='headings')
                self.tree.heading("QR CODE", text="QR CODE")
                self.tree.heading("Name", text="Name")
                self.tree.heading("Company Name", text="Company Name")
                self.tree.heading("Phone", text="Phone")
                self.tree.heading("Email", text="Email")
                self.tree.heading("DATE AND TIME", text="DATE AND TIME")

                self.v_scroll = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)
                self.h_scroll = ttk.Scrollbar(self.results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)

                self.tree.grid(row=0, column=0, sticky="nsew",)
                self.v_scroll.grid(row=0, column=1, sticky="ns")
                self.h_scroll.grid(row=1, column=0, sticky="ew")
                self.tree.configure(yscrollcommand=self.v_scroll.set)

                self.tree.column("QR CODE", width=220)
                self.tree.column("Name", width=220)
                self.tree.column("Company Name", width=220)
                self.tree.column("Phone", width=220)
                self.tree.column("Email", width=220)
                self.tree.column("DATE AND TIME", width=220)

                style = ttk.Style()
                style.configure('Treeview', rowheight=18,highlightbackground="black",highlightthickness=2)
                style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
                style.configure("Treeview", font=("Arial", 11,"bold"))

                self.tree.bind("<<TreeviewSelect>>", self.on_item_selected)

                # Insert new rows
                for index, row in filtered_df.iterrows():
                    self.tree.insert("", tk.END, values=list(row))

                if filtered_df.empty:
                    messagebox.showinfo("No Results", "No matching results found.")
            else:
                messagebox.showerror("Error", "Column name not found in the Excel file.")         

    def update_column_suggestions(self, event):
        """Updates the column listbox based on the text in the column_entry."""
        search_text = self.column_entry.get().lower()
        self.column_listbox.delete(0, tk.END)
        
        if search_text:
            # Suggest columns based on the search text
            suggestions = [col for col in self.column_suggestions if search_text in col.lower()]
            for suggestion in suggestions:
                self.column_listbox.insert(tk.END, suggestion)

    def update_value_suggestions(self, event):
        """Updates the value listbox with all values based on the selected column or filters them based on user input."""
        # Get the selected column
        selected_column = self.column_entry.get()
        if selected_column and selected_column in self.value_suggestions:
            # Get the values for the selected column
            values = self.value_suggestions[selected_column]
            self.value_listbox.delete(0, tk.END)
            suggestions=values
            for suggestion in suggestions:
                    self.value_listbox.insert(tk.END, suggestion)

    def update_val_suggestions(self, event):
        """Updates the column listbox based on the text in the column_entry."""
        search_text = self.value_entry.get().lower()
        selected_column = self.column_entry.get()
        if selected_column and selected_column in self.value_suggestions:
            if search_text:
                    self.value_listbox.delete(0, tk.END)
                    values = self.value_suggestions[selected_column]
                    # Suggest columns based on the search text
                    suggestions = [val for val in values if search_text in str(val).lower()]
                    for suggestion in suggestions:
                        self.value_listbox.insert(tk.END, suggestion)

    def select_column(self, event):
        """Handles the selection of a column from the column listbox and updates value suggestions."""
        selection = self.column_listbox.curselection()
        if selection:
            column_name = self.column_listbox.get(selection[0])
            self.column_entry.delete(0, tk.END)
            self.column_entry.insert(0, column_name)
            
            # Immediately update the value suggestions based on the selected column
            self.update_value_suggestions(None)

    def select_value(self, event):
        """Handles the selection of a value from the value listbox."""
        selection = self.value_listbox.curselection()
        if selection:
            value = self.value_listbox.get(selection[0])
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, value)
            
            # Update the start time based on selected value
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, value)
            
            # Set the end time to the video duration (example end time used)
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, self.end_time_str)

    def on_item_selected(self, event):
        """Handles selection of an item from the treeview."""
        selected_item = self.tree.selection()
        self.initial_time_str = get_initial_time(self.video_path)
        self.end_time_str = get_video_end_time(self.video_path)
        
        if selected_item:
            item_values = self.tree.item(selected_item)["values"]
            if len(item_values) >= 6:
                timestamp = item_values[5].strip()  # Ensure no extra spaces
                print(f"Selected Timestamp: '{timestamp}'")
                print(f"Initial Time: '{self.initial_time_str}', End Time: '{self.end_time_str}'")
                
                # Convert strings to datetime objects for comparison
                selected_time = parse_time(timestamp)
                initial_time = parse_time(self.initial_time_str)
                end_time = parse_time(self.end_time_str)
                
                if selected_time is None or initial_time is None or end_time is None:
                    print(f"Error parsing times.")
                    messagebox.showinfo("Error", "Could not parse time.")
                    return
                
                print(f"Parsed Selected Time: {selected_time}")
                print(f"Parsed Initial Time: {initial_time}")
                print(f"Parsed End Time: {end_time}")
                
                # Compare times and handle errors
                if selected_time > end_time:
                    messagebox.showinfo("Error", "Selected time exceeds the end time.")
                elif selected_time < initial_time:
                    messagebox.showinfo("Error", "Selected time is before the initial time.")
                else:
                    self.jump_time_entry.delete(0, tk.END)
                    self.jump_time_entry.insert(0, timestamp)
                    
                    # Jump to the selected time (call the jump function if implemented)
                    self.jump_to_time()
                    
                    # Update the start time and set end time
                    self.start_entry.delete(0, tk.END)
                    self.start_entry.insert(0, timestamp)
                    self.end_entry.delete(0, tk.END)
                    self.end_entry.insert(0, self.end_time_str)  # Use the actual end time of the video



    def extract_times(self):
        if self.video_path:
            self.initial_time_str = get_initial_time(self.video_path)
            self.end_time_str = get_video_end_time(self.video_path)
            
            self.initial_time_label.configure(text=f"Initial Time: {self.initial_time_str}")
            self.end_time_label.configure(text=f"End Time: {self.end_time_str}")
            self.update_progress()
            self.play_video()


    def update_progress(self):
            if self.player.is_playing() and not self.slider_in_use:  # Only update if slider is not being manually moved
                length = self.player.get_length() / 1000  # in seconds
                current_time = self.player.get_time() / 1000  # in seconds

                # Calculate progress as a percentage
                if length > 0:
                    progress = (current_time / length) * 100
                    self.progress_value.set(progress)  # Update the slider with the current progress

                # Check if the video has reached the end
                if current_time >= length:
                    self.player.pause()  # Optionally pause the video when it reaches the end
                    self.slider_in_use = False  # Ensure slider updates stop

                    # Display a success message when the video ends
                    if not hasattr(self, 'video_ended_displayed') or not self.video_ended_displayed:
                        messagebox.showinfo("Video Ended", "The video has ended successfully.")
                        self.video_ended_displayed = True  # Set a flag to indicate that the message has been shown
            self.root.after(100, self.update_progress)


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = VideoPlayerApp(root)
    root.mainloop()
