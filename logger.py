import os
import logging
import re
from colorama import Fore, Style, init

init(autoreset=True)

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[38;5;51m" + Style.BRIGHT,
        logging.INFO: Fore.BLUE + Style.BRIGHT,
        logging.ERROR: "\x1b[38;5;204m" + Style.BRIGHT,
        logging.WARNING: "\x1b[38;5;7m" + Style.BRIGHT,
        logging.CRITICAL: "\x1b[38;5;135m" + Style.BRIGHT,
        'timestamp': Fore.LIGHTBLACK_EX + Style.BRIGHT,
        'filename': "\x1b[38;5;225m"
    }
    
    def format(self, record):
        record.asctime = self.formatTime(record, self.datefmt)
        colored_levelname = self.COLORS.get(record.levelno, Style.RESET_ALL) + record.levelname + Style.RESET_ALL
        timestamp_color = self.COLORS['timestamp'] + record.asctime + Style.RESET_ALL

        message = super().format(record)
        message = re.sub(
            r'<(.*?)>',
            lambda m: self.COLORS.get(record.levelno, Style.RESET_ALL) + m.group(1) + Style.RESET_ALL,
            message
        )
        message = message.replace(record.asctime, timestamp_color)\
                         .replace(record.levelname, colored_levelname)
        return message

def setup_logger(name='app_logger', log_file='app.log', level=logging.DEBUG):
    fmt = '%(asctime)s %(levelname)-8s %(message)s'
    formatter = ColorFormatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(ch)
    logger.addHandler(fh)
    
    return logger

log = setup_logger()
