import time
import logging

tic = time.perf_counter()

def elapsed(string=None):
    toc = time.perf_counter()
    return "{:.2f}s".format(toc-tic)

def log(string, level="INFO", show_time=True):
    logstring = ""
    if show_time: logstring += elapsed()
    logstring += " {}".format(string)
    if level == "INFO": logging.info(logstring)
    if level == "DEBUG": logging.debug(logstring)
