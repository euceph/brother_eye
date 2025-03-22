# brother_eye

a lightweight, local voice assistant for the terminal.

## Overview

brother_eye is a voice assistant built with Textual, meant to run mostly locally on-device and to provide a quick user experience.

## Requirements
- Python 3.12 (specific version required)
- Ollama (installed with install script)
- 4GB+ RAM recommended
- Microphone for voice

### Features
- User speech to text recognition + wake word detection
- Configurable local language model processing via Ollama
- Intent recognition for common tasks, featuring custom NLTK mini-intent model
- Basic weather and time/date functions implemented

## Project Structure
```
brother_eye/
├── __init__.py
├── install.sh
├── main.py
├── prompt.txt
├── requirements.txt
├── run.bat
├── run.sh
├── setup.py
├── __services__
│   ├── __init__.py
│   ├── intents.py         # intent recognition
│   ├── model.py           # core Ollama AI model integration
│   ├── stt.py             # speech-to-text
│   ├── time.py            # time-related functions
│   ├── wake_word.py       # wake word detection
│   └── weather.py         # weather information
├── __ui__
│   ├── __init__.py
│   ├── app.py             # main application UI
│   ├── styles.tcss        # Textual CSS styles
│   └── widgets.py         # terminal UI components
└── __utils__
    ├── __init__.py
    └── helpers.py         # utility functions
```

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/euceph/brother_eye.git
   cd brother_eye
   ```

2. Make the install script executable:
   ```
   chmod +x install.sh
   ```

3. Run the installation script:
   ```
   ./install.sh
   ```

   This takes care of:
   - setting up a 3.12 venv
   - installing required dependencies
   - attempting an ollama install if not already on device
   - configuring settings

## Usage
After install:
- On Linux/macOS: 
  ```
  ./run.sh
  ```
- On Windows: 
  ```
  run.bat
  ```

### Commands
- `ctrl+w` - Listen for wake word
- `ctrl+l` - Start listening directly
- `ctrl+s` - Stop listening
- `ctrl+q` - Quit

## Customization
- Create a custom system prompt to specify rules for the assistant
- Add new features by creating modules in the `__services__` directory
- Modify UI elements in the `__ui__` directory

## Troubleshooting
- If speech recognition fails:
  - Check your microphone settings
  - Ensure you're in a quiet environment
  - Try adjusting the input volume

- If Ollama fails to install:
  - Install manually from https://ollama.com/download
  - Ensure you have the required system permissions
  - Check system compatibility

- If the UI doesn't render correctly:
  - Ensure your terminal supports modern terminal features
  - Try a different terminal emulator if necessary

## Contributing
Contributions are always welcome. Feel free to submit a pull request.
