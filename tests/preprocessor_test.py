from tts_arranger.tts_preprocessor import TTS_Preprocessor
from tts_arranger.tts_reader.text_splitter import TextSplitter
from tts_arranger.functions import load_default_config


def test_uppercase_parts():
    text = "NASA is a space agency."

    preprocessor = TTS_Preprocessor()
    result = preprocessor.preprocess([{"text": text}], {})

    assert result[0]["text"] == "NASA is a space agency. "


def test_split_text():
    config = load_default_config()

    text = "But for better or for worse, after I was given a Commodore 64 for Christmas in 1984, model railroading fell by the wayside pretty quickly. (How’s that for a parable of the modern homo digitalis?)"

    text_splitter = TextSplitter(config.get("gemini_api", ""))
    result = text_splitter.split_text(text)

    assert len(result) == 3
    assert (
        result[0].get("text")
        == "But for better or for worse, after I was given a Commodore 64 for Christmas in "
    )
    assert result[0].get("type") == "text"
    assert result[1].get("text") == "1984"
    assert result[1].get("type") == "year"
    assert (
        result[2].get("text")
        == ", model railroading fell by the wayside pretty quickly. (How’s that for a parable of the modern homo digitalis?)"
    )
    assert result[2].get("type") == "text"
