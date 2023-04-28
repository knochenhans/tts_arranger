# TTS Arranger

Library that simplifies arranging text items fragments with multiple speakers and processing them using coqui.ai TTS to write audio files. It also features helper classes for converting HTML (and thus EPUB files) into TTS projects, based of customizeable rules to read specific elements with different speakers, and define pauses after certain elements.

## Overview

### TTS project elements
* TTS_Item, TTS_Chapter, TTS_Project

### Writer Classes
* TTS_Simple_Writer: Simple single-file writer, works with lists of TTS_Items directly
* TTS_Writer: Designed for writing audiobooks with meta data and chapters, works on with TTS_Project

### Reader Classes
* TTS_Text_Reader: Reads and converts plain text into a TTS_Project instance 
* TTS_HTML_Reader: Reads and converts HTML content into a TTS_Project instance
* TTS_EPUB_Reader: Reads and converts an EPUB file into a TTS_Project instance
* TTS_SRT_Reader: Reads and converts an SRT subtitle file into a TTS_Project instance *[not working due to timing bug at this point]*

### Helper Classes
* TTS_Processor: Takes a TTS_Item, synthesizes and writes it to a file, also takes care of preprocessing the text input and post processing the audio output
* TTS_HTML_Converter: Parses HTML content into a TTS_Project (mainly used by TTS_HTML_Reader and TTS_EPUB_Reader)

## Examples

```python
from tts_arranger import (TTS_Chapter, TTS_Item, TTS_Project,
                          TTS_Simple_Writer, TTS_Writer)

# Simple example using Simple Writer (using a simple list of TTS items)

tts_items = []

preferred_speakers = ['p273', 'p330']

tts_items.append(TTS_Item('This is a test', 1))
tts_items.append(TTS_Item(length=2000))  # Insert pause
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 0, length=10000))

simple_writer = TTS_Simple_Writer(tts_items, preferred_speakers)
simple_writer.synthesize_and_write('/tmp/tts_arranger_example_output/test.mp3')

# English example using tts_models/en/vctk/vits (with multispeaker support)

items1 = []
items1.append(TTS_Item('This is a test:', 0))
items1.append(TTS_Item('This is another test:', 1))

items2 = []
items2.append(TTS_Item('Another test',  0))
items2.append(TTS_Item('This is getting boring!', 1))

chapter = []
chapter.append(TTS_Chapter(items1, 'Chapter 1'))
chapter.append(TTS_Chapter(items2, 'Chapter 2'))

project = TTS_Project(chapter, 'Project Title', 'Project Subtitle', author='Some Author')

# Add a cover image
project.add_image_from_url('https://coqui.ai/static/38a06ec53309f617be3eb3b8b9367abf/598c3/logo-wordmark.png')

writer = TTS_Writer(project, '/tmp/tts_arranger_example_output/', preferred_speakers=preferred_speakers)
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

project = TTS_Project(chapter, 'Projektname', 'Projekt-Untertitel', author='Ein Autor', lang_code='de')

writer = TTS_Writer(project, '/tmp/tts_arranger_example_output/', model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', output_format='mp3')
writer.synthesize_and_write(project.author + ' - ' + project.title, concat=False)
```