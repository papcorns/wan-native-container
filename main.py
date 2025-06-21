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
    and calling its main() function with arguments, without modifying the script.
    """
    # Add ComfyUI directory to Python path for its internal imports
    sys.path.insert(0, COMFYUI_DIR)
    
    # The script and its dependencies assume the current working dir is ComfyUI
    original_cwd = os.getcwd()
    os.chdir(COMFYUI_DIR)
    
    # Backup original sys state that we are about to modify
    original_argv = sys.argv
    original_main_module = sys.modules.get('main')

    # Remove our own 'main' from modules to allow ComfyUI's main to be loaded
    if 'main' in sys.modules:
        del sys.modules['main']

    try:
        # Step 1: Pre-load ComfyUI's main.py. This is the critical fix.
        # NativeWanScript will try to `from main import ...`, and this ensures
        # it finds the right file and the `load_extra_path_config` function.
        import importlib.util
        comfy_main_path = os.path.join(COMFYUI_DIR, "main.py")
        main_spec = importlib.util.spec_from_file_location("main", comfy_main_path)
        comfy_main_module = importlib.util.module_from_spec(main_spec)
        main_spec.loader.exec_module(comfy_main_module)
        sys.modules['main'] = comfy_main_module

        # Step 2: Now that the environment is correct, import our target script
        script_path = os.path.join(COMFYUI_DIR, "NativeWanScript.py")
        spec = importlib.util.spec_from_file_location("NativeWanScript", script_path)
        native_wan_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native_wan_module)
        
        # Step 3: Call the script's original main() function, passing our
        # arguments by temporarily replacing sys.argv.
        logging.info("Injecting arguments and calling NativeWanScript.main()")
        sys.argv = [
            script_path,
            "--input-image", input_image_path,
            "--output-prefix", output_prefix
        ]
        native_wan_module.main()
        
    finally:
        # Step 4: Restore original state to not interfere with other processes
        os.chdir(original_cwd)
        sys.argv = original_argv
        if original_main_module:
            sys.modules['main'] = original_main_module
        elif 'main' in sys.modules:
            del sys.modules['main']
