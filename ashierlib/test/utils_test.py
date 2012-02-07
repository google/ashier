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

This module contains unit tests for the utils module.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'


import unittest

from .. import utils


class TestSplitNone(unittest.TestCase):
  """Unit tests for utils.SplitNone()."""

  def DoTest(self, arg, expected):
    self.assertEqual(
        utils.SplitNone(arg), expected)

  def testEmpty(self):
    self.DoTest([], [])

  def testOnlyNone(self):
    self.DoTest([None], [])

  def testOnlyNones(self):
    self.DoTest([None, None, None], [])

  def testStartNone(self):
    self.DoTest([None, 3, 5], [[3, 5]])

  def testEndNone(self):
    self.DoTest([4, 2, None, None], [[4, 2]])

  def testStartEndNone(self):
    self.DoTest([None, 5, 0, None, None], [[5, 0]])

  def testSplitInTwo(self):
    self.DoTest([7, None, None, 6, 2], [[7], [6, 2]])

  def testSplitInThree(self):
    self.DoTest([2, None, 5, 3, None, 4], [[2], [5, 3], [4]])


class TestRemoveRegexBindingGroups(unittest.TestCase):
  """Unit tests for utils.RemoveRegexBindingGroups()."""

  def DoTest(self, arg, expected):
    self.assertEqual(
        utils.RemoveRegexBindingGroups(arg), expected)

  def testNoBindingGroup(self):
    self.DoTest(r'abc', r'abc')

  def testBindingGroup(self):
    self.DoTest(r'a(bc)', r'a(?:bc)')

  def testBindingGroups(self):
    self.DoTest(r'a(bc)(def)', r'a(?:bc)(?:def)')

  def testNestedBindingGroups(self):
    self.DoTest(r'a((bc))', r'a(?:(?:bc))')

  def testEscapedParens(self):
    self.DoTest(r'a\(b\)', r'a\(b\)')

  def testEscapedBackSlashes(self):
    self.DoTest(r'a\\(b\\)', r'a\\(?:b\\)')
    self.DoTest(r'a\\\(b\\)', r'a\\\(b\\)')
    self.DoTest(r'a\\\\(b\\)', r'a\\\\(?:b\\)')


if __name__ == '__main__':
  unittest.main()
