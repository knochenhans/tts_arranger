import json
import os
from typing import Any, Dict, Optional

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


def load_default_voices(
    lang: Optional[str] = None, backend: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    voices = load_json_file("default_voices.json")

    # Update voice paths with absolute path
    user_data_dir_: str = user_data_dir("tts_arranger")
    filtered_voices = {}
    for voice_name, voice in voices.items():
        if (lang is None or voice.get("lang") == lang) and (
            backend is None or voice.get("backend") == backend
        ):
            if "ref_audio_path" in voice:
                voice["ref_audio_path"] = os.path.join(
                    user_data_dir_, "default_voices", voice["ref_audio_path"]
                )
            filtered_voices[voice_name] = voice

    return filtered_voices


def load_default_config() -> Dict[str, Any]:
    return load_json_file("default_config.json")
