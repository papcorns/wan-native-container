import functions_framework
import subprocess
import os
import tempfile
import requests
import glob
from google.cloud import storage
import logging
from flask import jsonify

# Basic logging configuration
logging.basicConfig(level=logging.INFO)

# Configuration from environment variables
OUTPUT_BUCKET_NAME = os.environ.get("OUTPUT_BUCKET")
COMFYUI_OUTPUT_DIR = "/app/ComfyUI/output"
COMFYUI_DIR = "/app/ComfyUI"

# Initialize GCS client lazily
storage_client = None

def get_storage_client():
    """Get or create the Google Cloud Storage client."""
    global storage_client
    if storage_client is None:
        storage_client = storage.Client()
    return storage_client

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

def wan_video_function(request):
    """
    Handles the image-to-video generation.
    Expects a JSON payload with 'input_image_url'.
    The generated video is uploaded to a GCS bucket.
    """
    if not OUTPUT_BUCKET_NAME:
        logging.error("OUTPUT_BUCKET environment variable is not set.")
        return jsonify({"error": "OUTPUT_BUCKET environment variable is not set."}), 500

    request_json = request.get_json(silent=True)
    if not request_json or 'input_image_url' not in request_json:
        return jsonify({"error": "JSON payload with 'input_image_url' is required."}), 400

    input_image_url = request_json['input_image_url']
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir="/tmp") as temp_image:
            temp_image_path = temp_image.name
            with requests.get(input_image_url, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    temp_image.write(chunk)
        logging.info(f"Input image downloaded to: {temp_image_path}")

        cleanup_directory(COMFYUI_OUTPUT_DIR)

        output_prefix = "generated_video"
        command = [
            "python", "/app/NativeWanScript.py",
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

        output_files = glob.glob(os.path.join(COMFYUI_OUTPUT_DIR, f"{output_prefix}_*.webp"))
        if not output_files:
            logging.error("Generation failed. No output file found.")
            return jsonify({"error": f"Generation failed. No output file found. stderr: {process.stderr}"}), 500
        
        output_file_path = output_files[0]
        output_filename = os.path.basename(output_file_path)

        bucket = get_storage_client().bucket(OUTPUT_BUCKET_NAME)
        blob = bucket.blob(output_filename)
        
        logging.info(f"Uploading {output_file_path} to gs://{OUTPUT_BUCKET_NAME}/{output_filename}")
        blob.upload_from_filename(output_file_path)
        
        os.remove(temp_image_path)
        cleanup_directory(COMFYUI_OUTPUT_DIR)
        
        return jsonify({"output_video_url": blob.public_url})

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running script: {e.stderr}")
        if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return jsonify({"error": f"Error during video generation: {e.stderr}"}), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download input image: {e}")
        if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return jsonify({"error": f"Failed to download input image: {e}"}), 400
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return jsonify({"error": "An internal server error occurred."}), 500

@functions_framework.http
def wan_native_handler(request):
    """
    Main HTTP Cloud Function that routes requests.
    - GET /: Health check
    - POST /: Video generation
    """
    if request.method == 'GET' and request.path == '/':
        return jsonify({
            "status": "healthy",
            "message": "WAN Native Container is running",
            "version": "1.0.0"
        }), 200

    if request.method == 'POST' and request.path == '/':
        # For backwards compatibility, route POST on / to the video function
        return wan_video_function(request)

    # You can add more routes here based on request.path
    # For example:
    # if request.path == '/generate':
    #     return wan_video_function(request)
    
    return jsonify({"error": "Not Found"}), 404
