#!/usr/bin/python3
from tts_arranger.json_processor import JSON_Processor

json_processor = JSON_Processor("/tmp/test")
json_processor.synthesize_project("src/tts_arranger/data/test.json", "test")
