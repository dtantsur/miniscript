# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from collections import abc
import typing

import jinja2
from jinja2 import nativetypes  # type: ignore
from jinja2 import sandbox  # type: ignore


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

    def evaluate(self, expr: str, context: 'Context') -> typing.Any:
        """Evaluate an expression."""
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
    """A namespace with value rendering."""

    __slots__ = ("_env", "_ctx", "_data")

    def __init__(self, environment, context, *args, **kwargs):
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

    def copy(self):
        return Namespace(self._env, self._ctx, self._data)


class Context(Namespace):
    """A context of an execution."""

    def __init__(self, engine, *args, **kwargs):
        # A trick to enable easier copying
        env = (engine if isinstance(engine, jinja2.Environment)
               else engine.environment)
        super().__init__(env, self, *args, **kwargs)

    def copy(self):
        return Context(self._env, self._data)
