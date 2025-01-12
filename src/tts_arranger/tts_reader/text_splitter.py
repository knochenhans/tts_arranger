import ast
import json
from typing import Dict, List
import google.generativeai as genai

import typing_extensions as typing


# Set up type for the response, should contain text and type of the text
class TextItem(typing.TypedDict):
    text: str
    type: str


class TextSplitterResponse(typing.TypedDict):
    original_text: str
    splitted_text: List[TextItem]


class TextSplitter:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro-latest")

    def split_text(self, text: str) -> Dict:
        prompt = "Split the following text when encountering year numbers and acronyms (like US, NBC, etc.). Preserve punctuation and whitespace"
        contents = prompt + "\n\n" + text

        result = self.model.generate_content(
            contents=contents,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=TextSplitterResponse,
            ),
        )

        return ast.literal_eval(result.text).get("splitted_text")
