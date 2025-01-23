from typing import List, Optional

import xml.etree.ElementTree as ET


class SSMLBuilder:
    def __init__(self):
        self.root: ET.Element = ET.Element(
            "speak",
            xmlns="http://www.w3.org/2001/10/synthesis",
            attrib={"version": "1.0", "xml:lang": "en-US"},
        )
        self.current_voice: Optional[ET.Element] = None

    def add_metadata(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        publisher: Optional[str] = None,
        language: Optional[str] = None,
        date: Optional[str] = None,
        rights: Optional[str] = None,
        format: Optional[str] = None,
        creators: Optional[List[str]] = None,
    ) -> "SSMLBuilder":
        metadata = ET.SubElement(self.root, "metadata")
        rdf_rdf = ET.SubElement(
            metadata,
            "rdf:RDF",
            {
                "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "xmlns:rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xmlns:dc": "http://purl.org/dc/elements/1.1/",
            },
        )
        rdf_description_attribs = {
            "rdf:about": "http://www.example.com/meta.ssml",
        }
        if title:
            rdf_description_attribs["dc:title"] = title
        if description:
            rdf_description_attribs["dc:description"] = description
        if publisher:
            rdf_description_attribs["dc:publisher"] = publisher
        if language:
            rdf_description_attribs["dc:language"] = language
        if date:
            rdf_description_attribs["dc:date"] = date
        if rights:
            rdf_description_attribs["dc:rights"] = rights
        if format:
            rdf_description_attribs["dc:format"] = format

        rdf_description = ET.SubElement(
            rdf_rdf,
            "rdf:Description",
            rdf_description_attribs,
        )
        if creators:
            dc_creator = ET.SubElement(rdf_description, "dc:creator")
            rdf_seq = ET.SubElement(dc_creator, "rdf:Seq", ID="Creators")
            for creator in creators:
                ET.SubElement(rdf_seq, "rdf:li").text = creator

        return self

    def add_voice(self, name: str, effect: Optional[str] = None) -> "SSMLBuilder":
        self.current_voice = ET.SubElement(self.root, "voice", name=name)
        if effect:
            self.current_voice.set("effect", effect)
        return self

    def add_text(self, text: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding text.")
        self.current_voice.text = (self.current_voice.text or "") + text
        return self

    def add_paragraph(self, text: Optional[str] = "") -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding paragraph.")
        p = ET.SubElement(self.current_voice, "p")
        p.text = text
        return self

    def add_sentence(self, text: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding sentence.")
        s = ET.SubElement(self.current_voice, "s")
        s.text = text
        return self

    def add_break(
        self, time: Optional[str] = None, strength: Optional[str] = None
    ) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding break.")
        if time:
            ET.SubElement(self.current_voice, "break", time=time)
        elif strength:
            ET.SubElement(self.current_voice, "break", strength=strength)
        else:
            ET.SubElement(self.current_voice, "break")
        return self

    def add_prosody(
        self,
        text: str,
        rate: str = "medium",
        pitch: str = "medium",
        volume: str = "medium",
    ) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding prosody.")
        prosody = ET.SubElement(
            self.current_voice, "prosody", rate=rate, pitch=pitch, volume=volume
        )
        prosody.text = text
        return self

    def add_audio(self, src: str, text: Optional[str] = None) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding audio.")
        audio = ET.SubElement(self.current_voice, "audio", src=src)
        if text:
            audio.text = text
        return self

    def add_bookmark(self, mark: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding bookmark.")
        ET.SubElement(self.current_voice, "bookmark", mark=mark)
        return self

    def add_emphasis(self, text: str, level: str = "moderate") -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding emphasis.")
        emphasis = ET.SubElement(self.current_voice, "emphasis", level=level)
        emphasis.text = text
        return self

    def add_lang(self, text: str, lang: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding lang.")
        lang_elem = ET.SubElement(self.current_voice, "lang", attrib={"xml:lang": lang})
        lang_elem.text = text
        return self

    def add_lexicon(self, uri: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding lexicon.")
        ET.SubElement(self.current_voice, "lexicon", uri=uri)
        return self

    def add_math(self, mathml: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding math.")
        math_elem = ET.SubElement(
            self.current_voice, "math", xmlns="http://www.w3.org/1998/Math/MathML"
        )
        math_elem.text = mathml
        return self

    def add_phoneme(self, text: str, alphabet: str, ph: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding phoneme.")
        phoneme = ET.SubElement(self.current_voice, "phoneme", alphabet=alphabet, ph=ph)
        phoneme.text = text
        return self

    def add_say_as(
        self,
        text: str,
        interpret_as: str,
        format: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding say-as.")
        attribs = {"interpret-as": interpret_as}
        if format:
            attribs["format"] = format
        if detail:
            attribs["detail"] = detail
        say_as = ET.SubElement(self.current_voice, "say-as", attrib=attribs)
        say_as.text = text
        return self

    def add_sub(self, text: str, alias: str) -> "SSMLBuilder":
        if self.current_voice is None:
            raise ValueError("Voice must be set before adding sub.")
        sub = ET.SubElement(self.current_voice, "sub", alias=alias)
        sub.text = text
        return self

    def to_string(self, pretty_print: bool = True) -> str:
        raw_ssml = ET.tostring(self.root, encoding="unicode", method="xml")
        if pretty_print:
            import xml.dom.minidom as minidom

            dom = minidom.parseString(raw_ssml)
            return dom.toprettyxml(indent="  ")
        return raw_ssml

    def save_to_file(self, filename: str) -> None:
        ssml_string = self.to_string()
        with open(filename, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(ssml_string)
