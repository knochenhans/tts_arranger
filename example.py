from tts_convert import TTS_Convert, TTS_Item, TTS_Item_Properties

t = TTS_Convert()
t.initialize()

# Get speakers from the list of default speakers
speaker_1 = TTS_Convert.default_speakers[0]
# speaker_1 = 'p273'
speaker_2 = TTS_Convert.default_speakers[1]

tts_items = []

p1 = TTS_Item_Properties(speaker_1)
p2 = TTS_Item_Properties(speaker_2)

tts_items.append(TTS_Item('This is a test', p1))
tts_items.append(TTS_Item('This is a test', p2))
tts_items.append(TTS_Item('This is a test', p2))
tts_items.append(TTS_Item('This is a test', p1))

t.synthesize_and_export(tts_items, '/tmp/test2.mp3')
