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