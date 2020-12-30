import typing


class Error(Exception):
    """Base class for all errors."""


class ExecutionFailed(Error):
    """Execution of a task failed."""


class InvalidScript(Error):
    """The script definition is invalid."""


class InvalidTask(Error):
    """The task definition is invalid."""


class UnknownTask(InvalidTask):
    """An task is not known."""


class FinishScript(BaseException):
    """Finish the script successfully."""

    def __init__(self, result: typing.Any):
        self.result = result


class Aborted(ExecutionFailed):
    """Abort the script."""
