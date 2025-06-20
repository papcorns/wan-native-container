# Use a PyTorch base image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set the working directory
WORKDIR /app

# Install git, wget, curl, and other dependencies
RUN apt-get update && apt-get install -y git wget curl && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
# This is useful if your application needs to interact with gcloud, but not strictly
# necessary if you use client libraries. Keeping it for flexibility.
RUN curl https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin

# Accept MODEL_BUCKET as a build argument
ARG MODEL_BUCKET
ENV MODEL_BUCKET=${MODEL_BUCKET}

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

# --- DEBUGGING STEPS ---
RUN echo "--- STARTING DEBUG ---"
RUN echo "MODEL_BUCKET is set to: $MODEL_BUCKET"
RUN gcloud auth list
RUN gsutil ls gs://$MODEL_BUCKET/
RUN echo "--- ENDING DEBUG ---"

# Copy model download script and execute it during build
COPY download_models.sh /app/ComfyUI/
RUN chmod +x download_models.sh && ./download_models.sh

# Copy the application source code
WORKDIR /app
COPY main.py .
COPY NativeWanScript.py /app/ComfyUI/
COPY requirements.txt .

# Install application-specific dependencies from the new requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint to run the Functions Framework server
# The server will automatically start and listen for HTTP requests on port 8080
# The target is the function name in main.py
ENTRYPOINT ["functions-framework", "--target=wan_video_endpoint", "--host=0.0.0.0", "--port=8080"] 