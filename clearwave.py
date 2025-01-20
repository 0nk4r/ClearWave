import sys
import numpy as np
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QSlider, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from collections import deque

class AudioProcessor(QThread):
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.noise_reduction = 0.5
        self.output_device = None
        self.prev_buffer = None
        self.buffer_size = 2048
        self.overlap = 0.5
        
    def run(self):
        def callback(indata, outdata, frames, time, status):
            if status:
                print(status)
            
            try:
                # Ensure input data is 2D and correct type
                audio_data = indata.copy().astype(np.float32)
                if audio_data.ndim == 1:
                    audio_data = audio_data.reshape(-1, 1)
                
                # Initialize previous buffer if needed
                if self.prev_buffer is None:
                    self.prev_buffer = np.zeros_like(audio_data)
                
                # Process each channel separately
                for ch in range(audio_data.shape[1]):
                    channel_data = audio_data[:, ch]
                    
                    # Apply FFT
                    freq_data = np.fft.rfft(channel_data)
                    magnitudes = np.abs(freq_data)
                    
                    # Simple noise gate with smoothing
                    threshold = np.mean(magnitudes) * self.noise_reduction
                    mask = magnitudes > threshold
                    
                    # Use real-valued convolution for smoothing
                    smoothing_window = np.hanning(5)
                    smoothed_mask = np.convolve(
                        mask.astype(float), 
                        smoothing_window/smoothing_window.sum(), 
                        mode='same'
                    )
                    
                    # Apply mask and reconstruct
                    freq_data *= smoothed_mask
                    clean_audio = np.fft.irfft(freq_data)
                    
                    # Ensure correct length
                    if len(clean_audio) != len(channel_data):
                        clean_audio = clean_audio[:len(channel_data)]
                    
                    # Store back in audio_data
                    audio_data[:, ch] = clean_audio
                
                # Crossfade with previous buffer
                fade_len = int(len(audio_data) * self.overlap)
                fade_in = np.linspace(0, 1, fade_len)[:, np.newaxis]
                fade_out = np.linspace(1, 0, fade_len)[:, np.newaxis]
                
                # Apply crossfade
                audio_data[:fade_len] *= fade_in
                audio_data[:fade_len] += self.prev_buffer[-fade_len:] * fade_out
                
                # Store current buffer for next iteration
                self.prev_buffer = audio_data.copy()
                
                # Normalize output (prevent clipping)
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.9
                
                # Copy to output buffer
                outdata[:] = audio_data
                
            except Exception as e:
                print(f"Error in callback: {e}")
                outdata[:] = indata
            
            try:
                # Convert to float32
                audio_data = indata.astype(np.float32)
                
                # Initialize previous buffer if needed
                if self.prev_buffer is None:
                    self.prev_buffer = np.zeros_like(audio_data)
                
                # Apply simple noise reduction
                # Using a gentler approach to prevent audio breaks
                freq_data = np.fft.rfft(audio_data, axis=0)
                magnitudes = np.abs(freq_data)
                phases = np.angle(freq_data)
                
                # Simple noise gate with smoothing
                threshold = np.mean(magnitudes) * self.noise_reduction
                mask = magnitudes > threshold
                smoothed_mask = np.convolve(mask.astype(float), 
                                          np.hanning(5), 
                                          mode='same')
                
                # Apply mask and reconstruct
                freq_data_clean = freq_data * smoothed_mask[:, np.newaxis]
                clean_audio = np.fft.irfft(freq_data_clean, axis=0)
                
                # Crossfade with previous buffer
                fade_len = int(len(clean_audio) * self.overlap)
                fade_in = np.linspace(0, 1, fade_len)
                fade_out = np.linspace(1, 0, fade_len)
                
                # Apply crossfade
                clean_audio[:fade_len] *= fade_in[:, np.newaxis]
                clean_audio[:fade_len] += self.prev_buffer[-fade_len:] * fade_out[:, np.newaxis]
                
                # Store current buffer for next iteration
                self.prev_buffer = clean_audio.copy()
                
                # Normalize output
                if np.max(np.abs(clean_audio)) > 0:
                    clean_audio = clean_audio / np.max(np.abs(clean_audio)) * 0.9
                
                outdata[:] = clean_audio
                
            except Exception as e:
                print(f"Error in callback: {e}")
                outdata[:] = indata

        try:
            # Find Blackhole/Soundflower device
            devices = sd.query_devices()
            input_device = None
            
            for i, device in enumerate(devices):
                if 'BlackHole' in device['name'] or 'Soundflower' in device['name']:
                    input_device = i
                    break
            
            if input_device is None:
                raise ValueError("No BlackHole or Soundflower device found.")
            
            if self.output_device is None:
                raise ValueError("No output device selected.")
            
            # Get device info
            input_info = sd.query_devices(input_device)
            output_info = sd.query_devices(self.output_device)
            channels = min(input_info['max_input_channels'],
                         output_info['max_output_channels'])
            
            print(f"Using input device: {input_info['name']}")
            print(f"Using output device: {output_info['name']}")
            print(f"Channels: {channels}")

            # Using larger buffer size and explicit latency settings
            with sd.Stream(device=(input_device, self.output_device),
                         samplerate=48000,
                         channels=channels,
                         callback=callback,
                         blocksize=self.buffer_size,
                         latency=('low', 'low')):  # Request low latency
                print("Audio processing started")
                while self.running:
                    sd.sleep(100)

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.running = False

    def stop(self):
        self.running = False
        self.prev_buffer = None

class AudioDenoiser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Audio Denoiser")
        self.setMinimumSize(400, 300)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Instructions
        instructions = QLabel(
            "1. Install BlackHole or Soundflower\n"
            "2. Set system audio output to BlackHole/Soundflower\n"
            "3. Select your speakers/headphones as output device\n"
            "4. Adjust noise reduction strength\n"
            "5. Click Start to begin denoising"
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Output device selection
        output_label = QLabel("Select Output Device (Speakers/Headphones):")
        self.output_combo = QComboBox()
        self.populate_output_devices()
        layout.addWidget(output_label)
        layout.addWidget(self.output_combo)
        
        # Device info label
        self.device_info = QLabel()
        layout.addWidget(self.device_info)
        
        # Noise reduction slider
        noise_label = QLabel("Noise Reduction Strength:")
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setMinimum(0)
        self.noise_slider.setMaximum(100)
        self.noise_slider.setValue(30)  # Lower default value
        self.noise_slider.valueChanged.connect(self.update_noise_reduction)
        layout.addWidget(noise_label)
        layout.addWidget(self.noise_slider)
        
        # Start/Stop button
        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_processing)
        layout.addWidget(self.toggle_button)
        
        # Initialize audio processor
        self.audio_processor = AudioProcessor()
        self.audio_processor.error_occurred.connect(self.show_error)
        
        # Update device info when selection changes
        self.output_combo.currentIndexChanged.connect(self.update_device_info)
        self.update_device_info()
        
    def populate_output_devices(self):
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                self.output_combo.addItem(f"{device['name']}", i)
    
    def update_device_info(self):
        try:
            device_id = self.output_combo.currentData()
            if device_id is not None:
                device_info = sd.query_devices(device_id)
                self.device_info.setText(
                    f"Selected Output: {device_info['name']}\n"
                    f"Channels: {device_info['max_output_channels']}\n"
                    f"Sample Rate: {device_info['default_samplerate']}Hz"
                )
        except Exception as e:
            self.show_error(str(e))
    
    def update_noise_reduction(self, value):
        self.audio_processor.noise_reduction = value / 100.0
    
    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)
        self.toggle_button.setText("Start")
        self.audio_processor.running = False
    
    def toggle_processing(self):
        if not self.audio_processor.running:
            self.audio_processor.output_device = self.output_combo.currentData()
            self.audio_processor.running = True
            self.audio_processor.start()
            self.toggle_button.setText("Stop")
        else:
            self.audio_processor.stop()
            self.toggle_button.setText("Start")

def main():
    app = QApplication(sys.argv)
    window = AudioDenoiser()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
