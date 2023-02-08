# TTS Arranger

Simplifies arranging text fragments with multiple speakers and processing it with coqui.ai TTS.

# Example

```python
from tts_arranger import TTS_Arranger, TTS_Item

t = TTS_Arranger()
t.initialize()

tts_items = []

tts_items.append(TTS_Item('This is a test using speaker with name p330', 'p330'))
tts_items.append(TTS_Item('This is a test with another speaker and a minimum length', 'ED\n', length=10000))
tts_items.append(TTS_Item(length=2000)) # Insert pause

t.synthesize_and_write(tts_items, '/tmp/test2.mp3')
```