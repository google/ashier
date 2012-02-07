#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Ashier: Template-based scripting for terminal interactions.

Ashier is a program that serves the same purpose as expect(1): it helps
users script terminal interactions. However, unlike expect, Ashier is
programming language agnostic and provides a readable template language
for terminal output matching. These features make scripted terminal
interactions simpler to create and easier to maintain.

This module contains unit tests for the directive module.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'


import unittest

from .. import directive
from .. import linebuf
from .. import reactive
from .. import utils


class TestPattern(unittest.TestCase):
  """Unit tests for reactive.Pattern."""

  def DoSetup(self, sample, marks):
    utils._error_messages = []
    line = directive.Line('fn', 4, '')
    template = directive.Template(line, sample)
    markers = []
    for start, finish, name in marks:
      markers.append(directive.Marker(line, start, finish, name, ''))
    return reactive.Pattern(template, markers)

  def DoTestInit(self, sample, marks, regex, bound_names):
    pattern = self.DoSetup(sample, marks)
    self.assertEqual(pattern.pattern, regex)
    self.assertEqual(pattern.bound_names, bound_names)
    self.assertEqual(utils._error_messages, [])

  def testInit(self):
    """Test Pattern object initialization."""

    self.DoTestInit('abc: def/123',
                    [(0, 3, 'title'), (5, 8, None), (9, 12, 'end')],
                    r'([^:]+)\:\s+([^/]+)\/(.+)',
                    ['title', None, 'end'])
    self.DoTestInit('abc: def/123',
                    [(5, 8, None), (9, 12, 'end'), (0, 3, 'title')],
                    r'([^:]+)\:\s+([^/]+)\/(.+)',
                    ['title', None, 'end'])
    self.DoTestInit('abc: def/123',
                    [(5, 8, None), (0, 3, 'title'), (9, 12, 'end')],
                    r'([^:]+)\:\s+([^/]+)\/(.+)',
                    ['title', None, 'end'])

  def DoTestInitError(self, sample, marks):
    self.DoSetup(sample, marks)
    self.assertNotEqual(utils._error_messages, [])

  def testInitError(self):
    """Test Pattern object initialization failures.

    If there are overlapping markers, or if a marker extends beyond
    the end of the sample string, the Pattern constructor should
    report an error.
    """

    self.DoTestInitError(
        'abc: def/123', [(0, 6, 'title'), (5, 8, None)])
    self.DoTestInitError(
        'abc: def/123', [(0, 3, 'title'), (5, 15, None)])
    self.DoTestInitError(
        'a:c: def/123', [(0, 3, 'title'), (5, 8, None)])
    self.DoTestInitError(
        'abc:  ef/123', [(0, 3, 'title'), (5, 8, None)])


class TestReactive(unittest.TestCase):
  """Unit tests for reactive.Reactive."""

  def DoSetup(self, nesting, config):
    utils._error_messages = []
    directives = []
    for lineno, content in enumerate(config):
      line = directive.Line('fn', lineno, content)
      directives.append(directive.ParseDirective(line))
    return reactive.Reactive(nesting, directives)

  def DoTestInitErrors(self, config):
    self.DoSetup([], config)
    self.assertNotEqual(utils._error_messages, [])

  def testInitErrors(self):
    """Test Reactive object initialization failures.

    If the directives are out of order (e.g., Send before Template),
    miss essential parts (Marker without Template), or have
    non-uniform levels of indentation, the Reactive constructor should
    report an error.
    """

    self.DoTestInitErrors(['?\t  ....'])
    self.DoTestInitErrors(['>\tFoo', ' >\tBar'])
    self.DoTestInitErrors([' >\tFoo', '>\tBar'])
    self.DoTestInitErrors(['! terminal "abc"', '>\tBar'])
    self.DoTestInitErrors(['! terminal "abc"', '?\t .'])

  def DoTestReact(self, config_nesting, config, text, nesting, retval):
    react = self.DoSetup(config_nesting, config)
    buf = linebuf.Buffer()
    buf.AppendRawData(text)
    bound = react.React(nesting, buf, buf.GetBound(), [])
    self.assertEqual(bound, retval)
    self.assertEqual(utils._error_messages, [])

  def testReact(self):
    """Test React input matching."""

    self.DoTestReact([], [' >\tFoo'], 'Foo', [], -2)
    self.DoTestReact([], [' >\tFoo'], 'FooBar', [], -2)
    self.DoTestReact([], [' >\tFoo', ' >'], 'Foo\nBar', [], -2)
    self.DoTestReact([], [' >\tFoo', ' >'], 'FooBar\n', [], 2)
    self.DoTestReact([], [' >\tFoo', ' >\tB'], 'Foo\nBar', [], -3)
    self.DoTestReact([], [' >\tFoo'], 'Foo', [(0, 0)], -2)
    self.DoTestReact([(0, 0)], [' >\tFoo'], 'Foo', [(0, 0)], -2)
    self.DoTestReact([(0, 0)], [' >\tFoo'], 'Foo', [], 2)


if __name__ == '__main__':
  unittest.main()
