# Use a PyTorch base image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set the working directory
WORKDIR /app

# Install git, wget, and Google Cloud SDK
RUN apt-get update && apt-get install -y git wget curl && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
RUN curl https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin

# Accept HF_TOKEN as build argument (kept for compatibility)
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

# Clone ComfyUI repository
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Set ComfyUI as a subdirectory and install its dependencies
WORKDIR /app/ComfyUI
RUN pip install -r requirements.txt

# Create directories for models
RUN mkdir -p models/diffusion_models && \
    mkdir -p models/vae && \
    mkdir -p models/clip_vision && \
    mkdir -p models/text_encoders && \
    mkdir -p models/loras

# Copy model download script
COPY download_models.sh /app/ComfyUI/
RUN chmod +x download_models.sh

# Copy the main script into the ComfyUI directory
COPY NativeWanScript.py /app/ComfyUI/

# Set the entrypoint to first download models then run the script
WORKDIR /app/ComfyUI
ENTRYPOINT ["sh", "-c", "./download_models.sh && python NativeWanScript.py"] 