import unittest

from tts_arranger import TTS_Processor
from tts_arranger.items.tts_item import TTS_Item


class Test(unittest.TestCase):
    def test_break1(self):
        t = TTS_Processor()

        tts_item = TTS_Item('This. Is: A t:est!', 'p330')

        tts_items = t._prepare_item(tts_item)

        self.assertEqual(tts_items[0].text, 'This. Is')
        self.assertEqual(tts_items[1].length, 150)
        self.assertEqual(tts_items[2].text, 'A t:est!')
        self.assertEqual(tts_items[3].length, 1000)

    # def test_break2(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item('This “Is” a test, right?', 'test', 10, 10, True)

    #     tts_items = t._prepare_item(tts_item)

    #     self.assertEqual(tts_items[0].text, 'This')
    #     self.assertEqual(tts_items[1].text, 'Is')
    #     self.assertEqual(tts_items[2].text, 'a test, right?')

    # def test_break3(self):
    #     t = TTS_Arranger()

    #     text = '''In this rough theatre of teeming peoples and conflicting cultures were developed the agriculture and commerce, the horse and wagon, the coinage and letters of credit, the crafts and industries, the law and government, the mathematics and medicine, the enemas and drainage systems, the geometry and astronomy, the calendar and clock and zodiac, the alphabet and writing, the paper and ink, the books and libraries and schools, the literature and music, the sculpture and architecture, the glazed pottery and fine furniture, the monotheism and monogamy, the cosmetics and jewelry, the checkers and dice, the ten-pins and income tax, the wet-nurses and beer, from which our own European and American culture derive by a continuous succession through the mediation of Crete and Greece and Rome.'''

    #     tts_item = TTS_Item(text, 'test', 10, 10, True)

    #     tts_items = t.prepare_item(tts_item)

    #     self.assertEqual(tts_items[0].text, 'In this rough theatre of teeming peoples and conflicting cultures were developed the agriculture and commerce, the horse and wagon, the coinage and letters of credit, the crafts and industries, the law and government, the mathematics and medicine, the enemas and drainage systems, the geometry and astronomy')
    #     self.assertEqual(tts_items[1].text, 'the calendar and clock and zodiac, the alphabet and writing, the paper and ink, the books and libraries and schools, the literature and music, the sculpture and architecture, the glazed pottery and fine furniture, the monotheism and monogamy, the cosmetics and jewelry, the checkers and dice')
    #     self.assertEqual(
    #         tts_items[2].text, 'the ten-pins and income tax, the wet-nurses and beer, from which our own European and American culture derive by a continuous succession through the mediation of Crete and Greece and Rome.')

    # def test_break4(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item('LoremipsumdolorsitametconsecteturadipiscingelitseddoeiusmodtemporincididuntutlaboreetdoloremagnaaliquaUtenimadminimveniamquisnostrudexercitationullamcolaborisnisiutaliquipexeacommodoconsequatduisauteiruredolorinreprehenderitinvoluptatevelitessecillumdoloreeufugiatnullapariaturexcepteursintoccaecatcupidatatnonproidentsuntinculpaquiofficiadeseruntmollitanimidestlaborum.', 'test', 10, 10, True)

    #     tts_items = t.prepare_item(tts_item)

    #     self.assertEqual(tts_items[0].text, 'LoremipsumdolorsitametconsecteturadipiscingelitseddoeiusmodtemporincididuntutlaboreetdoloremagnaaliquaUtenimadminimveniamquisnostrudexercitationullamcolaborisnisiutaliquipexeacommodoconsequatduisauteiruredolorinreprehenderitinvoluptatevelitessecillumdoloreeufugiatnullapariaturexcepteursintoccaecatcupidatatnonproidentsu')
    #     self.assertEqual(
    #         tts_items[1].text, 'ntinculpaquiofficiadeseruntmollitanimidestlaborum.')

    def test_url(self):
        t = TTS_Processor()

        tts_item = TTS_Item('https://stackoverflow.com/questions/17730788/search-and-replace-with-whole-word-only-option', '')

        tts_items = t._prepare_item(tts_item)
        self.assertEqual(tts_items[0].text, 'stackoverflow.com')

    def test_endings(self):
        t = TTS_Processor()

        tts_item = TTS_Item('''Lovely story!
Do you mean pidgin Danish, perhaps? :''', '')

        tts_items = t._prepare_item(tts_item)
        self.assertEqual(tts_items[0].text, 'Lovely story!')
        self.assertEqual(tts_items[1].length, 1000)
        self.assertEqual(tts_items[2].length, 250)
        self.assertEqual(tts_items[3].text, 'Do you mean pidgin Danish, perhaps?')
        self.assertEqual(tts_items[4].length, 1000)

    # def test_punctuation1(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item('Sure, these were all hoary old tropes even by the late ’70s/early ’80s, but this particular combination of them, at this exact date…? Even the “silly but kind of grim” atmosphere that you correctly mention the game possessing is the exact way I would describe “Night Horrors”.', '')

    #     tts_items = t._prepare_item(tts_item)
    #     self.assertEqual(tts_items[0].text, 'Sure, these were all hoary old tropes even by the late \'70s/early \'80s, but this particular combination of them, at this exact date?')
    #     self.assertEqual(tts_items[1].text, 'Even the')
    #     self.assertEqual(tts_items[2].text, 'silly but kind of grim')
    #     self.assertEqual(tts_items[3].text, 'atmosphere that you correctly mention the game possessing is the exact way I would describe')
    #     self.assertEqual(tts_items[4].text, 'Night Horrors.')

    def test_punctuation2(self):
        t = TTS_Processor()

        tts_item = TTS_Item('Specifically, he wanted to bring FORTRAN, as it happens the implementation language of the original Adventure (not that Ken likely knew this or cared), to the little Apple II.', '')

        tts_items = t._prepare_item(tts_item)
        self.assertEqual(tts_items[0].text, 'Specifically, he wanted to bring FORTRAN, as it happens the implementation language of the original Adventure')
        self.assertEqual(tts_items[1].length, 300)
        self.assertEqual(tts_items[2].text, 'not that Ken likely knew this or cared,')
        self.assertEqual(tts_items[3].length, 300)
        self.assertEqual(tts_items[4].text, 'to the little Apple 2.')
        self.assertEqual(tts_items[5].length, 750)

    def test_punctuation3(self):
        t = TTS_Processor()

        tts_item = TTS_Item('a — b.', '')

        tts_items = t._prepare_item(tts_item)
        self.assertEqual(tts_items[0].text, 'a')
        self.assertEqual(tts_items[1].length, 300)
        self.assertEqual(tts_items[2].text, 'b.')
        self.assertEqual(tts_items[3].length, 750)

    # def test_punctuation3(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item('Much of what led to designs like The Wizard and the Princess — the lack of understood “best practices” for game design, primitive technology, the simple inexperience of the designers themselves — I’ve already mentioned here and elsewhere. Certainly, as I’ve particularly harped, it was difficult with a Scott Adams- or Hi-Res-Adventures-level parser and world model to find a ground for challenging puzzles that were not unfair; the leap from trivial to impossible being made in one seemingly innocuous hop, as it were.', '')

    #     tts_items = t._prepare_item(tts_item)
    #     self.assertEqual(tts_items[0].text, 'Much of what led to designs like The Wizard and the Princess')
    #     self.assertEqual(tts_items[1].text, 'the lack of understood')
    #     self.assertEqual(tts_items[2].text, 'best practices')
    #     self.assertEqual(tts_items[3].text, 'for game design, primitive technology, the simple inexperience of the designers themselves')
    #     self.assertEqual(tts_items[4].text, 'I\'ve already mentioned here and elsewhere.')
    #     self.assertEqual(tts_items[5].text, 'Certainly, as I\'ve particularly harped, it was difficult with a Scott Adams- or Hi-Res-Adventures-level parser and world model to find a ground for challenging puzzles that were not unfair')
    #     self.assertEqual(tts_items[6].text, 'the leap from trivial to impossible being made in one seemingly innocuous hop, as it were.')

    # def test_start_end(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item(
    #         '“In ASCII “A” numerically follows “B” which follows “C,” etc.”.')

    #     # tts_items = t.break_start_end([tts_item], ('“', '”'), True)
    #     tts_items = t.break_speakers([tts_item], ('“', '”'), True)

    #     self.assertEqual(tts_items[0].text, 'In ASCII')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[1].text, 'A')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[2])
    #     self.assertEqual(tts_items[2].text, 'numerically follows')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[3].text, 'B')
    #     # self.assertEqual(tts_items[3].speaker, t.default_speakers[2])
    #     self.assertEqual(tts_items[4].text, 'which follows')
    #     # self.assertEqual(tts_items[4].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[5].text, 'C,')
    #     # self.assertEqual(tts_items[5].speaker, t.default_speakers[2])
    #     self.assertEqual(tts_items[6].text, 'etc..')
    #     # self.assertEqual(tts_items[6].speaker, t.default_speakers[1])
    #     # self.assertEqual(tts_items[7].text, '.')
    #     # self.assertEqual(tts_items[7].speaker, t.default_speakers[0])

    # def test_quotes2(self):
    #     t = TTS_Arranger()

    #     tts_item = TTS_Item('"This" is a "test".')

    #     tts_items = t.break_speakers([tts_item], ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'This')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[1].text, 'is a')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[2].text, 'test.')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[1])

    # def test_new_break(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('Hello, “This” is a “test”.', t.default_speakers[0]),
    #                  TTS_Item('“And this is another test.”', t.default_speakers[0])]

    #     tts_items = t.break_speakers(tts_items, ('“', '”'), True)

    #     self.assertEqual(tts_items[0].text, 'Hello,')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[1].text, 'This')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[2].text, 'is a')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[3].text, 'test.')
    #     # self.assertEqual(tts_items[3].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[4].text, 'And this is another test.')
    #     # self.assertEqual(tts_items[4].speaker, t.default_speakers[1])

    # def test_start_end2(self):
    #     t = TTS_Arranger()

    #     tts_items = []

    #     tts_items.append(TTS_Item('Test abc “hallo test', ''))
    #     tts_items.append(TTS_Item('continued test” something.', ''))

    #     # tts_items = t.break_start_end([tts_item], ('“', '”'), True)
    #     tts_items = t.break_speakers(tts_items, ('“', '”'), True)

    #     self.assertEqual(tts_items[0].text, 'Test abc')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[1].text, 'hallo test')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[2].text, 'continued test')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[3].text, 'something.')
    #     # self.assertEqual(tts_items[3].speaker, t.default_speakers[0])

    # def test_new_break2(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('Hello, "This" is a "test".', t.default_speakers[0]),
    #                  TTS_Item('"And this is another test."', t.default_speakers[0])]

    #     tts_items = t.break_speakers(tts_items, ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'Hello,')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[1].text, 'This')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[2].text, 'is a')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[3].text, 'test.')
    #     # self.assertEqual(tts_items[3].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[4].text, 'And this is another test.')
    #     # self.assertEqual(tts_items[4].speaker, t.default_speakers[1])

    # def test_new_break3(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('"I’m a “test. ‘This as well’”."', t.default_speakers[0])]

    #     tts_items = t._prepare_item(tts_items[0])

    #     self.assertEqual(tts_items[0].text, 'I\'m a')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[1].text, 'test.')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[2])
    #     self.assertEqual(tts_items[2].text, 'This as well.')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[3])

    # def test_new_break_a1(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('a', t.default_speakers[0]), TTS_Item('"b"', t.default_speakers[0]), TTS_Item('"c"', t.default_speakers[0])]

    #     tts_items = t.break_speakers(tts_items, ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'a')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[1].text, 'b')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[2].text, 'c')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[1])

    # def test_new_break_a2(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('a', t.default_speakers[1]), TTS_Item('"b"', t.default_speakers[1]), TTS_Item('"c"', t.default_speakers[1])]

    #     tts_items = t.break_speakers(tts_items, ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'a')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[1].text, 'b')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[2])
    #     self.assertEqual(tts_items[2].text, 'c')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[2])

    # def test_new_break_a3(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('“‘"Test1."’”')]

    #     tts_items = t.break_speakers(tts_items, ('“', '”'), True)
    #     tts_items = t.break_speakers(tts_items, ('‘', '’'), True)
    #     tts_items = t.break_speakers(tts_items, ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'Test1.')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[3])

    # def test_new_break_a4(self):
    #     t = TTS_Arranger()

    #     tts_items = [TTS_Item('a'),
    #                  TTS_Item('“b'),
    #                  TTS_Item('c”')]

    #     tts_items = t.break_speakers(tts_items, ('“', '”'), True)
    #     # tts_items = t.break_speakers(tts_items, ('‘', '’'), True)
    #     # tts_items = t.break_speakers(tts_items, ('"', '"'), True)

    #     self.assertEqual(tts_items[0].text, 'a')
    #     # self.assertEqual(tts_items[0].speaker, t.default_speakers[0])
    #     self.assertEqual(tts_items[1].text, 'b')
    #     # self.assertEqual(tts_items[1].speaker, t.default_speakers[1])
    #     self.assertEqual(tts_items[2].text, 'c')
    #     # self.assertEqual(tts_items[2].speaker, t.default_speakers[1])

    def test_new_break_a5(self):
        t = TTS_Processor()

        tts_item = TTS_Item('sic!].')

        tts_items = t._prepare_item(tts_item)
        # tts_items = t.break_speakers(tts_items, ('‘', '’'), True)
        # tts_items = t.break_speakers(tts_items, ('"', '"'), True)

        self.assertEqual(tts_items[0].text, 'sic!')

    def test_new_break_a6(self):
        t = TTS_Processor()

        tts_item = TTS_Item('candle- ?, ?')

        tts_items = t._prepare_item(tts_item)
        # tts_items = t.break_speakers(tts_items, ('‘', '’'), True)
        # tts_items = t.break_speakers(tts_items, ('"', '"'), True)

        self.assertEqual(tts_items[0].text, 'candle-')
