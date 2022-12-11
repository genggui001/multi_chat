import uvicorn

from multi_chat import config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "multi_chat.log.LoguruHandler",
        },
    },
    "loggers": {
        "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO",
        },
    },
}

if __name__ == "__main__":
    uvicorn.run(
        app=config.uvicorn.app_module,
        host=config.uvicorn.host,
        port=config.uvicorn.port,
        reload=config.uvicorn.reload,
        log_config=LOGGING_CONFIG,
    )
