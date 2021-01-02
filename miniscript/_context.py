from collections import abc
import typing

import jinja2
from jinja2 import lexer
from jinja2 import nativetypes  # type: ignore
from jinja2 import sandbox


# NOTE(dtantsur): NativeTemplate calls dict() breaking lazy rendering
class Template(jinja2.Template):
    environment_class = nativetypes.NativeEnvironment

    def render(self, context):
        try:
            context = self.environment.context_class(
                self.environment, context, self.name, self.blocks)
            return nativetypes.native_concat(self.root_render_func(context))
        except Exception:  # pragma: no cover
            return self.environment.handle_exception()


class Environment(sandbox.Environment):  # type: ignore
    """A templating environment."""

    code_generator_class = nativetypes.NativeCodeGenerator
    template_class = Template

    def __init__(self):
        super().__init__(autoescape=False)

    def _fixup_slashes(self, expr: str) -> typing.Iterator[str]:
        # See https://github.com/ansible/ansible/issues/11891
        expr = self.preprocess(expr)
        in_variable = False
        for _lineno, token_type, value in self.lex(expr):
            if token_type == lexer.TOKEN_VARIABLE_BEGIN:
                in_variable = True
            elif token_type == lexer.TOKEN_VARIABLE_END:
                in_variable = False
            elif in_variable and token_type == lexer.TOKEN_STRING:
                value = value.replace("\\", "\\\\")
            yield value

    def evaluate(self, expr: str, context: 'Context') -> typing.Any:
        """Evaluate an expression."""
        if '\\' in expr:
            expr = ''.join(self._fixup_slashes(expr))
        return self.from_string(expr).render(context)

    def evaluate_recursive(self, source, context: 'Context'):
        """Evaluate a complex value recursively."""
        if isinstance(source, dict):
            return Namespace(self, context, source)
        elif isinstance(source, list):
            return [self.evaluate_recursive(item, context) for item in source]
        elif isinstance(source, str):
            return self.evaluate(source, context)
        else:
            return source

    def evaluate_code(self, expr: str, context: 'Context') -> typing.Any:
        """Evaluate something as if it was surrounded by tags."""
        # Ansible definitely does something smarter...
        if not expr.startswith(self.variable_start_string):
            expr = self.variable_start_string + expr
        if not expr.endswith(self.variable_end_string):
            expr += self.variable_end_string
        return self.evaluate(expr, context)


Template.environment_class = Environment


class Namespace(abc.MutableMapping):
    """A namespace with value rendering.

    Works like a dictionary, but evaluates values on access using the provided
    templating environment.

    .. versionadded:: 1.1

    :param environment: Templating environment to use.
    :param context: A :class:`Context` object to hold execution context.
    :param args: Passed to ``dict`` unchanged.
    :param kwargs: Passed to ``dict`` unchanged.
    """

    __slots__ = ("_env", "_ctx", "_data")

    def __init__(
        self,
        environment: Environment,
        context: 'Context',
        *args,
        **kwargs
    ):
        self._data = dict(*args, **kwargs)
        self._env = environment
        self._ctx = context

    def __getitem__(self, key):
        value = self._data[key]
        return self._env.evaluate_recursive(value, self._ctx)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__} {self._data}"

    def copy(self) -> 'Namespace':
        """Make a shallow copy of the namespace."""
        return Namespace(self._env, self._ctx, self._data)

    def get_raw(self, key, default=None) -> typing.Any:
        """Get a value without evaluating it."""
        return self._data.get(key, default)

    def materialize(self) -> dict:
        """Recursively evaluate values, returning a normal dict."""
        return {key: materialize(value) for key, value in self.items()}


class Context(Namespace):
    """A context of an execution."""

    def __init__(self, engine, *args, **kwargs):
        # A trick to enable easier copying
        env = (engine if isinstance(engine, jinja2.Environment)
               else engine.environment)
        super().__init__(env, self, *args, **kwargs)

    def copy(self) -> 'Context':
        """Make a shallow copy of the context."""
        return Context(self._env, self._data)


def materialize(value):
    """Evaluate and meterialize value, getting rid of namespaces."""
    if isinstance(value, Namespace):
        return value.materialize()
    else:
        return value
