import os
import random
import sys
from typing import Sequence, Mapping, Any, Union
import torch
import argparse


def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Recursively call the function with the parent directory
    return find_path(name, parent_directory)


def add_comfyui_directory_to_sys_path() -> None:
    """
    Add 'ComfyUI' to the sys.path
    """
    comfyui_path = find_path("ComfyUI")
    if comfyui_path is not None and os.path.isdir(comfyui_path):
        sys.path.append(comfyui_path)
        print(f"'{comfyui_path}' added to sys.path")


def add_extra_model_paths() -> None:
    """
    Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
    """
    try:
        from main import load_extra_path_config
    except ImportError:
        print(
            "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
        )
        from utils.extra_config import load_extra_path_config

    extra_model_paths = find_path("extra_model_paths.yaml")

    if extra_model_paths is not None:
        load_extra_path_config(extra_model_paths)
    else:
        print("Could not find the extra_model_paths config file.")


add_comfyui_directory_to_sys_path()
add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    import asyncio
    import execution
    from nodes import init_extra_nodes
    import server

    # Creating a new event loop and setting it as the default loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Creating an instance of PromptServer with the loop
    server_instance = server.PromptServer(loop)
    execution.PromptQueue(server_instance)

    # Initializing custom nodes
    init_extra_nodes()


from nodes import NODE_CLASS_MAPPINGS


def main():
    parser = argparse.ArgumentParser(
        description="Run ComfyUI workflow for image-to-video."
    )
    parser.add_argument(
        "--input-image", type=str, required=True, help="Path to the input image."
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="ComfyUI",
        help="Prefix for the output file.",
    )
    args = parser.parse_args()

    import_custom_nodes()
    with torch.inference_mode():
        cliploader = NODE_CLASS_MAPPINGS["CLIPLoader"]()
        cliploader_38 = cliploader.load_clip(
            clip_name="umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            type="wan",
            device="default",
        )

        cliptextencode = NODE_CLASS_MAPPINGS["CLIPTextEncode"]()
        cliptextencode_6 = cliptextencode.encode(
            text="a cute anime girl with massive fennec ears and a big fluffy tail wearing a maid outfit turning around",
            clip=get_value_at_index(cliploader_38, 0),
        )

        cliptextencode_7 = cliptextencode.encode(
            text="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
            clip=get_value_at_index(cliploader_38, 0),
        )

        unetloader = NODE_CLASS_MAPPINGS["UNETLoader"]()
        unetloader_37 = unetloader.load_unet(
            unet_name="wan2.1_i2v_480p_14B_fp16.safetensors", weight_dtype="default"
        )

        vaeloader = NODE_CLASS_MAPPINGS["VAELoader"]()
        vaeloader_39 = vaeloader.load_vae(vae_name="wan_2.1_vae.safetensors")

        clipvisionloader = NODE_CLASS_MAPPINGS["CLIPVisionLoader"]()
        clipvisionloader_49 = clipvisionloader.load_clip(
            clip_name="clip_vision_h.safetensors"
        )

        loadimage = NODE_CLASS_MAPPINGS["LoadImage"]()
        loadimage_52 = loadimage.load_image(image=args.input_image)

        clipvisionencode = NODE_CLASS_MAPPINGS["CLIPVisionEncode"]()
        clipvisionencode_51 = clipvisionencode.encode(
            crop="none",
            clip_vision=get_value_at_index(clipvisionloader_49, 0),
            image=get_value_at_index(loadimage_52, 0),
        )

        wanimagetovideo = NODE_CLASS_MAPPINGS["WanImageToVideo"]()
        wanimagetovideo_50 = wanimagetovideo.encode(
            width=512,
            height=512,
            length=33,
            batch_size=1,
            positive=get_value_at_index(cliptextencode_6, 0),
            negative=get_value_at_index(cliptextencode_7, 0),
            vae=get_value_at_index(vaeloader_39, 0),
            clip_vision_output=get_value_at_index(clipvisionencode_51, 0),
            start_image=get_value_at_index(loadimage_52, 0),
        )

        modelsamplingsd3 = NODE_CLASS_MAPPINGS["ModelSamplingSD3"]()
        ksampler = NODE_CLASS_MAPPINGS["KSampler"]()
        vaedecode = NODE_CLASS_MAPPINGS["VAEDecode"]()
        saveanimatedwebp = NODE_CLASS_MAPPINGS["SaveAnimatedWEBP"]()

        for q in range(1):
            modelsamplingsd3_54 = modelsamplingsd3.patch(
                shift=8, model=get_value_at_index(unetloader_37, 0)
            )

            ksampler_3 = ksampler.sample(
                seed=random.randint(1, 2**64),
                steps=20,
                cfg=6,
                sampler_name="uni_pc",
                scheduler="simple",
                denoise=1,
                model=get_value_at_index(modelsamplingsd3_54, 0),
                positive=get_value_at_index(wanimagetovideo_50, 0),
                negative=get_value_at_index(wanimagetovideo_50, 1),
                latent_image=get_value_at_index(wanimagetovideo_50, 2),
            )

            vaedecode_8 = vaedecode.decode(
                samples=get_value_at_index(ksampler_3, 0),
                vae=get_value_at_index(vaeloader_39, 0),
            )

            saveanimatedwebp_28 = saveanimatedwebp.save_images(
                filename_prefix=args.output_prefix,
                fps=16,
                lossless=False,
                quality=90,
                method="default",
                images=get_value_at_index(vaedecode_8, 0),
            )


if __name__ == "__main__":
    main()
