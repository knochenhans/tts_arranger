import os
import tempfile
import urllib.request

# from src.tts_arranger.tts_html_converter_json import TTS_HTML_Converter_JSON
from src.tts_arranger.tts_reader.checker import (
    Checker,
    CheckerItemProperties,
    ConditionClass,
    ConditionName,
)


def test_html_reader1():
    html = '<body><html><p class="bla bla2">test1 <span class="x"><i>test2</i> <b>test3</b> test4</span></p></html></body>'

    checkers = [
        Checker(
            [ConditionName("p"), ConditionClass("bla")], CheckerItemProperties("1", 800)
        ),
        Checker([ConditionName("i")], CheckerItemProperties("2", 500)),
        Checker([ConditionName("b")], CheckerItemProperties("3", 1000)),
    ]

    # converter = TTS_HTML_Converter_JSON(custom_checkers=checkers)

    # converter.add_from_html(html)

    # items = converter.project["tts_chapters"][0]["tts_items"]

    # reader = TTS_HTML_Reader(custom_checkers=checkers)
    # reader.load_raw(html)

    # items = reader.project.tts_chapters[0].tts_items

    # assert items[0].speaker_idx == 1
    # assert items[0].text == "test1 "
    # assert items[1].text == "test2"
    # assert items[3].text == " "
    # assert items[4].text == "test3"
    # assert items[4].speaker_idx == 3
    # assert items[5].length == 1000
    # assert items[6].text == " test4"
