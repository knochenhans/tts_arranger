from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


@dataclass
class Element():
    name: str = ''
    id = ''
    classes: list[str] = field(default_factory=list)


class Condition(ABC):
    def __init__(self, arg: str):
        self.arg = arg

    @abstractmethod
    def check(self, elem: Element) -> bool:
        return False


class ConditionName(Condition):
    def check(self, elem: Element) -> bool:
        return elem.name == self.arg


class ConditionClass(Condition):
    def check(self, elem: Element) -> bool:
        return self.arg in elem.classes


class ConditionID(Condition):
    def check(self, elem: Element) -> bool:
        return self.arg == elem.id


class CHECKER_SIGNAL(Enum):
    NO_SIGNAL = auto()
    IGNORE = auto()
    NEW_CHAPTER = auto()


class CHECK_SPEAKER_RESULT(Enum):
    MATCHED = auto()
    NOT_MATCHED = auto()
    # IGNORE = auto()


@dataclass
class CheckerItemProperties():
    """
    Defines the properties for a TTS item to be generated. If pause_after is set, a pause item will be generated as well after the current item
    """
    speaker_idx: int = 0
    pause_after: int = 0


class Checker():
    """
    Consists of a list of conditions that must be met to return a set of TTS item properties and an optional signal
    """

    def __init__(self, conditions: list[Condition], properties: Optional[CheckerItemProperties], signal=CHECKER_SIGNAL.NO_SIGNAL):
        """
        :param conditions: a list of Condition objects
        :type conditions: list[Condition]

        :param properties: an optional CheckerItemProperties object
        :type properties: Optional[CheckerItemProperties]

        :param signal: an optional CHECKER_SIGNAL object, defaults to CHECKER_SIGNAL.NO_SIGNAL
        :type signal: CHECKER_SIGNAL, optional
        """
        self.conditions = conditions
        self.properties = properties
        self.signal = signal

    def determine(self, elem: Element) -> tuple[CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Optional[CheckerItemProperties]]:
        """
        Determines whether a given element meets a set of conditions and returns a set of TTS item properties and an optional signal.

        :param elem: an HTML Element object
        :type elem: Element

        :return: a tuple consisting of a CHECK_SPEAKER_RESULT object, a CHECKER_SIGNAL object, and an optional CheckerItemProperties object
        :rtype: tuple[CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Optional[CheckerItemProperties]]
        """
        ret_val = None
        ret_total = None

        for condition in self.conditions:
            ret_val = condition.check(elem)

            if ret_val:
                if self.signal == CHECKER_SIGNAL.IGNORE:
                    return CHECK_SPEAKER_RESULT.MATCHED, self.signal, None

            if ret_total:
                ret_total &= ret_val
            else:
                ret_total = ret_val

        if ret_total:
            return CHECK_SPEAKER_RESULT.MATCHED, self.signal, self.properties
        return CHECK_SPEAKER_RESULT.NOT_MATCHED, self.signal, None
