from tts_arranger.tts_preprocessor import TTS_Preprocessor
from tts_arranger.tts_reader.text_splitter import TextSplitter
from tts_arranger.functions import load_default_config
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.items.tts_item import TTS_Item


def test_uppercase_parts():
    text = "NASA is a space agency."

    preprocessor = TTS_Preprocessor()
    tts_item = TTS_Item([TTS_Element(text)])
    result = preprocessor.preprocess([tts_item], {})

    assert result[0].elements[0].text == "NASA is a space agency. "


def test_split_text1():
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


def test_split_text2():
    config = load_default_config()

    text = "In the US, this is called the 1948 Approach, and rightfully so?"

    text_splitter = TextSplitter(config.get("gemini_api", ""))
    result = text_splitter.split_text(text)

    assert len(result) == 5
    assert result[0].get("text") == "In the "
    assert result[0].get("type") == "text"

    assert result[1].get("text") == "US"
    assert result[1].get("type") == "acronym"

    assert result[2].get("text") == ", this is called the "
    assert result[2].get("type") == "text"

    assert result[3].get("text") == "1948"
    assert result[3].get("type") == "year"

    assert result[4].get("text") == " Approach, and rightfully so?"
    assert result[4].get("type") == "text"


def test_split_text3():
    config = load_default_config()

    text = "The year 2020 was unprecedented."

    text_splitter = TextSplitter(config.get("gemini_api", ""))
    result = text_splitter.split_text(text)

    assert len(result) == 3
    assert result[0].get("text") == "The year "
    assert result[0].get("type") == "text"
    assert result[1].get("text") == "2020"
    assert result[1].get("type") == "year"
    assert result[2].get("text") == " was unprecedented."
    assert result[2].get("type") == "text"


def test_split_text4():
    config = load_default_config()

    text = "In 1492, Columbus sailed the ocean blue."

    text_splitter = TextSplitter(config.get("gemini_api", ""))
    result = text_splitter.split_text(text)

    assert len(result) == 3
    assert result[0].get("text") == "In "
    assert result[0].get("type") == "text"
    assert result[1].get("text") == "1492"
    assert result[1].get("type") == "year"
    assert result[2].get("text") == ", Columbus sailed the ocean blue."
    assert result[2].get("type") == "text"
