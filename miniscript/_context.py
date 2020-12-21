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
            if isinstance(source, Namespace):
                return source
            else:
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


class Namespace(dict):
    """A namespace with value rendering."""

    __slots__ = ("_env", "_ctx")

    def __init__(self, environment, context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._env = environment
        self._ctx = context

    def __getitem__(self, key):
        value = super().__getitem__(key)
        result = self._env.evaluate_recursive(value, self._ctx)
        return result

    def __iter__(self):
        raise NotImplementedError(
            "Iterating is not supported for lazy namespaces")


class Context(Namespace):
    """A context of an execution."""

    __slots__ = ()

    def __init__(self, engine, *args, **kwargs):
        super().__init__(engine.environment, self, *args, **kwargs)
