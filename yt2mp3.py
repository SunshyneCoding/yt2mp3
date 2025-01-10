import sys
import os
import re
import yt_dlp
import customtkinter as ctk
from moviepy.editor import AudioFileClip
import threading
from tkinter import messagebox
import time

class DeviceAuthPopup(ctk.CTkToplevel):
    def __init__(self, auth_url, device_code):
        super().__init__()
        self.title("Device Authentication Required")
        self.geometry("500x300")
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Instructions
        ctk.CTkLabel(self, text="Please follow these steps to authenticate:", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(self, text="1. Visit this URL in your browser:").pack(pady=5)
        
        # URL Entry (readonly)
        url_entry = ctk.CTkEntry(self, width=400)
        url_entry.pack(pady=5, padx=20)
        url_entry.insert(0, auth_url)
        url_entry.configure(state="readonly")
        
        ctk.CTkLabel(self, text="2. Enter this device code when prompted:").pack(pady=5)
        
        # Code Entry (readonly)
        code_entry = ctk.CTkEntry(self, width=200)
        code_entry.pack(pady=5)
        code_entry.insert(0, device_code)
        code_entry.configure(state="readonly")
        
        ctk.CTkLabel(self, text="3. Click 'Continue' after completing authentication").pack(pady=10)
        
        # Continue button
        ctk.CTkButton(self, text="Continue", command=self.destroy).pack(pady=10)

class YouTubeDownloader:
    def __init__(self):
        self.output_path = "downloads"
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def validate_url(self, url):
        # YouTube URL patterns
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([^?]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return True
        return False

    def download_and_convert(self, url, callback=None, progress_callback=None):
        try:
            if not self.validate_url(url):
                raise ValueError("Invalid YouTube URL. Please make sure you're using a valid YouTube video URL.")

            if callback:
                callback("Starting download...")

            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and 'downloaded_bytes' in d:
                        progress = (d['downloaded_bytes'] / d['total_bytes']) * 50
                        if progress_callback:
                            progress_callback(progress)
                    if callback and 'speed' in d:
                        speed = d['speed'] / 1024 if d['speed'] else 0  # KB/s
                        callback(f"Downloading... {speed:.1f} KB/s")

            ydl_opts = {
                'format': 'bestaudio/best',
                'progress_hooks': [progress_hook],
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                out_file = ydl.prepare_filename(info)

            if callback:
                callback("Converting to MP3...")

            # Convert to MP3
            base, _ = os.path.splitext(out_file)
            mp3_file = base + '.mp3'

            # If the downloaded file is already an MP3, just rename it
            if out_file.endswith('.mp3'):
                if os.path.exists(out_file):
                    os.rename(out_file, mp3_file)
            else:
                audio = AudioFileClip(out_file)
                duration = audio.duration
                
                # Update progress periodically during conversion
                def update_conversion_progress():
                    if progress_callback:
                        for i in range(51, 101):  # 50% to 100%
                            progress_callback(i)
                            time.sleep(duration/50)  # Spread updates across conversion time
                
                # Start progress updates in separate thread
                if progress_callback:
                    progress_thread = threading.Thread(target=update_conversion_progress, daemon=True)
                    progress_thread.start()
                
                audio.write_audiofile(mp3_file)
                audio.close()

                # Clean up the original file
                if os.path.exists(out_file):
                    os.remove(out_file)

            if callback:
                callback(f"Successfully downloaded: {os.path.basename(mp3_file)}")
            return mp3_file

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            if callback:
                callback(error_msg)
            else:
                print(error_msg)
            return None

class ConverterGUI:
    def __init__(self):
        self.downloader = YouTubeDownloader()
        
        self.window = ctk.CTk()
        self.window.title("YouTube to MP3 Converter")
        self.window.geometry("600x400")
        ctk.set_appearance_mode("dark")
        
        # URL Input
        self.url_frame = ctk.CTkFrame(self.window)
        self.url_frame.pack(pady=20, padx=20, fill="x")
        
        self.url_label = ctk.CTkLabel(self.url_frame, text="YouTube URL:")
        self.url_label.pack(side="left", padx=5)
        
        self.url_entry = ctk.CTkEntry(self.url_frame, width=400)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Progress Bar
        self.progress_frame = ctk.CTkFrame(self.window)
        self.progress_frame.pack(pady=10, padx=20, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=5)
        self.progress_bar.set(0)
        
        # Convert Button
        self.convert_btn = ctk.CTkButton(
            self.window,
            text="Convert to MP3",
            command=self.start_conversion
        )
        self.convert_btn.pack(pady=10)
        
        # Status Display
        self.status_text = ctk.CTkTextbox(self.window, height=200)
        self.status_text.pack(pady=10, padx=20, fill="both", expand=True)
        
    def update_status(self, message):
        self.status_text.insert("end", message + "\n")
        self.status_text.see("end")
        
    def update_progress(self, progress):
        self.progress_bar.set(progress / 100)
        self.window.update()
        
    def start_conversion(self):
        url = self.url_entry.get()
        if not url:
            self.update_status("Please enter a YouTube URL")
            return
            
        self.convert_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.update_status("Starting download and conversion...")
        
        def conversion_thread():
            self.downloader.download_and_convert(url, self.update_status, self.update_progress)
            self.convert_btn.configure(state="normal")
            self.progress_bar.set(1)  # Ensure progress bar shows complete
            
        threading.Thread(target=conversion_thread, daemon=True).start()
        
    def run(self):
        self.window.mainloop()

def main():
    if len(sys.argv) > 1:
        # CLI Mode
        url = sys.argv[1]
        downloader = YouTubeDownloader()
        result = downloader.download_and_convert(url)
        if result:
            print(f"Successfully converted! File saved as: {result}")
    else:
        # GUI Mode
        app = ConverterGUI()
        app.run()

if __name__ == "__main__":
    main()
