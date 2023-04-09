from enum import Enum, auto


class bcolors:
    """Colors for console output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class LOG_TYPE(Enum):
    """Log types."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


def log(log_type: LOG_TYPE, message: str):
    """
    Print a colored message to the console based on the log type.

    :param log_type: The log type (INFO, WARNING, or ERROR).
    :type log_type: LOG_TYPE

    :param message: The message to print.
    :type message: str
    """
    format = bcolors.ENDC

    if log_type == LOG_TYPE.INFO:
        format = bcolors.HEADER
    elif log_type == LOG_TYPE.WARNING:
        format = bcolors.WARNING
    elif log_type == LOG_TYPE.ERROR:
        format = bcolors.FAIL

    print(format + message + bcolors.ENDC)
