from contextlib import contextmanager
from time import perf_counter


@contextmanager
def timer():
    start=perf_counter(); result={"seconds": 0.0}
    try:
        yield result
    finally:
        result["seconds"] = perf_counter() - start
