from tts_convert import TTS_Convert, TTS_Item

t = TTS_Convert()
# t = TTS_Convert(model='tts_models/de/thorsten/tacotron2-DDC', vocoder='vocoder_models/de/thorsten/hifigan_v1', multi=False)
t.initialize()

# # Get speakers from the list of default speakers
# speaker_1 = t.default_speakers[0]
# # speaker_1 = 'p273'
# speaker_2 = t.default_speakers[1]

tts_items = []

# tts_items.append(TTS_Item('Sie gelten als sanftmütig, verspielt, eigenwilliig. Sie sind Wohnungskatzen. Sie sind die ganze Zeit unter uns, doch haben sie immer noch Ihre Geheimnisse. Einen ganzen Tag lang wollen wir deshalb Shiro und Sora in ihrem gewohnten Habitat, der Stoschstraße, begleiten. Wir möchten verstehen, wie sie die Welt wahrnehmen. Was ist das Interessante am Küchenboden? Wieso schauen sie sich alles genau an, wenn wir Menschen uns nur hinhocken. Warum laufen sie uns immer vor die Füße? Welchen Sinn erfüllt es, Gummi zu fressen? Ist aufgeweichtes Trockenfutter leckerer als trockenes? Wie ist es wohl, sich am eigenem Hintern lecken zu können?', p1))
tts_items.append(TTS_Item('This is a test', 'p330'))
tts_items.append(TTS_Item('This is a test', 'ED\n', length=5000))
tts_items.append(TTS_Item(length=2000))
# tts_items.append(TTS_Item('This is a test', p2))
# tts_items.append(TTS_Item('This is a test', p1))

t.synthesize_and_export(tts_items, '/tmp/test2.mp3')
