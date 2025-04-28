import logging.config

def setup_logger(debug_level=logging.WARN):
    logging_config = dict(
        version = 1,
        formatters = {
            'colored': {
                '()': 'colorlog.ColoredFormatter',
                'fmt': '%(asctime)s %(name)-4s: %(log_color)s %(levelname)-8s %(blue)s%(message)s'},        
            },
        handlers = {
            'h': {'class': 'logging.StreamHandler',
                'formatter': 'colored',
                'level': logging.DEBUG}
            },
        root = {
            'handlers': ['h'],
            'level': debug_level,
            },
    )


    logging.config.dictConfig(logging_config)
    return logging.getLogger()