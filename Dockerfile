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

# Set the entrypoint to run the Functions Framework server
# The server will automatically start and listen for HTTP requests on port 8080
# The target is the function name in main.py
ENTRYPOINT ["functions-framework", "--target=wan_video_endpoint", "--host=0.0.0.0", "--port=8080"] 
