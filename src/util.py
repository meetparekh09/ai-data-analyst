import logging
import sys

def get_stdout_handler():
    stdout_handler = logging.StreamHandler(sys.stdout)
    return stdout_handler

def get_formatter():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    return formatter

def get_logger(name, level=logging.INFO, handler=get_stdout_handler(), formatter=get_formatter()):
    logger = logging.getLogger(name)
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def print_logprobs(logprobs, logger):
    logger.info(" ".join([f"{logprob.token}({logprob.logprob})" for logprob in logprobs]))
