FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
RUN pip install --upgrade pip
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
RUN pip install qwen-tts gradio noisereduce platformdirs

# Copy app
COPY app.py .

# Set data directory for Docker (uses volume mount)
ENV QWEN_TTS_DATA_DIR=/app/data

# Create data directories
RUN mkdir -p /app/data/saved_voices /app/data/outputs

# Expose port
EXPOSE 8000

# Run app
CMD ["python3", "app.py"]
