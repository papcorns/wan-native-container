import functions_framework
import subprocess
import os
import tempfile
import requests
import glob
from google.cloud import storage
import logging

# Basic logging configuration
logging.basicConfig(level=logging.INFO)

# Configuration from environment variables
OUTPUT_BUCKET_NAME = os.environ.get("OUTPUT_BUCKET")
COMFYUI_OUTPUT_DIR = "/app/ComfyUI/output"
COMFYUI_DIR = "/app/ComfyUI"

# Initialize GCS client
storage_client = storage.Client()

def cleanup_directory(directory: str):
    """Removes all files in a directory."""
    logging.info(f"Cleaning up directory: {directory}")
    files = glob.glob(os.path.join(directory, "*"))
    for f in files:
        try:
            os.remove(f)
            logging.info(f"Removed {f}")
        except OSError as e:
            logging.error(f"Error removing file {f}: {e}")

@functions_framework.http
def wan_video_endpoint(request):
    """
    HTTP Cloud Function to trigger image-to-video generation.
    Expects a JSON payload with 'input_image_url'.
    The generated video is uploaded to a GCS bucket specified by OUTPUT_BUCKET env var.

    JSON Payload:
    {
        "input_image_url": "http://example.com/my-image.png"
    }

    Success Response:
    {
        "output_video_url": "https://storage.googleapis.com/your-bucket/generated_video.webp"
    }
    """
    if not OUTPUT_BUCKET_NAME:
        logging.error("OUTPUT_BUCKET environment variable is not set.")
        return "OUTPUT_BUCKET environment variable is not set.", 500

    request_json = request.get_json(silent=True)
    if not request_json or 'input_image_url' not in request_json:
        return "JSON payload with 'input_image_url' is required.", 400

    input_image_url = request_json['input_image_url']
    
    try:
        # Download the input image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir="/tmp") as temp_image:
            temp_image_path = temp_image.name
            with requests.get(input_image_url, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    temp_image.write(chunk)
        logging.info(f"Input image downloaded to: {temp_image_path}")

        # Clean previous output files before running
        cleanup_directory(COMFYUI_OUTPUT_DIR)

        # Run the generation script
        output_prefix = "generated_video"
        command = [
            "python", "NativeWanScript.py",
            "--input-image", temp_image_path,
            "--output-prefix", output_prefix
        ]

        logging.info(f"Running command: {' '.join(command)}")
        process = subprocess.run(
            command,
            cwd=COMFYUI_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        logging.info(f"Script stdout: {process.stdout}")
        if process.stderr:
            logging.warning(f"Script stderr: {process.stderr}")

        # Find the generated output file
        output_files = glob.glob(os.path.join(COMFYUI_OUTPUT_DIR, f"{output_prefix}_*.webp"))
        if not output_files:
            logging.error("Generation failed. No output file found.")
            return f"Generation failed. No output file found. stderr: {process.stderr}", 500
        
        output_file_path = output_files[0]
        output_filename = os.path.basename(output_file_path)

        # Upload the output file to Google Cloud Storage
        bucket = storage_client.bucket(OUTPUT_BUCKET_NAME)
        blob = bucket.blob(output_filename)
        
        logging.info(f"Uploading {output_file_path} to gs://{OUTPUT_BUCKET_NAME}/{output_filename}")
        blob.upload_from_filename(output_file_path)
        
        # Clean up local temporary files
        os.remove(temp_image_path)
        cleanup_directory(COMFYUI_OUTPUT_DIR)
        
        return {"output_video_url": blob.public_url}

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running script: {e.stderr}")
        return f"Error during video generation: {e.stderr}", 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download input image: {e}")
        return f"Failed to download input image: {e}", 400
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return "An internal server error occurred.", 500
