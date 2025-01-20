# ClearWave

Real-time audio noise reduction system built with Python, PyQt, and NumPy. ClearWave processes audio input in real-time to reduce background noise while preserving audio quality through FFT-based spectral processing and smooth crossfading.

## Features

- Real-time audio processing with minimal latency
- Adaptive noise reduction using spectral gating
- Smooth crossfading between audio buffers to prevent artifacts
- Multi-channel audio support
- Automatic audio device detection
- Qt-based threading for responsive performance
- Configurable noise reduction threshold
- Automatic output normalization to prevent clipping

## Requirements

- Python 3.7+
- PyQt5
- NumPy
- sounddevice

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/clearwave.git
cd clearwave
```

2. Install dependencies:
```bash
pip install PyQt5 numpy sounddevice
```

## Usage

Basic usage example:

```python
from clearwave import AudioProcessor
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
processor = AudioProcessor()

# Configure noise reduction (0.0 to 1.0, default 0.5)
processor.noise_reduction = 0.5

# Start processing
processor.start()

# Run the application
sys.exit(app.exec_())
```

## How It Works

ClearWave uses the following techniques to reduce noise:

1. **FFT Processing**: Converts audio to frequency domain for spectral analysis
2. **Adaptive Thresholding**: Automatically determines noise floor
3. **Spectral Gating**: Reduces frequencies below the noise threshold
4. **Smoothing**: Applies window-based smoothing to prevent harsh transitions
5. **Crossfading**: Implements buffer overlapping to ensure smooth audio output

## Configuration

Key parameters that can be adjusted:

- `noise_reduction`: Controls threshold sensitivity (0.0 to 1.0)
- `buffer_size`: Audio processing block size (default: 2048)
- `overlap`: Crossfade amount between buffers (default: 0.5)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FFT implementation powered by NumPy
- Audio I/O handled by sounddevice
- UI components built with PyQt5

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.
