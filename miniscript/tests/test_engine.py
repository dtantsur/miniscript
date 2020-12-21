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

import unittest

from .. import _engine
from .. import _task


class TestTask(_task.Task):
    pass


class EngineTestCase(unittest.TestCase):

    def test_forbidden_names(self):
        for name in _engine._KNOWN_PARAMETERS:
            with self.subTest(name=name):
                self.assertRaises(ValueError, _engine.Engine,
                                  {name: TestTask})
