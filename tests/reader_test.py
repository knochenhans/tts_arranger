import os
import tempfile
import urllib.request

from tts_arranger.items.element_optimizer import ElementOptimizer
from tts_arranger.items.tts_chapter import TTS_Chapter
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.tts_item import TTS_Item
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.tts_html_converter import (
    CHECKER_SIGNAL,
    Checker,
    CheckerItemProperties,
    ConditionClass,
    ConditionID,
    ConditionName,
)
from tts_arranger.tts_reader.tts_epub_reader import TTS_EPUB_Reader
from tts_arranger.tts_reader.tts_html_reader import TTS_HTML_Reader
from tts_arranger.tts_reader.tts_text_reader import TTS_Text_Reader


def test_text_reader1():
    text = "Hello, world!"

    reader = TTS_Text_Reader()
    reader.load_raw(text)

    items = reader.project.chapters[0].items

    assert items[0].elements[0].text == "Hello, world!"


def test_text_reader2():
    text = "Hello, world!\n\nThis is a test."

    reader = TTS_Text_Reader()
    reader.load_raw(text)

    items = reader.project.chapters[0].items

    assert items[0].elements[0].text == "Hello, world!"
    assert items[1].elements[0].text == "This is a test."


def test_html_reader1():
    html = '<body><html><p class="bla bla2">test1 <span class="x"><i>test2</i> <b>test3</b> test4</span></p></html></body>'

    checkers = [
        Checker(
            [ConditionName("p"), ConditionClass("bla")], CheckerItemProperties("1", 800)
        ),
        Checker([ConditionName("i")], CheckerItemProperties("2", 500)),
        Checker([ConditionName("b")], CheckerItemProperties("3", 1000)),
    ]

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    assert items[0].elements[0].text == "test1 "
    assert items[0].elements[1].text == "test2"
    assert items[0].elements[2].min_length == 500
    assert items[0].elements[3].text == " "
    assert items[0].elements[4].text == "test3"
    assert items[0].elements[5].min_length == 1000
    assert items[0].elements[6].text == " test4"


def test_html_reader2():
    html = '<body><html><sup class="endnote">1</sup>2</html></body>'

    checkers = [
        Checker(
            [ConditionName("sup"), ConditionClass("endnote")],
            None,
            CHECKER_SIGNAL.IGNORE,
        )
    ]

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))

    optimizer = ElementOptimizer()

    # project.optimize()
    items = project.chapters[0].items

    assert items[0].elements[0].text == "2"


def test_html_reader3():
    html = '<body id="itest" class="ctest"><html><p>1 <i>2</i> 3</p></html></body>'

    checkers = []

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))
    # project.optimize()
    items = project.chapters[0].items

    assert items[0].elements[0].text == "1 "
    assert items[0].elements[1].text == "2"
    assert items[0].elements[2].text == " 3"


def test_merge_items1():
    html = "<body><html><p>1<i>2</i>3</p><p>4</p><p>5</p></html></body>"

    checkers = [Checker([ConditionName("p")], CheckerItemProperties("0", 800))]

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.add_item(items[0])
    items = project.chapters[0].items
    item = items[0]
    item.optimize()

    assert item.elements[0].text == "123"
    assert item.elements[1].min_length == 800
    assert item.elements[2].text == "4"
    assert item.elements[3].min_length == 800
    assert item.elements[4].text == "5"
    assert item.elements[5].min_length == 800


def test_merge_items2a():
    html = """<p id="b">a <em>b</em></p>"""

    checkers = [Checker([ConditionID("b")], CheckerItemProperties("1", 800))]

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))
    items = project.chapters[0].items
    item = items[0]
    # item.optimize()

    assert item.elements[0].text == "a "
    assert item.elements[0].speaker_id == "1"
    assert item.elements[1].text == "b"
    assert item.elements[1].speaker_id == "1"


def test_merge_items2():
    html = """<div class="c"><p id="a">a <a href="">b</a>. c.</p><p id="b">a <em>b</em>, c — d <a href="">e</a> f — g.</p><p id="c">a <a href="">b</a> c. d. e.</p></div>"""

    checkers = [
        Checker([ConditionID("b")], CheckerItemProperties("1", 800)),
        Checker([ConditionName("p")], CheckerItemProperties("0", 800)),
    ]

    reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))
    # project.optimize()
    item = project.chapters[0].items[0]
    item.optimize()

    assert item.elements[0].text == "a b. c."
    assert item.elements[0].speaker_id == "0"
    assert item.elements[2].text == "a b, c — d e f — g."
    assert item.elements[2].speaker_id == "1"
    assert item.elements[4].text == "a b c. d. e."


def test_merge_items3():
    html = """<div style="text-align: justify;">Released 1992 for <b>Macintosh</b> <br></div>"""

    checkers = [Checker([ConditionName("br")], CheckerItemProperties("0", 800))]

    reader = TTS_HTML_Reader(custom_checkers=checkers)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))

    items = project.chapters[0].items
    item = items[0]
    item.optimize()

    assert items[0].elements[0].text == "Released 1992 for Macintosh "


def test_merge_items4():
    html = """<span>1</span><span>2</span>"""

    checkers = [Checker([ConditionName("span")], CheckerItemProperties())]

    reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))

    items = project.chapters[0].items
    item = items[0]
    item.optimize()

    assert items[0].elements[0].text == "12"


def test_merge_items5():
    html = """<span>1</span><span>2</span>"""

    checkers = [Checker([ConditionName("span")], CheckerItemProperties())]

    reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))

    items = project.chapters[0].items
    item = items[0]
    item.optimize()

    assert item.elements[0].text == "12"


def test_nested_tags():
    html = """<blockquote><p>test</p></blockquote>"""

    checkers = [
        Checker([ConditionName("p")], CheckerItemProperties("0")),
        Checker([ConditionName("blockquote")], CheckerItemProperties("1")),
    ]

    reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
    reader.load_raw(html)

    items = reader.project.chapters[0].items

    project = TTS_Project()
    project.chapters.append(TTS_Chapter(items))

    items = project.chapters[0].items
    item = items[0]
    item.optimize()

    assert item.elements[0].text == "test"
    assert item.elements[0].speaker_id == "1"


def test_merge_items_pause():
    elements = [
        TTS_Element(min_length=1000),
        TTS_Element(min_length=1000),
        TTS_Element(min_length=1000),
    ]

    optimizer = ElementOptimizer.optimize(elements, 1500)

    assert optimizer[0].min_length == 1500


# def test_epub1():
#     preferred_speakers = ["p273", "p330"]

#     with tempfile.TemporaryDirectory() as temp_dir:
#         file_path = os.path.join(temp_dir, "epub_test.epub")

#         urllib.request.urlretrieve(
#             "https://epubtest.org/books/Fundamental-Accessibility-Tests-Basic-Functionality-v1.0.0.epub",
#             file_path,
#         )

#         checkers = [Checker([ConditionName("h1")], CheckerItemProperties(1, 800))]

#         reader = TTS_EPUB_Reader(custom_checkers=checkers)
#         reader.load(file_path)
#         reader.get_project().optimize()

#         items = reader.get_project().chapters[0].items

#         assert items[0].text == "Table of Contents"
#         assert items[0].speaker_idx == 1

#         items = reader.get_project().chapters[2].items

#         assert items[0].text == "Introduction"
#         assert items[0].speaker_idx == 1
#         assert (
#             items[4].text
#             == "This publication is currently considered [stable] by the DAISY Consortium and is in support of the efforts of the W3C EPUB 3 Community Group."
#         )
#         assert items[4].speaker_idx == 0
