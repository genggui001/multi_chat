import logging
import re
import sys
from typing import TYPE_CHECKING, Union

import loguru

if TYPE_CHECKING:
    from loguru import Logger, Record


logger: "Logger" = loguru.logger


class LoguruHandler(logging.Handler):  # pragma: no cover
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def escape_tag(s: str) -> str:
    return re.sub(r"</?((?:[fb]g\s)?[^<>\s]*)>", r"\\\g<0>", s)


def default_filter(level: Union[str, int]):
    def _filter(record: "Record"):
        levelno = logger.level(level).no if isinstance(level, str) else level
        return record["level"].no >= levelno

    return _filter


# setup default logger handler
logger.remove()
logger.add("./logs/run_{time}.log", backtrace=True, diagnose=True, rotation="200KB", retention=10, compression="gz", level="INFO")
default_format = (
    "<g>{time:MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    # "<c>{function}:{line}</c>| "
    "{message}"
)
