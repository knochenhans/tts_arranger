import base64
import datetime
import json
import pickle
import tempfile
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.element_optimizer import ElementOptimizer
from tts_arranger.items.tts_item import TTS_Item
from tts_arranger.items.tts_chapter import TTS_Chapter
from tts_arranger.items.tts_project import TTS_Project
from unittest import TestCase


def test_element1():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    optimizer = ElementOptimizer()

    merged_items = optimizer.merge_items([element1, element2], join_char=" ")

    assert len(merged_items) == 1
    assert merged_items[0].text == "test1 test2"

    merged_items[0].to_json()

    assert merged_items[0].to_json() == {
        "text": "test1 test2",
        "speaker_id": "1",
        "min_length": 1300,
        "custom_data": None,
    }


def test_element2():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="2", min_length=500)

    optimizer = ElementOptimizer()

    merged_items = optimizer.merge_items([element1, element2], join_char=" ")

    assert len(merged_items) == 2
    assert merged_items[0].text == "test1"
    assert merged_items[1].text == "test2"

    assert merged_items[0].to_json() == {
        "text": "test1",
        "speaker_id": "1",
        "min_length": 800,
        "custom_data": None,
    }

    assert merged_items[1].to_json() == {
        "text": "test2",
        "speaker_id": "2",
        "min_length": 500,
        "custom_data": None,
    }


def test_element3():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)
    element3 = TTS_Element(text="test3", speaker_id="2", min_length=1000)

    optimizer = ElementOptimizer()

    merged_items = optimizer.optimize(
        [element1, element2, element3], max_pause_duration=200, join_char=" "
    )

    assert len(merged_items) == 2

    assert merged_items[0].text == "test1 test2"
    assert merged_items[0].min_length == 200
    assert merged_items[0].speaker_id == "1"
    assert merged_items[0].to_json() == {
        "text": "test1 test2",
        "speaker_id": "1",
        "min_length": 200,
        "custom_data": None,
    }

    assert merged_items[1].text == "test3"
    assert merged_items[1].min_length == 200
    assert merged_items[1].speaker_id == "2"
    assert merged_items[1].to_json() == {
        "text": "test3",
        "speaker_id": "2",
        "min_length": 200,
        "custom_data": None,
    }


def test_element4_from_to_json():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    optimizer = ElementOptimizer()

    merged_items = optimizer.merge_items([element1, element2], join_char=" ")

    assert len(merged_items) == 1
    assert merged_items[0].text == "test1 test2"

    json_data = merged_items[0].to_json()

    assert json_data == {
        "text": "test1 test2",
        "speaker_id": "1",
        "min_length": 1300,
        "custom_data": None,
    }

    element3 = TTS_Element.from_json(json_data)

    assert element3.text == "test1 test2"
    assert element3.speaker_id == "1"
    assert element3.min_length == 1300
    assert element3.custom_data is None


def test_save_load_project_json():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    optimizer = ElementOptimizer()

    merged_items = optimizer.merge_items([element1, element2], join_char=" ")

    assert len(merged_items) == 1
    assert merged_items[0].text == "test1 test2"

    json_data = merged_items[0].to_json()

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(json.dumps(json_data).encode("utf-8"))
        temp_file_path = temp_file.name

    with open(temp_file_path, "r") as temp_file:
        loaded_json_data = json.load(temp_file)

    assert loaded_json_data == json_data

    loaded_element = TTS_Element.from_json(loaded_json_data)

    assert loaded_element.text == "test1 test2"
    assert loaded_element.speaker_id == "1"
    assert loaded_element.min_length == 1300
    assert loaded_element.custom_data is None


def test_item1():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    assert len(item1) == 2


def test_item2():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="2", min_length=500)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    assert len(item1) == 2
    assert item1[0].text == "test1"
    assert item1[1].text == "test2"


def test_item3():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)
    element3 = TTS_Element(text="test3", speaker_id="2", min_length=1000)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)
    item1.append(element3)

    assert len(item1) == 3
    assert item1[0].text == "test1"
    assert item1[1].text == "test2"
    assert item1[2].text == "test3"


def test_item4_to_json():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    json_data = item1.to_json()
    expected_json_data = {
        "elements": [
            {
                "text": "test1",
                "speaker_id": "1",
                "min_length": 800,
                "custom_data": None,
            },
            {
                "text": "test2",
                "speaker_id": "1",
                "min_length": 500,
                "custom_data": None,
            },
        ]
    }

    TestCase().assertDictEqual(
        json_data,
        expected_json_data,
    )


def test_chapter1():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    chapter1 = TTS_Chapter()
    chapter1.append(item1)

    assert len(chapter1) == 1
    assert len(chapter1[0]) == 2
    assert chapter1[0][0].text == "test1"
    assert chapter1[0][1].text == "test2"


def test_chapter2():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)
    element3 = TTS_Element(text="test3", speaker_id="2", min_length=1000)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    item2 = TTS_Item()
    item2.append(element3)

    chapter1 = TTS_Chapter()
    chapter1.append(item1)
    chapter1.append(item2)

    assert len(chapter1) == 2
    assert len(chapter1[0]) == 2
    assert len(chapter1[1]) == 1
    assert chapter1[0][0].text == "test1"
    assert chapter1[0][1].text == "test2"
    assert chapter1[1][0].text == "test3"


def test_chapter4_to_json():
    element1 = TTS_Element(text="test1", speaker_id="1", min_length=800)
    element2 = TTS_Element(text="test2", speaker_id="1", min_length=500)
    element3 = TTS_Element(text="test3", speaker_id="2", min_length=1000)

    item1 = TTS_Item()
    item1.append(element1)
    item1.append(element2)

    item2 = TTS_Item()
    item2.append(element3)

    chapter1 = TTS_Chapter()
    chapter1.append(item1)
    chapter1.append(item2)

    json_data = chapter1.to_json()
    expected_json_data = {
        "items": [
            {
                "elements": [
                    {
                        "text": "test1",
                        "speaker_id": "1",
                        "min_length": 800,
                        "custom_data": None,
                    },
                    {
                        "text": "test2",
                        "speaker_id": "1",
                        "min_length": 500,
                        "custom_data": None,
                    },
                ]
            },
            {
                "elements": [
                    {
                        "text": "test3",
                        "speaker_id": "2",
                        "min_length": 1000,
                        "custom_data": None,
                    }
                ]
            },
        ],
        "title": "",
        "start_time": 0,
        "end_time": 0,
    }

    TestCase().assertDictEqual(
        json_data,
        expected_json_data,
    )


def test_project_from_json():
    json_data = json.dumps(
        {
            "tts_chapters": [],
            "title": "Test Project",
            "subtitle": "Test Subtitle",
            "date": datetime.datetime.now().isoformat(),
            "author": "Test Author",
            "lang_code": "en",
            "image_bytes": base64.b64encode(b"test_image").decode("utf-8"),
            "raw": False,
        }
    )

    project = TTS_Project.from_json(json_data)

    assert project.title == "Test Project"
    assert project.subtitle == "Test Subtitle"
    assert project.author == "Test Author"
    assert project.lang_code == "en"
    assert project.image_bytes == b"test_image"
    assert project.raw is False


def test_project_to_json():
    project = TTS_Project(
        title="Test Project",
        subtitle="Test Subtitle",
        date=datetime.datetime.now(),
        author="Test Author",
        lang_code="en",
        image_bytes=b"test_image",
        raw=False,
    )

    json_data = project.to_json()
    loaded_data = json.loads(json_data)

    assert loaded_data["title"] == "Test Project"
    assert loaded_data["subtitle"] == "Test Subtitle"
    assert loaded_data["author"] == "Test Author"
    assert loaded_data["lang_code"] == "en"
    assert base64.b64decode(loaded_data["image_bytes"]) == b"test_image"
    assert loaded_data["raw"] is False


def test_project_merge():
    project1 = TTS_Project(title="Project 1")
    project2 = TTS_Project(title="Project 2")

    project1.merge_from_project(project2)

    assert len(project1.tts_chapters) == len(project2.tts_chapters)


def test_project_dump_as_json_file():
    project = TTS_Project(title="Test Project")
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name

    project.dump_as_json_file(temp_file_path)

    with open(temp_file_path, "rb") as file:
        loaded_project = pickle.load(file)

    assert loaded_project.title == "Test Project"
