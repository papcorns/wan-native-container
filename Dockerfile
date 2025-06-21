# Use a PyTorch base image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV APP_HOME /
ENV PYTHONUNBUFFERED TRUE

# Set the working directory
WORKDIR $APP_HOME

# Install git, wget, curl, and other dependencies
RUN apt-get update && apt-get install -y git wget curl && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt comfy-ui-requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install -r comfy-ui-requirements.txt 
RUN pip install functions-framework

# Copy the application source code
COPY papcorns-app.py ./

# Print debug information
RUN echo "----------ls -la CALISIYOR"

# List all files and folders for debugging
RUN ls -la 
# Set the entrypoint to run the Functions Framework server
CMD exec functions-framework --source=papcorns-app.py --target=wan_video_endpoint --debug
