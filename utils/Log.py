import logging
from colorama import init, Fore, Back

init(autoreset=True)

class ColorFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    COLORS = {
        "DEBUG": Fore.MAGENTA,
        "INFO": Fore.BLUE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.LIGHTRED_EX
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        level_name = record.levelname
        if self.use_color and level_name in self.COLORS:
            # print(type(record.asctime))
            # record.threadName = color + record.threadName
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)

def set_root_logger(level = logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    str_fmt = f"{Fore.LIGHTWHITE_EX}[%(asctime)s] %(levelname)-10s | %(filename)s::%(funcName)s %(threadName)s :  %(message)s"
    formatter = ColorFormatter(str_fmt)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

def main():
    set_root_logger()
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

if __name__ == "__main__":
    main()
