import sys

from .config import Config
from .log import default_filter, default_format, escape_tag, logger

config = Config()

# config logger
for logger_config in config.logger:
    if logger_config.sink.type == "stdout":
        sink = sys.stdout
    elif logger_config.sink.type == "stderr":
        sink = sys.stderr
    else:
        sink = logger_config.sink.filename
    logger.add(
        sink,
        colorize=logger_config.colorize,
        diagnose=logger_config.diagnose,
        filter=default_filter(logger_config.level),
        format=default_format,
    )

logger.opt(colors=True).debug(
    f"Loaded <y><b>Config</b></y>: {escape_tag(str(config.dict()))}"
)

from .app import app as app
