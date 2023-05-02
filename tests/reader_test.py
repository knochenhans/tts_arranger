import os
import tempfile
import unittest
import urllib.request

from tts_arranger import TTS_Chapter, TTS_Item, TTS_Project
from tts_arranger.tts_html_converter import (CHECKER_SIGNAL, Checker,
                                             CheckerItemProperties,
                                             ConditionClass, ConditionID,
                                             ConditionName)
from tts_arranger.tts_reader.tts_epub_reader import TTS_EPUB_Reader
from tts_arranger.tts_reader.tts_html_reader import TTS_HTML_Reader


class TTS_HTML_ReaderTest(unittest.TestCase):
    def test1(self):
        html = '<body><html><p class="bla bla2">test1 <span class="x"><i>test2</i> <b>test3</b> test4</span></p></html></body>'

        checkers: list[Checker] = []

        checkers.append(Checker([ConditionName('p'), ConditionClass('bla')], CheckerItemProperties(1, 800)))
        checkers.append(Checker([ConditionName('i')], CheckerItemProperties(2, 500)))
        checkers.append(Checker([ConditionName('b')], CheckerItemProperties(3, 1000)))

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        self.assertEqual(items[0].speaker_idx, 1)
        self.assertEqual(items[0].text, 'test1 ')
        self.assertEqual(items[1].text, 'test2')
        self.assertEqual(items[3].text, ' ')
        self.assertEqual(items[4].text, 'test3')
        self.assertEqual(items[4].speaker_idx, 3)
        self.assertEqual(items[5].length, 1000)
        self.assertEqual(items[6].text, ' test4')

    def test2(self):
        html = '<body><html><sup class="endnote">1</sup>2</html></body>'

        checkers = []

        checkers.append(Checker([ConditionName('sup'), ConditionClass('endnote')], None, CHECKER_SIGNAL.IGNORE))

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, '2')

    def test3(self):
        html = '<body id="itest" class="ctest"><html><p>1 <i>2</i> 3</p></html></body>'

        checkers = []

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, '1 2 3')

    def test_merge_items1(self):

        html = '<body><html><p>1<i>2</i>3</p><p>4</p><p>5</p></html></body>'

        checkers = []

        checkers.append(Checker([ConditionName('p')], CheckerItemProperties(0, 800)))

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, '123')
        self.assertEqual(items[1].length, 800)
        self.assertEqual(items[2].text, '4')
        self.assertEqual(items[3].length, 800)
        self.assertEqual(items[4].text, '5')
        self.assertEqual(items[5].length, 800)

    def test_merge_items2a(self):
        html = """<p id="b">a <em>b</em></div>"""
        checkers = []

        checkers.append(Checker([ConditionID('b')], CheckerItemProperties(1, 800)))

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, 'a b')
        self.assertEqual(items[0].speaker_idx, 1)

    def test_merge_items2(self):
        html = """<div class="c"><p id="a">a <a href="">b</a>. c.</p><p id="b">a <em>b</em>, c — d <a href="">e</a> f — g.</p><p id="c">a <a href="">b</a> c. d. e.</p></div>"""
        checkers = []

        checkers.append(Checker([ConditionID('b')], CheckerItemProperties(1, 800)))
        checkers.append(Checker([ConditionName('p')], CheckerItemProperties(0, 800)))

        reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, 'a b. c.')
        self.assertEqual(items[0].speaker_idx, 0)
        self.assertEqual(items[2].text, 'a b, c — d e f — g.')
        self.assertEqual(items[2].speaker_idx, 1)
        self.assertEqual(items[4].text, 'a b c. d. e.')

    def test_merge_items3(self):
        html = """<div style="text-align: justify;">Released 1992 for <b>Macintosh</b> <br></div>"""
        checkers = []

        checkers.append(Checker([ConditionName('br')], CheckerItemProperties(0, 800)))

        reader = TTS_HTML_Reader(custom_checkers=checkers)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, 'Released 1992 for Macintosh')

    def test_merge_items4(self):
        html = """<span>1</span><span>2</span>"""

        checkers = []

        checkers.append(Checker([ConditionName('span')], CheckerItemProperties()))

        reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, '12')

    def test_merge_items5(self):
        html = """<span>1</span><span>2</span>"""

        checkers = []

        checkers.append(Checker([ConditionName('span')], CheckerItemProperties()))

        reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].text, '12')
        # self.assertEqual(items[1].text, '2')

    # def test_merge_items6(self):
    #     # html = """<p>a <a href="">b</a>:<strong> </strong>c </p>"""
    #     html = """<p id="2AaPJu">For more than two decades, the American Lung Association (ALA) has <a href="https://www.lung.org/research/sota">posed a simple question</a>:<strong> </strong>Is air pollution in the United States getting better or worse? </p>"""

    #     checkers = []

    #     # checkers.append(Checker([ConditionName('span')], CheckerItemProperties()))

    #     reader = TTS_HTML_Reader(custom_checkers=checkers)
    #     reader.load_raw(html)

    #     items = reader.project.tts_chapters[0].tts_items

    #     project = TTS_Project()
    #     project.tts_chapters.append(TTS_Chapter(items))
    #     project.optimize()
    #     items = project.tts_chapters[0].tts_items

    #     # p = TTS_Processor()
    #     # items = p.preprocess_items(items)
    #     # reader.project = project
    #     # reader.synthesize('/tmp/test.mp3')

    #     self.assertEqual(items[0].text, 'a')
    #     # self.assertEqual(items[1].text, '2')

    # def test_merge_items7(self):
    #     html = """<div>a. <b>b</b>. c. <i>d: </i><b>e</b>.</div>"""

    #     checkers = []

    #     checkers.append(Checker([ConditionName('b')], CheckerItemProperties(speaker_idx=1)))
    #     checkers.append(Checker([ConditionName('i')], CheckerItemProperties(speaker_idx=1)))

    #     reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
    #     reader.load_raw(html)

    #     items = reader.project.tts_chapters[0].tts_items

    #     project = TTS_Project()
    #     project.tts_chapters.append(TTS_Chapter(items))
    #     project.optimize()
    #     items = project.tts_chapters[0].tts_items

    #     self.assertEqual(items[0].text, '12')

    def test_nested_tags(self):
        # html = """<p>a <a href="">b</a>:<strong> </strong>c </p>"""
        html = """<blockquote><p>test</p></blockquote>"""

        checkers = []

        checkers.append(Checker([ConditionName('p')], CheckerItemProperties(0)))
        checkers.append(Checker([ConditionName('blockquote')], CheckerItemProperties(1)))

        reader = TTS_HTML_Reader(custom_checkers=checkers, ignore_default_checkers=True)
        reader.load_raw(html)

        items = reader.project.tts_chapters[0].tts_items

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize()
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].speaker_idx, 1)

    def test_merge_items_pause(self):

        items = []

        items.append(TTS_Item(length=1000))
        items.append(TTS_Item(length=1000))
        items.append(TTS_Item(length=1000))

        project = TTS_Project()
        project.tts_chapters.append(TTS_Chapter(items))
        project.optimize(1500)
        items = project.tts_chapters[0].tts_items

        self.assertEqual(items[0].length, 1500)

    def test_epub1(self):
        preferred_speakers = ['p273', 'p330']

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, 'epub_test.epub')

            urllib.request.urlretrieve('https://epubtest.org/books/Fundamental-Accessibility-Tests-Basic-Functionality-v1.0.0.epub', file_path)

            checkers = []

            checkers.append(Checker([ConditionName('h1')], CheckerItemProperties(1, 800)))

            reader = TTS_EPUB_Reader(preferred_speakers, custom_checkers=checkers)
            reader.load(file_path)
            reader.get_project().optimize()

            items = reader.get_project().tts_chapters[0].tts_items

            self.assertEqual(items[0].text, 'Table of Contents')
            self.assertEqual(items[0].speaker_idx, 1)

            items = reader.get_project().tts_chapters[2].tts_items

            self.assertEqual(items[0].text, 'Introduction')
            self.assertEqual(items[0].speaker_idx, 1)
            self.assertEqual(items[4].text, 'This publication is currently considered [stable] by the DAISY Consortium and is in support of the efforts of the W3C EPUB 3 Community Group.')
            self.assertEqual(items[4].speaker_idx, 0)


if __name__ == '__main__':
    unittest.main()
