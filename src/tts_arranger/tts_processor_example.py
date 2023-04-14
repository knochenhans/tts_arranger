#!/usr/bin/python3
from tts_arranger import (TTS_Chapter, TTS_Item, TTS_Project,
                          TTS_Simple_Writer, TTS_Writer)

# Simple example using Simple Writer (using a simple list of TTS items)

tts_items = []

tts_items.append(TTS_Item('This is a test', 'p330'))
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 'p273', length=10000))
tts_items.append(TTS_Item(length=2000))  # Insert pause

simple_writer = TTS_Simple_Writer(tts_items)
simple_writer.synthesize_and_write('/tmp/tts_arranger_example_output/test.mp3')

# English example using tts_models/en/vctk/vits (with multispeaker support)

items1 = []
items1.append(TTS_Item('This is a test:', speaker_idx=0))
items1.append(TTS_Item('This is another test:',  speaker_idx=1))

items2 = []
items2.append(TTS_Item('Another test',  speaker_idx=0))
items2.append(TTS_Item('This is getting boring!',  speaker_idx=1))

chapter = []
chapter.append(TTS_Chapter(items1, 'Chapter 1'))
chapter.append(TTS_Chapter(items2, 'Chapter 2'))

project = TTS_Project(chapter, 'Project title', 'This is a subtitle', author='Some author')

# Add a cover image
project.add_image_from_url('https://coqui.ai/static/38a06ec53309f617be3eb3b8b9367abf/598c3/logo-wordmark.png')

writer = TTS_Writer(project, '/tmp/tts_arranger_example_output/')
writer.synthesize_and_write(project.author + ' - ' + project.title)

# German example using Thorsten voice (no multispeaker support)

items1 = []
items1.append(TTS_Item('Dies ist ein Test:', speaker_idx=0))
items1.append(TTS_Item('Noch ein Test:',  speaker_idx=1))

items2 = []
items2.append(TTS_Item('Ein weiterer Test',  speaker_idx=0))
items2.append(TTS_Item('Langsam wird es langweilig!',  speaker_idx=1))

chapter = []
chapter.append(TTS_Chapter(items1, 'Kapitel 1'))
chapter.append(TTS_Chapter(items2, 'Kapitel 2'))

project = TTS_Project(chapter, 'Projektname', 'Dies ist ein Untertitel', author='Ein Autor', lang_code='de')

writer = TTS_Writer(project, '/tmp/tts_arranger_example_output/', model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', output_format='mp3')
writer.synthesize_and_write(project.author + ' - ' + project.title, concat=False)
