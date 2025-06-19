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
RUN mkdir -p models/diffusion_models && \
    mkdir -p models/vae && \
    mkdir -p models/clip_vision && \
    mkdir -p models/text_encoders && \
    mkdir -p models/loras

# Download the models
RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors -P ./models/diffusion_models/
RUN echo "Downloaded Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors"

RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -P ./models/vae/
RUN echo "Downloaded Wan2_1_VAE_bf16.safetensors"

RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -P ./models/clip_vision/
RUN echo "Downloaded clip_vision_h.safetensors"

RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -P ./models/text_encoders/
RUN echo "Downloaded umt5-xxl-enc-bf16.safetensors"

RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors -P ./models/text_encoders/
RUN echo "Downloaded umt5-xxl-enc-fp8_e4m3fn.safetensors"

RUN wget --header="Authorization: Bearer ${HF_TOKEN}" -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors -P ./models/loras/
RUN echo "Downloaded Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors"

# Copy the script into the ComfyUI directory
COPY NativeWanScript.py /app/ComfyUI/

# Set the entrypoint to run the script
WORKDIR /app/ComfyUI
ENTRYPOINT ["python", "NativeWanScript.py"] 