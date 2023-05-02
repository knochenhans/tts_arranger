#!/usr/bin/python3
import os

from tts_arranger import TTS_Item, TTS_Simple_Writer

# Simple example using Simple Writer (using a simple list of TTS items), uses tts_models/en/vctk/vits by (default)

tts_items = []

user_dir = os.path.expanduser('~')

preferred_speakers = ['p273', 'p330']

tts_items.append(TTS_Item('This is a test', 0))  # Uses preferred speaker #0
tts_items.append(TTS_Item(length=2000))  # Insert pause
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 1, length=10000)) # Uses preferred speaker #1 and sets minimum length

# Create writer using our item list and prefered speakers and synthesize and save as mp3 audio
simple_writer = TTS_Simple_Writer(tts_items, preferred_speakers)
simple_writer.synthesize_and_write(os.path.join(user_dir, 'tts_arranger_example_output/test.mp3'))
