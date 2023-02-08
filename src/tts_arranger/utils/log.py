from enum import Enum, auto


class bcolors:
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
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


def log(log_type: LOG_TYPE, message: str):
    format = f'{bcolors.ENDC}'

    if log_type == LOG_TYPE.INFO:
        format = f'{bcolors.HEADER}'
    elif log_type == LOG_TYPE.WARNING:
        format = f'{bcolors.WARNING}'
    elif log_type == LOG_TYPE.ERROR:
        format = f'{bcolors.FAIL}'

    print(format + message + f'{bcolors.ENDC}')
