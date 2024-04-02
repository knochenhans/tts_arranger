# TTS Arranger

Library that simplifies arranging text items fragments with multiple speakers, and processing them using [Coqui.ai TTS](https://github.com/coqui-ai/TTS) to write audio files, including chapter markers and metadata. It also features helper classes for converting HTML (and thus EPUB files) into TTS projects, based of customizeable rules to read specific elements with different speakers, and define pauses after certain elements.

Install via pip: ``python -m pip install tts_arranger``

## Overview

### TTS project elements
* TTS_Item: basic building block containing text to synthesize, speaker index and length; is also used for pauses
* TTS_Chapter: contains a list if TTS_Item objects, represents a chapter in the output audio file
* TTS_Project: contains a list of chapters as well as metadata for the output file (like author, title, cover image)

### Writer Classes
* TTS_Simple_Writer: Simple single-file writer, works with lists of TTS_Items directly
* TTS_Writer: Designed for writing audiobooks with meta data and chapters, works with a TTS_Project object

### Reader Classes
* TTS_Text_Reader: Reads and converts plain text into a TTS_Project instance 
* TTS_HTML_Reader: Reads and converts HTML content into a TTS_Project instance
* TTS_EPUB_Reader: Reads and converts an EPUB file into a TTS_Project instance
* TTS_SRT_Reader: Reads and converts an SRT subtitle file into a TTS_Project instance *[not working due to timing bug at this point]*
* TTS_Docx_Reader: Reads and converts Microsoft  Word documents *[very early stage]*

### Helper Classes
* TTS_Processor: Takes a TTS_Item, synthesizes and writes it to a file, also takes care of preprocessing the text input and post processing the audio output
* TTS_HTML_Converter: Parses HTML content into a TTS_Project (mainly used by TTS_HTML_Reader and TTS_EPUB_Reader)

## Requirements
* ffmpeg, espeak-ng
* for required Python packages see requirements.txt

## Examples

```python
import os

from tts_arranger import TTS_Item, TTS_Simple_Writer

# Simple example using Simple Writer (using a simple list of TTS items), uses tts_models/en/vctk/vits by (default)

user_dir = os.path.expanduser('~')

tts_items = []

preferred_speakers = ['p273', 'p330']

tts_items.append(TTS_Item('This is a test', 0))  # Uses preferred speaker #0
tts_items.append(TTS_Item(length=2000))  # Insert pause
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 1, length=10000)) # Uses preferred speaker #1 and sets minimum length

# Create writer using our item list and prefered speakers and synthesize and save as mp3 audio
simple_writer = TTS_Simple_Writer(tts_items, preferred_speakers)
simple_writer.synthesize_and_write(os.path.join(user_dir, 'tts_arranger_example_output/test.mp3'))

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

writer = TTS_Writer(project, os.path.join(user_dir, 'tts_arranger_example_output/'), preferred_speakers=preferred_speakers)
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

writer = TTS_Writer(project, os.path.join(user_dir, 'tts_arranger_example_output/'), model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', output_format='mp3')
writer.synthesize_and_write(project.author + ' - ' + project.title, concat=False)
```

## Converting HTML-based content

You can use TTS_HTML_Reader and TTS_EPUB_Reader to convert HTML and EPUB files and raw code into a TTS project based on a list of customizable rules called _Checkers_ in this project. A Checker consists of a condition (for example `p` tags or tags with the class `class1`) and TTS item properties (speaker index and pause after the current segment) the created TTS item containing the tag’s text should have. A typical use case would be to read out headings with a different voice and insert a pause afterwards.

TTS_HTML_Reader internally uses the TTS_HTML_Converter class to parse the given HTML code, checks every tag it encounters against the list of checkers and creates TTS items accordingly.

TTS Arranger comes with a more or less sane default list of Checkers that will be applied when using TTS_HTML_Converter.

Checkers can also be loaded from JSON.

### Example

The following example converts HTML code into a TTS project and uses hard-coded checkers.

```python
import os

from tts_arranger import TTS_Writer
from tts_arranger.tts_html_converter import (Checker, CheckerItemProperties,
                                             ConditionClass, ConditionID,
                                             ConditionName)
from tts_arranger.tts_reader.tts_html_reader import TTS_HTML_Reader

user_dir = os.path.expanduser('~')

preferred_speakers = ['p273', 'p330']

html = '''<body><html>
            <h1>HTML Converter Example</h1>
            <p class="class1">This example shows how to read different parts of the text using different multispeaker voices.</p>
            <p id="id1">For example, this part uses our second speaker and is followed by a long pause.</p>
            <p>This part will fallback to using the default voice and pause properties.</p>
        </html></body>'''

checkers: list[Checker] = []

checkers.append(Checker([ConditionName('h1')], CheckerItemProperties(1, 1000)))  # Read headers with speaker 1 and followed with a 1000ms pause
checkers.append(Checker([ConditionName('p'), ConditionClass('class1')], CheckerItemProperties(0, 1500)))  # You can target paragraphs with specific classes
checkers.append(Checker([ConditionID('id1')], CheckerItemProperties(1, 500)))  # You can also target specific ids

reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)  # Initialize the HTML Reader with our custom checkers and ignore default checkers that shipped with the project
reader.load_raw(html, 'Project title', 'Some author')  # Load and convert the HTML code

project = reader.get_project()  # Get the finished project from the reader

# Finally synthesize and write the project as a m4b audiobook using our preferred speakers
writer = TTS_Writer(project, os.path.join(user_dir, 'tts_arranger_example_output/'), preferred_speakers=preferred_speakers)
writer.synthesize_and_write(project.author + ' - ' + project.title)
```

It’s also possible to load checkers from a JSON file. The corresponding JSON for the example above would look like this:

```JSON
{
    "check_entries": [
        {
            "conditions": [
                {
                    "name": "Name",
                    "arg": "h1"
                }
            ],
            "properties": {
                "speaker_idx": 1,
                "pause_after": 1000
            }
        },
        {
            "conditions": [
                {
                    "name": "Name",
                    "arg": "p"
                },
                {
                    "name": "Class",
                    "arg": "class1"
                }
            ],
            "properties": {
                "pause_after": 1500
            }
        },
        {
            "conditions": [
                {
                    "name": "ID",
                    "arg": "id1"
                }
            ],
            "properties": {
                "speaker_idx": 1,
                "pause_after": 500
            }
        }
    ]
}
```

This file can now be loaded using
```python
reader = TTS_HTML_Reader(custom_checkers_files=['path_to_your_json_file'], ignore_default_checkers=True)
```

It’s also possible to load multiple JSON files like this (the `custom_checkers_files` parameter takes a list of strings), and this can be combined with custom hard-coded checkers, and the defaults checkers. If checkers are loaded from all 3 sources, custom checkers have the highest priority, followed by the checker JSON files (in the order they were given), and finally the default checkers file. Thus, if a condition for the tag `p` is present in multiple checkers sources, the HTML converter will use the first one it finds.