# ComfyUI WAN Image-to-Video Container

This project provides a containerized version of a ComfyUI workflow that generates a video from an input image using the WAN Image-to-Video model.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system.
- For GPU acceleration, you need an NVIDIA GPU and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed.

## Setup

1.  **Create Input and Output Directories:**

    Create `input` and `output` directories in the root of the project.

    ```bash
    mkdir input
    mkdir output
    ```

2.  **Place Input Image:**

    Place your input image file (e.g., `my_image.png`) inside the `input` directory.

## Build the Docker Image

Build the Docker image using the provided `Dockerfile`. This process will take a significant amount of time as it downloads the base image, clones the ComfyUI repository, installs dependencies, and downloads several large model files.

```bash
docker build -t comfyui-wan-i2v .
```

## Run the Container

To run the container, you need to mount the `input` and `output` directories and provide the path to your input image.

```bash
docker run --gpus all \
  -v $(pwd)/input:/app/ComfyUI/input \
  -v $(pwd)/output:/app/ComfyUI/output \
  comfyui-wan-i2v \
  --input-image /app/ComfyUI/input/your_input_image.png \
  --output-prefix your_video_name
```

### Command Breakdown:

-   `--gpus all`: Enables GPU access for the container. Remove this if you are running on a CPU (not recommended as it will be extremely slow).
-   `-v $(pwd)/input:/app/ComfyUI/input`: Mounts your local `input` directory to `/app/ComfyUI/input` inside the container.
-   `-v $(pwd)/output:/app/ComfyUI/output`: Mounts your local `output` directory to `/app/ComfyUI/output` inside the container. The generated video will appear in your local `output` folder.
-   `comfyui-wan-i2v`: The name of the Docker image you built.
-   `--input-image /app/ComfyUI/input/your_input_image.png`: Specifies the path to your input image *inside the container*. **Remember to replace `your_input_image.png` with the actual filename of your image.**
-   `--output-prefix your_video_name`: Sets the prefix for the output video file. The final output will be something like `your_video_name_00001_.webp`.

After the container finishes execution, your generated video will be available in the `output` directory on your local machine. 

## Build with Google Cloud Build

This project includes a `cloudbuild.yaml` file to automatically build the Docker image and push it to Google Container Registry (GCR) using Google Cloud Build.

### Prerequisites

- You must have the [Cloud Build API enabled](https://console.cloud.google.com/flows/enableapi?apiid=cloudbuild.googleapis.com) in your Google Cloud project.
- The `gcloud` command-line tool must be [installed and configured](https://cloud.google.com/sdk/docs/install).

### Triggering a Build

You can trigger a manual build by running the following command from the project's root directory:


Alternatively, you can set up the HF_TOKEN in Google Cloud Build trigger settings as a substitution variable for automated builds. 

## WAN Video Native Container

Bu proje, WAN Video modellerini Google Cloud üzerinde çalıştırmak için optimize edilmiş bir container image'i sağlar.

## 🚀 Hızlı Kurulum (Google Cloud Storage ile)

### 1. Modelleri Google Cloud Storage'a Yükleyin

İlk olarak modelleri bir kez GCS'e yükleyin (bu işlem sadece bir kez yapılır):

```bash
# HuggingFace token'ınızla modelleri GCS'e yükleyin
chmod +x upload_models_to_gcs.sh
HF_TOKEN=your_huggingface_token ./upload_models_to_gcs.sh my-wan-models-bucket
```

### 2. Cloud Build Konfigürasyonunu Güncelleyin

`cloudbuild.yaml` dosyasında bucket ismini güncelleyin:

```yaml
substitutions:
  _MODEL_BUCKET: 'my-wan-models-bucket'  # Kendi bucket isminizi yazın
```

### 3. Container'ı Build Edin

```bash
gcloud builds submit --config cloudbuild.yaml .
```

## 🎯 Neden Bu Yaklaşım Daha Hızlı?

### Eski Yaklaşım (HuggingFace'den direkt indirme):
- ❌ Her build'de 15-30 dakika model indirme
- ❌ Network timeout riski
- ❌ HuggingFace API limitleri
- ❌ Yavaş uluslararası network

### Yeni Yaklaşım (Google Cloud Storage):
- ✅ 2-5 dakikada model indirme
- ✅ Google Cloud içinde yüksek hızlı network
- ✅ Paralel indirme (`gsutil -m`)
- ✅ Güvenilir ve stabil
- ✅ Modeller bir kez yüklendikten sonra tekrar kullanılabilir

## 📁 Dosya Yapısı

```
wan-native-container/
├── Dockerfile                   # Ana container tanımı
├── cloudbuild.yaml             # Google Cloud Build konfigürasyonu
├── download_models.sh          # Runtime'da GCS'den model indirme
├── upload_models_to_gcs.sh     # HF'den GCS'e model yükleme (tek seferlik)
├── NativeWanScript.py          # Ana uygulama
└── README.md                   # Bu dosya
```

## 🔧 Gelişmiş Kullanım

### Custom Bucket İsmi ile Build

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _MODEL_BUCKET=my-custom-bucket
```

### Local Test

```bash
# Önce modelleri GCS'e yükleyin
export MODEL_BUCKET=my-wan-models-bucket
docker build -t wan-video-local .
docker run --rm wan-video-local
```

## 🏎️ Performans Karşılaştırması

| Yöntem | Build Süresi | Network Hızı | Güvenilirlik |
|--------|-------------|--------------|--------------|
| HuggingFace Direct | 25-35 dakika | ~50 MB/s | Orta |
| Google Cloud Storage | 5-8 dakika | ~500 MB/s | Yüksek |

## 🔐 Güvenlik

- Modeller private GCS bucket'ında saklanır
- IAM ile erişim kontrolü
- Container runtime'da sadece gerekli modeller indirilir

## 🤝 Katkıda Bulunma

Bu repository'ye katkıda bulunmak için pull request gönderin!

## 📄 Lisans

MIT License - detaylar için `LICENSE` dosyasına bakın.
