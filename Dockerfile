# Use a PyTorch base image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set the working directory
WORKDIR /app

# Install git, wget, curl, and other dependencies
RUN apt-get update && apt-get install -y git wget curl && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /app/requirements.txt
COPY comfy-ui-requirements.txt /app/comfy-ui-requirements.txt
RUN pip install -r requirements.txt
RUN pip install -r comfy-ui-requirements.txt 


# Copy the application source code
COPY main.py /app/main.py
COPY NativeWanScript.py /app/NativeWanScript.py

# Expose port 8080
EXPOSE 8080

RUN echo "pwd is $(pwd)"
RUN echo "ls is: \n$(ls)"

# Set the entrypoint to run the Functions Framework server
ENTRYPOINT functions-framework --target=wan_video_endpoint --source=main.py --host=0.0.0.0 --port=8080 
