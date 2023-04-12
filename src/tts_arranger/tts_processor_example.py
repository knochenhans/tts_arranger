#!/usr/bin/python3
from tts_arranger import (TTS_Chapter, TTS_Item, TTS_Project,
                          TTS_Simple_Writer, TTS_Writer)

# Simple example using Simple Writer

tts_items = []

tts_items.append(TTS_Item('This is a test', 'p330'))
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 'ED\n', length=10000))
tts_items.append(TTS_Item(length=2000))  # Insert pause

simple_writer = TTS_Simple_Writer(tts_items)
simple_writer.synthesize_and_write('/tmp/tts_arranger_example_output/test2.mp3')

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

project = TTS_Project(chapter, 'Projektname', 'Dies ist ein Untertitel', author='Ein Autor')

writer = TTS_Writer(project, '/tmp/tts_arranger_example_output/', model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1')
writer.synthesize_and_write(project.author + ' - ' + project.title)
