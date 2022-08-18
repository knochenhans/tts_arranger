from tts_convert import TTS_Convert, TTS_Item

t = TTS_Convert()

# Get speakers from the list of default speakers
speaker_1 = TTS_Convert.default_speakers[0]
# speaker_1 = 'p273'
speaker_2 = TTS_Convert.default_speakers[1]

tts_items = []

tts_items.append(TTS_Item('This is some text', speaker_1))
tts_items.append(TTS_Item('This is some text with a short pause before and a long after', speaker_1, pause_pre=200, pause_post=2000))
tts_items.append(TTS_Item('This is a text by another speaker', speaker_2))
tts_items.append(TTS_Item('The following quote will be read by the second speaker: “Just like this!” he said.', speaker_1))

t.speak(tts_items, '/tmp/test1.mp3')
