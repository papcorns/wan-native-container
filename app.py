import functions_framework
import subprocess
import os
import tempfile
import requests
import glob
from google.cloud import storage
import logging
import sys

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

def execute_native_wan_script(input_image_path, output_prefix):
    """
    Executes the NativeWanScript by preparing the environment and calling its main() function.
    """
    # Backup original state
    original_cwd = os.getcwd()
    original_argv = sys.argv
    
    # Enter ComfyUI's environment
    os.chdir(COMFYUI_DIR)
    if COMFYUI_DIR not in sys.path:
        sys.path.insert(0, COMFYUI_DIR)

    try:
        # Clear argv to prevent ComfyUI's argparser from running on import.
        # We only keep the program name itself.
        sys.argv = [original_argv[0]]

        # Import the user's script. When it executes `from main import ...`,
        # Python's importer will now find /app/ComfyUI/main.py because its
        # parent directory is in sys.path.
        import importlib.util
        script_path = os.path.join(COMFYUI_DIR, "NativeWanScript.py")
        spec = importlib.util.spec_from_file_location("NativeWanScript", script_path)
        native_wan_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native_wan_module)
        
        # Call the script's main() by injecting arguments into sys.argv.
        logging.info("Injecting arguments and calling NativeWanScript.main()")
        sys.argv = [
            script_path,
            "--input-image", input_image_path,
            "--output-prefix", output_prefix
        ]
        native_wan_module.main()

    finally:
        # Restore the original environment
        os.chdir(original_cwd)
        sys.argv = original_argv
        if COMFYUI_DIR in sys.path:
            sys.path.remove(COMFYUI_DIR)

        # Clean up ComfyUI's main from the cache to ensure a clean state
        # for the next function invocation in the same worker.
        if 'main' in sys.modules:
            del sys.modules['main']

@functions_framework.http
def wan_video_endpoint(request):
    """
    HTTP Cloud Function to trigger image-to-video generation.
    Expects a JSON payload with 'input_image_url'.
    The generated video is uploaded to a GCS bucket specified by OUTPUT_BUCKET env var.
    """
    if not OUTPUT_BUCKET_NAME:
        logging.error("OUTPUT_BUCKET environment variable is not set.")
        return "OUTPUT_BUCKET environment variable is not set.", 500

    request_json = request.get_json(silent=True)
    if not request_json or 'input_image_url' not in request_json:
        return "JSON payload with 'input_image_url' is required.", 400

    input_image_url = request_json['input_image_url']
    
    temp_image_path = None
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
        
        logging.info("Executing NativeWanScript workflow via import...")
        execute_native_wan_script(temp_image_path, output_prefix)

        output_files = glob.glob(os.path.join(COMFYUI_OUTPUT_DIR, f"{output_prefix}_*.webp"))
        if not output_files:
            logging.error("Generation failed. No output file found.")
            return "Generation failed. No output file found.", 500
        
        output_file_path = output_files[0]
        output_filename = os.path.basename(output_file_path)

        bucket = storage_client.bucket(OUTPUT_BUCKET_NAME)
        blob = bucket.blob(output_filename)
        
        logging.info(f"Uploading {output_file_path} to gs://{OUTPUT_BUCKET_NAME}/{output_filename}")
        blob.upload_from_filename(output_file_path)
        
        return {"output_video_url": blob.public_url}

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download input image: {e}")
        return f"Failed to download input image: {e}", 400
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return "An internal server error occurred.", 500
    finally:
        # Ensure cleanup runs even if errors occur
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        cleanup_directory(COMFYUI_OUTPUT_DIR) 