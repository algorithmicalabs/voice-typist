# audio.py
import os
import queue
import threading
import sounddevice as sd
import soundfile as sf

import numpy as np

class AudioRecorder:
    def __init__(self, filename="temp_recording.wav", samplerate=16000, channels=1):
        self.filename = filename
        self.samplerate = samplerate
        self.channels = channels
        self.q = queue.Queue()
        self.recording = False
        self.thread = None
        self.current_volume = 0.0

    def _record_loop(self):
        try:
            # Open file in write mode ('w') which overwrites existing files
            with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as file:
                with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback):
                    while self.recording:
                        try:
                            # Read data from queue with a timeout so we check self.recording status regularly
                            data = self.q.get(timeout=0.1)
                            file.write(data)
                        except queue.Empty:
                            continue
        except Exception as e:
            print(f"Error during audio recording thread: {e}")
            self.recording = False

    def _callback(self, indata, frames, time, status):
        """This is called for each audio block by sounddevice."""
        if status:
            print(f"SoundDevice status warning: {status}")
        
        # Calculate peak amplitude as volume level (0.0 to 1.0 range)
        if indata.size > 0:
            self.current_volume = float(np.max(np.abs(indata)))
        else:
            self.current_volume = 0.0
            
        self.q.put(indata.copy())

    def get_volume(self):
        """Return the current peak audio level (0.0 to 1.0)."""
        if not self.recording:
            return 0.0
        return self.current_volume

    def start(self):
        """Start audio recording in a background thread."""
        if self.recording:
            return False
            
        # Ensure directory for filename exists
        dirname = os.path.dirname(self.filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
            
        self.recording = True
        self.q = queue.Queue()
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.daemon = True # Allow exit if main app exits
        self.thread.start()
        return True

    def stop(self):
        """Stop audio recording and return the filename of the saved file."""
        if not self.recording:
            return None
            
        self.recording = False
        if self.thread:
            self.thread.join(timeout=2.0) # wait up to 2 seconds for thread to finish writing
        
        # Verify the file exists and is not empty
        if os.path.exists(self.filename) and os.path.getsize(self.filename) > 44: # 44 bytes is minimum WAV header size
            return self.filename
        return None
