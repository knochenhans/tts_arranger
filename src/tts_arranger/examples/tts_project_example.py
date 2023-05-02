#!/usr/bin/python3
import os
from tts_arranger import TTS_Item, TTS_Chapter, TTS_Project, TTS_Writer

user_dir = os.path.expanduser('~')

preferred_speakers = ['p273', 'p330']

# Advanced example using a TTS Project object for creating an audiobook with chapters and a title image, uses tts_models/en/vctk/vits by (default)

items1 = []
items1.append(TTS_Item('This is a test', 0))
items1.append(TTS_Item('This is another test by a different speaker', 1))

items2 = []
items2.append(TTS_Item('Another test',  0))
items2.append(TTS_Item(length=1000))
items2.append(TTS_Item('This is getting boring!', 1))

# Prepare chapters with titles
chapter = []
chapter.append(TTS_Chapter(items1, 'Chapter 1'))
chapter.append(TTS_Chapter(items2, 'Chapter 2'))

# Prepare the project file
project = TTS_Project(chapter, 'Project title', 'This is a subtitle', author='Some author')
project.add_image_from_url('https://coqui.ai/static/38a06ec53309f617be3eb3b8b9367abf/598c3/logo-wordmark.png')  # Add a cover image

# Finally synthesize and write the project as a m4b audiobook using our preferred speakers
writer = TTS_Writer(project, os.path.join(user_dir, 'tts_arranger_example_output/'), preferred_speakers=preferred_speakers)
writer.synthesize_and_write(project.author + ' - ' + project.title)

# German example using Thorsten voice (no multispeaker support), output as mp3, writing one mp3 file per chapter

items1 = []
items1.append(TTS_Item('Dies ist ein Test.'))
items1.append(TTS_Item('Noch ein Test.'))

items2 = []
items2.append(TTS_Item('Ein weiterer Test'))
items2.append(TTS_Item('Langsam wird es langweilig!'))

chapter = []
chapter.append(TTS_Chapter(items1, 'Kapitel 1'))
chapter.append(TTS_Chapter(items2, 'Kapitel 2'))

project = TTS_Project(chapter, 'Projektname', 'Dies ist ein Untertitel', author='Ein Autor', lang_code='de')

writer = TTS_Writer(project, os.path.join(user_dir, 'tts_arranger_example_output/'),
                    model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', output_format='mp3')
writer.synthesize_and_write(project.author + ' - ' + project.title, concat=False)
