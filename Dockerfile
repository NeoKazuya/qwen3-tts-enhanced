FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 and dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# Install pip for Python 3.12 using get-pip.py (avoids distutils issues)
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Install Python packages
RUN python3.12 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
RUN python3.12 -m pip install qwen-tts gradio noisereduce platformdirs matplotlib

# Copy app
COPY app.py .

# Set data directory for Docker (uses volume mount)
ENV QWEN_TTS_DATA_DIR=/app/data

# Create data directories
RUN mkdir -p /app/data/saved_voices /app/data/outputs

# Expose port
EXPOSE 8000

# Run app
CMD ["python3.12", "app.py"]
