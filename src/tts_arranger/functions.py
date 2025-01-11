import json
import os
from typing import Any, Dict

from platformdirs import user_data_dir


def load_json_file(file_name: str) -> Dict[str, Any]:
    user_data_dir_: str = user_data_dir("tts_arranger")
    file_path = os.path.join(user_data_dir_, file_name)

    try:
        with open(file_path, "r") as file:
            data: Dict[str, Any] = json.load(file)
    except json.JSONDecodeError:
        raise ValueError(f"Error decoding JSON from file: {file_path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")

    return data


def load_default_voices() -> Dict[str, Dict[str, Any]]:
    voices = load_json_file("default_voices.json")

    # Update voice paths with absolute path
    user_data_dir_: str = user_data_dir("tts_arranger")
    for voice in voices.values():
        voice["ref_audio_path"] = os.path.join(
            user_data_dir_, "default_voices", voice["ref_audio_path"]
        )

    return voices


def load_default_config() -> Dict[str, Any]:
    return load_json_file("default_config.json")
