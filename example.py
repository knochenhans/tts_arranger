from tts_convert import TTS_Convert, TTS_Item

t = TTS_Convert()
# t = TTS_Convert(model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', multi=False)
t.initialize()

tts_items = []

tts_items.append(TTS_Item('This is a test', 'p330'))
tts_items.append(TTS_Item('This is a test', 'ED\n', length=5000))
tts_items.append(TTS_Item(length=2000))

t.synthesize_and_export(tts_items, '/tmp/test2.mp3')
