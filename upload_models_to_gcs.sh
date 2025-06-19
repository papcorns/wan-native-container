#!/bin/bash

# Bu script modelleri HuggingFace'den indirip Google Cloud Storage'a yükler
# Bir kere çalıştırıldıktan sonra modeller GCS'de hazır olacak

set -e

# Konfigürasyon
BUCKET_NAME=${1:-"wan-ai-models"}
HF_TOKEN=${HF_TOKEN:-""}

if [ -z "$HF_TOKEN" ]; then
    echo "❌ HF_TOKEN environment variable gerekli!"
    echo "Usage: HF_TOKEN=your_token ./upload_models_to_gcs.sh your-bucket-name"
    exit 1
fi

echo "🚀 Starting model upload to Google Cloud Storage..."
echo "📦 Bucket: $BUCKET_NAME"

# Create local temp directory
TEMP_DIR="./temp_models"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Create model directories
mkdir -p diffusion_models vae clip_vision text_encoders loras

echo "📥 Downloading models from HuggingFace..."

# Download models using curl (macOS compatible)
echo "Downloading diffusion model..."
curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors \
    -o ./diffusion_models/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors

echo "Downloading VAE model..."
curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors \
    -o ./vae/Wan2_1_VAE_bf16.safetensors

echo "Downloading CLIP vision model..."
curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors \
    -o ./clip_vision/clip_vision_h.safetensors

echo "Downloading text encoders..."
curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors \
    -o ./text_encoders/umt5-xxl-enc-bf16.safetensors

curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors \
    -o ./text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors

echo "Downloading LoRA model..."
curl -L -H "Authorization: Bearer ${HF_TOKEN}" -C - \
    https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors \
    -o ./loras/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors

echo "📊 Model sizes:"
du -sh */

echo "☁️  Uploading to Google Cloud Storage..."

# Create bucket if it doesn't exist
gsutil mb -p $(gcloud config get-value project) gs://$BUCKET_NAME 2>/dev/null || echo "Bucket already exists or creation failed"

# Upload with parallel processing
gsutil -m cp -r . gs://$BUCKET_NAME/

echo "🎉 Upload complete!"
echo "📝 Don't forget to update cloudbuild.yaml with: _MODEL_BUCKET: '$BUCKET_NAME'"

# Cleanup
cd ..
rm -rf "$TEMP_DIR"

echo "✨ Models are now available at: gs://$BUCKET_NAME/" 