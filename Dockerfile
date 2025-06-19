# Use a PyTorch base image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set the working directory
WORKDIR /app

# Install git and wget
RUN apt-get update && apt-get install -y git wget && rm -rf /var/lib/apt/lists/*

# Accept HF_TOKEN as build argument and set as environment variable
ARG HF_TOKEN

ENV HF_TOKEN=${HF_TOKEN}

# Clone ComfyUI repository
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Set ComfyUI as a subdirectory and install its dependencies
WORKDIR /app/ComfyUI
RUN pip install -r requirements.txt

# Download models
# Create directories for models
RUN mkdir -p models/clip && \
    mkdir -p models/unets && \
    mkdir -p models/vae && \
    mkdir -p models/clip_vision

# Download the models
RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -O models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors https://huggingface.co/i-lol-i/wan-i2v/resolve/main/umt5_xxl_fp8_e4m3fn_scaled.safetensors
echo "Downloaded umt5_xxl_fp8_e4m3fn_scaled.safetensors"
RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -O models/unets/wan2.1_i2v_480p_14B_fp16.safetensors https://huggingface.co/i-lol-i/wan-i2v/resolve/main/wan2.1_i2v_480p_14B_fp16.safetensors
echo "Downloaded wan2.1_i2v_480p_14B_fp16.safetensors"
RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -O models/vae/wan_2.1_vae.safetensors https://huggingface.co/i-lol-i/wan-i2v/resolve/main/wan_2.1_vae.safetensors
echo "Downloaded wan_2.1_vae.safetensors"
RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -O models/clip_vision/clip_vision_h.safetensors https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
echo "Downloaded clip_vision_h.safetensors"

# Copy the script into the ComfyUI directory
COPY NativeWanScript.py /app/ComfyUI/

# Set the entrypoint to run the script
WORKDIR /app/ComfyUI
ENTRYPOINT ["python", "NativeWanScript.py"] 