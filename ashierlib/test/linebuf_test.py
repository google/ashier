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

This module contains unit tests for the linebuf module.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'


import random
import re
import unittest

from .. import linebuf


class TestBuffer(unittest.TestCase):
  """Unit tests for linebuf.Buffer."""

  def testBaseline(self):
    """Tests for Buffer.baseline.

    Buffer.baseline should be updated only by calls to
    Buffer.UpdateBaseline() and should not be updated by calls to
    Buffer.AppendRawData().  Buffer.UpdateBaseline() should keep
    Buffer.baseline unchanged and throw an AssertionError exception
    when its argument is out of range (i.e., lower than current
    baseline or higher than the maximum line number that currently
    exists in the buffer).
    """

    buf = linebuf.Buffer()
    self.assertEqual(buf.baseline, 1)
    self.assertRaises(AssertionError, buf.UpdateBaseline, 3)
    self.assertEqual(buf.baseline, 1)
    buf.UpdateBaseline(2)
    self.assertEqual(buf.baseline, 2)
    self.assertRaises(AssertionError, buf.UpdateBaseline, 1)
    self.assertRaises(AssertionError, buf.UpdateBaseline, 3)
    self.assertEqual(buf.baseline, 2)
    buf.AppendRawData('a\n\rb\n\rccc')
    buf.UpdateBaseline(3)
    self.assertEqual(buf.baseline, 3)
    self.assertRaises(AssertionError, buf.UpdateBaseline, 2)
    self.assertRaises(AssertionError, buf.UpdateBaseline, 5)
    self.assertEqual(buf.baseline, 3)
    buf.AppendRawData('c\n')
    self.assertEqual(buf.baseline, 3)

  def testBound(self):
    """Tests for Buffer.GetBound().

    Buffer.GetBound() should represent the upper line number limit
    (i.e., 1+ the maximum valid line number) of the Buffer object,
    where lines are separated by individual LF characters.
    """

    buf = linebuf.Buffer()
    self.assertEqual(buf.GetBound(), 2)
    buf.AppendRawData('a\r\nb\r\nccc')
    self.assertEqual(buf.GetBound(), 4)
    buf.AppendRawData('c\n')
    self.assertEqual(buf.GetBound(), 5)
    buf.AppendRawData('\r\r')
    self.assertEqual(buf.GetBound(), 5)

  def testFragmentation(self):
    """Tests for Buffer input fragmentation handling.

    The data stored in a Buffer object should be the same regardless
    of how the input is fragmented across Buffer.AppendRawData()
    calls.  This test feeds a test string into a Buffer object in
    randomly generated segments and check that the output remains
    identical regardless of input string segmentation.
    """

    rawstring = ('Pack my\r\r\nred\r\nbox\nwith five\r\n'
                 'dozen\rquality\r\n\r\r\njugs.\r\n')
    expected_output = re.split('\r*\n', rawstring)[:-1]
    random.seed(1337)

    for unused_count in range(100):
      buf = linebuf.Buffer()
      source = rawstring
      output = []
      while source:
        take = random.randint(1, 8)
        buf.AppendRawData(source[:take])
        source = source[take:]
        while buf.baseline < buf.GetBound()-1:
          output.append(buf.GetLine(buf.baseline))
          buf.UpdateBaseline(buf.baseline+1)
      self.assertEqual(output, expected_output)


if __name__ == '__main__':
  unittest.main()
