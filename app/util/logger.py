import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stream_handler_out = logging.StreamHandler(stream=sys.stdout)
stream_handler_out.setLevel(logging.DEBUG)

stream_handler_err = logging.StreamHandler(stream=sys.stderr)
stream_handler_err.setLevel(logging.WARNING)


formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
stream_handler_out.setFormatter(formatter)
stream_handler_err.setFormatter(formatter)

logger.addHandler(stream_handler_out)
logger.addHandler(stream_handler_err)
