import logging
import sys


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


logger = logging.getLogger()
logger.setLevel(logging.INFO)

out_handler = logging.StreamHandler(stream=sys.stdout)
out_handler.setLevel(logging.INFO)

out_handler.addFilter(MaxLevelFilter(logging.INFO))
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
out_handler.setFormatter(formatter)

err_handler = logging.StreamHandler(stream=sys.stderr)
err_handler.setLevel(logging.WARNING)
err_handler.setFormatter(formatter)

logger.addHandler(out_handler)
logger.addHandler(err_handler)
