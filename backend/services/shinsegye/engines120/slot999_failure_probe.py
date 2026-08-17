"""Failure probe slot for dispatch error-code standardization validation."""


def main(*args, **kwargs):
    raise RuntimeError("intentional runtime failure for failure-code validation")
