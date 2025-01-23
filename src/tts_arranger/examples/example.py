#!/usr/bin/python3
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.project_converter import ProjectConverterSSML
from tts_arranger.tts_processor import TTS_Processor

speaker_id_mapping = {
    "0": ["dt1"],
}


# Load project from JSON file
project = TTS_Project.from_json_file("/mnt/Daten/Datentausch/Redmi/Audiobooks/Renga in Blue/json/2025-01-14 00-30 - January 14, 2025 - Cornucopia The Long Departed.json")


