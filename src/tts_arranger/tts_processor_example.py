from tts_arranger import TTS_Processor
from tts_arranger.items.tts_item import TTS_Item

t = TTS_Processor()
# t = TTS_Arranger(model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1')
t.initialize()

tts_items = []

tts_items.append(TTS_Item('This is a test', 'p330'))
tts_items.append(TTS_Item('This is a test with another speaker and a fixed minimum length', 'ED\n', length=10000))
tts_items.append(TTS_Item(length=2000))  # Insert pause

t.synthesize_and_write(tts_items, '/tmp/test2.mp3')
