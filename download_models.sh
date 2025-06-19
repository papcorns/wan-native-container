#!/bin/bash

# Model download script for WAN Video models
# Bu script modelleri Google Cloud Storage'dan indirir

set -e

# Google Cloud Storage bucket name (bu değeri kendi bucket'ınızla değiştirin)
BUCKET_NAME=${MODEL_BUCKET:-"wan-ai-models"}

echo "Starting model download from Google Cloud Storage..."

# Function to download file if it doesn't exist
download_if_not_exists() {
    local file_path=$1
    local gcs_path=$2
    
    if [ ! -f "$file_path" ]; then
        echo "Downloading $(basename $file_path)..."
        gsutil -m cp "$gcs_path" "$file_path"
        echo "✅ Downloaded $(basename $file_path)"
    else
        echo "⏭️  $(basename $file_path) already exists, skipping"
    fi
}

# Download models with parallel gsutil
echo "📥 Downloading diffusion model..."
download_if_not_exists \
    "./models/diffusion_models/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors" \
    "gs://${BUCKET_NAME}/diffusion_models/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors"

echo "📥 Downloading VAE model..."
download_if_not_exists \
    "./models/vae/Wan2_1_VAE_bf16.safetensors" \
    "gs://${BUCKET_NAME}/vae/Wan2_1_VAE_bf16.safetensors"

echo "📥 Downloading CLIP vision model..."
download_if_not_exists \
    "./models/clip_vision/clip_vision_h.safetensors" \
    "gs://${BUCKET_NAME}/clip_vision/clip_vision_h.safetensors"

echo "📥 Downloading text encoders..."
download_if_not_exists \
    "./models/text_encoders/umt5-xxl-enc-bf16.safetensors" \
    "gs://${BUCKET_NAME}/text_encoders/umt5-xxl-enc-bf16.safetensors"

download_if_not_exists \
    "./models/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors" \
    "gs://${BUCKET_NAME}/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors"

echo "📥 Downloading LoRA model..."
download_if_not_exists \
    "./models/loras/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors" \
    "gs://${BUCKET_NAME}/loras/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors"

echo "🎉 All models downloaded successfully!"
echo "Model sizes:"
du -sh models/*/ 