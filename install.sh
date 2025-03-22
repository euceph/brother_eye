#!/bin/bash
set -e

cat << "EOF"
                    |              |    |
                    |---.,---.,---.|--- |---.,---.,---.   ,---.,   .,---.
                    |   ||    |   ||    |   ||---'|       |---'|   ||---'
                    `---'`    `---'`---'`   '`---'`       `---'`---|`---'
                                                       ---     `---'
               Your personal terminal assistant - light, local, and listening
EOF

echo

# check platform
case "$(uname -s)" in
    Linux*)     platform=linux;;
    Darwin*)    platform=macos;;
    MINGW*|MSYS*|CYGWIN*) platform=windows;;
    *)          platform=unknown;;
esac

# windows installation path
if [ "$platform" = "windows" ]; then
    echo "detected windows system"

    # check for powershell
    if ! command -v powershell.exe &> /dev/null; then
        echo "powershell is required but not installed."
        exit 1
    fi

    # verify python 3.12
    python_version=$(powershell.exe -Command "try { python --version 2>&1 } catch { exit 1 }" | grep -oE "3\.12\.[0-9]+")
    if [ -z "$python_version" ]; then
        echo "python 3.12.x is required but not installed or not in path. please install python 3.12 specifically."
        exit 1
    fi

    echo "found python $python_version"

    # create virtual env
    echo "creating and activating virtual environment with python 3.12..."
    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi
    source .venv/Scripts/activate

    # install deps
    echo "installing python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # get spacy model
    echo "downloading spacy model..."
    python -m spacy download en_core_web_md

    # install package
    echo "installing brother eye in development mode..."
    pip install -e .

    # setup ollama
    echo "checking for ollama installation..."
    if ! command -v ollama &> /dev/null; then
        echo "ollama not found. installing ollama automatically..."

        # get installer
        echo "downloading ollama for windows..."
        powershell.exe -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/windows' -OutFile 'OllamaSetup.exe'"

        # run installer
        echo "installing ollama (this may open a new window)..."
        powershell.exe -Command "Start-Process -FilePath './OllamaSetup.exe' -Wait"

        # cleanup
        echo "cleaning up installation files..."
        powershell.exe -Command "Remove-Item -Path './OllamaSetup.exe' -Force"

        # verify install
        echo "verifying installation..."
        if ! powershell.exe -Command "Get-Command ollama" &> /dev/null; then
            echo "ollama installation may have failed. please install manually from https://ollama.com/download/windows"
            echo "after installing, run: ollama pull gemma3:1b"
            echo "then re-run this script."
            exit 1
        fi

        echo "ollama installed successfully!"
    fi

    # pull model
    echo "pulling gemma 3 1b model with ollama..."
    ollama pull gemma3:1b

    # create run.bat
    echo "creating run.bat script..."
    cat > run.bat << "EOL"
@echo off
call .venv\Scripts\activate
brother_eye %*
EOL

    echo "=== installation complete! ==="
    echo "to run brother eye, simply use:"
    echo ""
    echo "    run.bat"
    echo ""
    exit 0

# linux/macos path
else
    # verify python 3.12
    if ! command -v python3.12 &> /dev/null; then
        echo "python 3.12 is required but not installed. please install python 3.12 specifically."
        exit 1
    fi

    PYTHON_VERSION=$(python3.12 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -ne 12 ]; then
        echo "python 3.12 is required. you have $PYTHON_VERSION"
        exit 1
    fi

    echo "found python $PYTHON_VERSION"

    # setup venv
    if [ ! -d ".venv" ]; then
        echo "creating virtual environment with python 3.12..."
        python3.12 -m venv .venv
    fi

    # activate venv
    echo "activating virtual environment..."
    source .venv/bin/activate

    # install system deps
    echo "installing system dependencies..."

    # distro-specific installs
    if [ -f /etc/debian_version ]; then
        echo "detected debian/ubuntu system"
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-dev libespeak1
    elif [ -f /etc/redhat-release ]; then
        echo "detected red hat/fedora/centos system"
        sudo dnf install -y portaudio-devel python3-devel espeak
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "detected macos system"
        if ! command -v brew &> /dev/null; then
            echo "homebrew not found. installing..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install portaudio espeak
    fi

    # install python deps
    echo "installing python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # get spacy model
    echo "downloading spacy model..."
    python -m spacy download en_core_web_md

    # install package
    echo "installing brother eye in development mode..."
    pip install -e .

    # setup ollama
    echo "checking for ollama installation..."
    if ! command -v ollama &> /dev/null; then
        echo "ollama not found. installing ollama automatically..."

        # os-specific installs
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macos install
            echo "installing ollama for macos..."
            curl -fsSL https://ollama.com/install.sh | sh
        elif [ -f /etc/debian_version ] || [ -f /etc/ubuntu_version ]; then
            # debian/ubuntu
            echo "installing ollama for debian/ubuntu..."
            curl -fsSL https://ollama.com/install.sh | sh
        elif [ -f /etc/redhat-release ]; then
            # rhel/fedora/centos
            echo "installing ollama for rhel/fedora/centos..."
            curl -fsSL https://ollama.com/install.sh | sh
        else
            echo "unsupported os for automatic ollama installation."
            echo "please install ollama manually from https://ollama.com/download"
            echo "after installing, run: ollama pull gemma3:1b"
            echo "then re-run this script."
            exit 1
        fi

        # verify install
        if ! command -v ollama &> /dev/null; then
            echo "ollama installation failed. please install manually from https://ollama.com/download"
            echo "after installing, run: ollama pull gemma3:1b"
            echo "then re-run this script."
            exit 1
        fi

        echo "ollama installed successfully!"
    fi

    # pull model
    echo "pulling gemma 3 1b model with ollama..."
    ollama pull gemma3:1b

    echo "=== installation complete! ==="
    echo "to run brother eye, simply use:"
    echo ""
    echo "    ./run.sh"
    echo ""
    exit 0
fi