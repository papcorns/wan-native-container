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
        execute_native_wan_script(temp_image_path, output_prefix)

        output_files = glob.glob(os.path.join(COMFYUI_OUTPUT_DIR, f"{output_prefix}_*.webp"))
        if not output_files:
            logging.error("Generation failed. No output file found.")
            return f"Generation failed. No output file found.", 500
        
        output_file_path = output_files[0]
        output_filename = os.path.basename(output_file_path)

        bucket = storage_client.bucket(OUTPUT_BUCKET_NAME)
        blob = bucket.blob(output_filename)
        
        logging.info(f"Uploading {output_file_path} to gs://{OUTPUT_BUCKET_NAME}/{output_filename}")
        blob.upload_from_filename(output_file_path)
        
        # NOTE: blob.public_url requires the object to be publicly accessible.
        # A better practice for private objects is to return a signed URL.
        # For simplicity, we are assuming public access for now.
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
    finally:
        # Ensure cleanup runs even if errors occur
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        cleanup_directory(COMFYUI_OUTPUT_DIR)

def execute_native_wan_script(input_image_path, output_prefix):
    """
    Executes the NativeWanScript by correctly preparing the environment
    to resolve module name collisions between the Cloud Function and ComfyUI.
    """
    # Backup original state
    original_cwd = os.getcwd()
    original_argv = sys.argv
    
    # Temporarily hide our own 'main' module (the Cloud Function)
    # to allow ComfyUI's 'main.py' to be imported correctly.
    if 'main' in sys.modules:
        cloud_function_main_module = sys.modules.pop('main')
    else:
        cloud_function_main_module = None

    # Enter ComfyUI's environment
    os.chdir(COMFYUI_DIR)
    if COMFYUI_DIR not in sys.path:
        sys.path.insert(0, COMFYUI_DIR)

    try:
        # Clear argv to prevent ComfyUI's argparser from running on import
        sys.argv = ['']

        # Import the user's script. When it executes `from main import ...`,
        # Python's importer will now find and load /app/ComfyUI/main.py.
        import importlib.util
        script_path = os.path.join(COMFYUI_DIR, "NativeWanScript.py")
        spec = importlib.util.spec_from_file_location("NativeWanScript", script_path)
        native_wan_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native_wan_module)
        
        # Now, call the script's original main() function by injecting
        # our arguments into sys.argv, making the script think it was
        # called from the command line.
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

        # Clean up ComfyUI's main from the cache
        if 'main' in sys.modules:
            del sys.modules['main']

        # Restore our main Cloud Function module
        if cloud_function_main_module:
            sys.modules['main'] = cloud_function_main_module
