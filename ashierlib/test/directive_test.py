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
from .. import utils


class TestLine(unittest.TestCase):
  """Unit tests for directive.Line."""

  def DoTestIndent(self, content, indent):
    self.assertEqual(
        directive.Line('fn', 5, content).GetIndent(), indent)

  def testGetIndent(self):
    self.DoTestIndent('', 0)
    self.DoTestIndent('abc', 0)
    self.DoTestIndent(' ', 1)
    self.DoTestIndent(' abc', 1)
    self.DoTestIndent('  abc', 2)
    self.DoTestIndent('  ab  c ', 2)
    self.DoTestIndent('\tabc', 8)
    self.DoTestIndent(' \tabc', 8)
    self.DoTestIndent('\t abc', 9)


class TestParseDirective(unittest.TestCase):
  """Unit tests for directive.ParseDirective()."""

  def DoTestParseNone(self, content):
    utils._error_messages = []
    line = directive.Line('fn', 7, content)
    self.assertEqual(directive.ParseDirective(line), None)
    self.assertEqual(utils._error_messages, [])

  def testParseNone(self):
    """Test blank line parsing.

    Parsing a blank line, or a line that contains nothing but
    whitespaces and comments, should return None with no errors.
    """

    self.DoTestParseNone('')
    self.DoTestParseNone('  ')
    self.DoTestParseNone(' \t')
    self.DoTestParseNone(' # comment')
    self.DoTestParseNone(' \t# comment')

  def DoTestParseError(self, content):
    utils._error_messages = []
    line = directive.Line('fn', 7, content)
    result = directive.ParseDirective(line)
    self.assertEqual(result, None)
    self.assertNotEqual(utils._error_messages, [])

  def testParseError(self):
    """Test malformed directive parsing.

    Parsing a malformed directive (i.e., any string that is neither a
    blank line nor a well-formed directive) should return None and
    report an error.
    """

    self.DoTestParseError('string')
    self.DoTestParseError('>\t')
    self.DoTestParseError('>abc\tdef')
    self.DoTestParseError('?')
    self.DoTestParseError('?\t')
    self.DoTestParseError('?  \t  ...')
    self.DoTestParseError('? name')
    self.DoTestParseError('? . name /regex')
    self.DoTestParseError('!')
    self.DoTestParseError('! "string"')

  def DoTestParseTemplate(self, content, sample):
    utils._error_messages = []
    line = directive.Line('fn', 7, content)
    result = directive.ParseDirective(line)
    self.assertTrue(isinstance(result, directive.Template))
    self.assertEqual(result.sample, sample)
    self.assertEqual(utils._error_messages, [])

  def testParseTemplate(self):
    """Test Template directive parsing."""

    self.DoTestParseTemplate('>', '')
    self.DoTestParseTemplate('>abc', 'abc')
    self.DoTestParseTemplate(' >abc', 'abc')
    self.DoTestParseTemplate('>abc def ', 'abc def ')
    self.DoTestParseTemplate('>abc   def ', 'abc   def ')

  def DoTestParseMarker(self, content, start, finish, name, regex):
    utils._error_messages = []
    line = directive.Line('fn', 7, content)
    result = directive.ParseDirective(line)
    self.assertTrue(isinstance(result, directive.Marker))
    self.assertEqual(
        (result.start, result.finish, result.name, result._regex),
        (start, finish, name, regex))
    self.assertEqual(utils._error_messages, [])

  def testParseMarker(self):
    """Test Marker directive parsing."""

    self.DoTestParseMarker('?.', 0, 1, None, '')
    self.DoTestParseMarker('?     ....', 5, 9, None, '')
    self.DoTestParseMarker('? . zeros', 1, 2, 'zeros', '')
    self.DoTestParseMarker('? . /0+/', 1, 2, None, '0+')
    self.DoTestParseMarker('? . zeros /0+/', 1, 2, 'zeros', '0+')

  def DoTestParseSend(self, content, channel, message):
    utils._error_messages = []
    line = directive.Line('fn', 7, content)
    result = directive.ParseDirective(line)
    self.assertTrue(isinstance(result, directive.Send))
    self.assertEqual(
        (result._channel, result._message),
        (channel, message))
    self.assertEqual(utils._error_messages, [])

  def testParseSend(self):
    """Test Send directive parsing."""

    self.DoTestParseSend('!terminal "a"', 'terminal', 'a')
    self.DoTestParseSend('! terminal "a"', 'terminal', 'a')
    self.DoTestParseSend('!controller "ab c"', 'controller', 'ab c')
    self.DoTestParseSend('! controller "ab c"', 'controller', 'ab c')
    self.DoTestParseSend('! controller "a "bc""', 'controller', 'a "bc"')


class TestTemplate(unittest.TestCase):
  """Unit tests for directive.Template."""

  def DoSetup(self, sample, start, finish):
    utils._error_messages = []
    line = directive.Line('fn', 9, '')
    template = directive.Template(line, sample)
    return template.InferSkip(start, finish)

  def DoTestInferSkip(self, sample, start, finish, regex):
    inferred = self.DoSetup(sample, start, finish)
    self.assertEqual(inferred, regex)
    self.assertEqual(utils._error_messages, [])

  def testInferSkip(self):
    """Test skip regex pattern inference."""

    self.DoTestInferSkip('abc', 0, 2, 'ab')
    self.DoTestInferSkip('abc', 0, 3, 'abc')
    self.DoTestInferSkip('abc def', 2, 4, r'c\s+')
    self.DoTestInferSkip('abc def', 2, 5, r'c\s+d')
    self.DoTestInferSkip('abc  def', 2, 6, r'c\s+d')

  def DoTestInferSkipError(self, sample, start, finish):
    self.DoSetup(sample, start, finish)
    self.assertNotEqual(utils._error_messages, [])

  def testInferSkipError(self):
    """Test skip regex pattern inference failures.

    If the substring to skip does not have a well-defined end
    delimiter (e.g., the substring ends in the middle of a
    multi-character whitespace sequence), the InferSkip method should
    report an error.
    """

    self.DoTestInferSkipError('ab  ', 1, 3)
    self.DoTestInferSkipError('ab   ', 1, 3)


class TestMarker(unittest.TestCase):
  """Unit tests for directive.Marker."""

  def DoSetup(self, sample, start, finish):
    utils._error_messages = []
    line = directive.Line('fn', 2, '')
    template = directive.Template(line, sample)
    marker = directive.Marker(line, start, finish, None, '')
    return marker.InferRegex(template)

  def DoTestInferRegex(self, sample, start, finish, regex):
    inferred = self.DoSetup(sample, start, finish)
    self.assertEqual(inferred, regex)
    self.assertEqual(utils._error_messages, [])

  def testInferRegex(self):
    """Test variable substring regex pattern inference."""

    self.DoTestInferRegex('abc', 0, 2, '[^c]+')
    self.DoTestInferRegex('abc', 0, 3, '.+')
    self.DoTestInferRegex('abc def', 0, 3, r'[^\s]+')
    self.DoTestInferRegex('abc  def', 0, 3, r'[^\s]+')

  def DoTestInferRegexError(self, sample, start, finish):
    self.DoSetup(sample, start, finish)
    self.assertNotEqual(utils._error_messages, [])

  def testInferRegexError(self):
    """Test variable substring regex pattern inference failures.

    If the variable substring does not have a well-defined end
    delimiter (due to the delimiter appearing in the string to match),
    the InferRegex method should report an error.
    """

    self.DoTestInferRegexError('abcabc', 0, 4)


class TestSend(unittest.TestCase):
  """Unit tests for directive.Send."""

  def DoSetup(self, channel, message):
    utils._error_messages = []
    line = directive.Line('fn', 4, '')
    return directive.Send(line, channel, message)

  def DoTestInitError(self, channel):
    self.DoSetup(channel, '')
    self.assertNotEqual(utils._error_messages, [])

  def testInitError(self):
    """Test Send object initialization failures.

    If the channel name is not "terminal" or "controller", the Send
    constructor should report an error.
    """

    self.DoTestInitError('')
    self.DoTestInitError('comptroller')

  def DoTestReferences(self, message, references):
    result = self.DoSetup('terminal', message).References()
    self.assertEqual(result, references)
    self.assertEqual(utils._error_messages, [])

  def testReferences(self):
    """Test variable reference extraction."""

    self.DoTestReferences('abc def', set())
    self.DoTestReferences('$abc $def', set(['abc', 'def']))
    self.DoTestReferences('abc $$ def', set())
    self.DoTestReferences('abc $$def', set(['def']))

  def DoTestExpandVariables(self, message, bindings, expanded):
    result = self.DoSetup('terminal', message).ExpandVariables(bindings)
    self.assertEqual(result, expanded)
    self.assertEqual(utils._error_messages, [])

  def testExpandVariables(self):
    """Test message variable substitution."""

    self.DoTestExpandVariables('', dict(), '')
    self.DoTestExpandVariables(
        'abc $foo def', {'foo': 'bar'}, 'abc bar def')


if __name__ == '__main__':
  unittest.main()
