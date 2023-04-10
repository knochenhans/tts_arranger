from tts_arranger import (TTS_Chapter, TTS_Item,  # type: ignore
                          TTS_Project)
from tts_arranger import TTS_Writer  # type: ignore

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

writer = TTS_Writer(project, '/tmp/test_m4b')
writer.synthesize_project(project.author + ' - ' + project.title)

# t = TTS_Arranger()
# t = TTS_Arranger(model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1')
# t.initialize()

# tts_items = []

# tts_items.append(TTS_Item('This is a test', 'p330'))
# tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length. This is a test with another speaker and a fixed minimum length. This is a test with another speaker and a fixed minimum length. This is a test with another speaker and a fixed minimum length. This is a test with another speaker and a fixed minimum length. This is a test with another speaker and a fixed minimum length.', 'ED\n', length=10000))
# tts_items.append(TTS_Item(length=2000)) # Insert pause

# t.synthesize_and_write(tts_items, '/tmp/test.mp3')
