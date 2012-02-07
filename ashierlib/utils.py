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

This module contains utility functions.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'

import itertools
import sys


_error_messages = []


def ReportError(mesg):
  """Report a user error.

  Report an error message by adding the message, along with an
  Error: header, into the _error_messages queue.  Invoke this
  function when you detect a user error (which is different from
  a program bug).

  Args:
    mesg: the error message to report.
  """

  _error_messages.append('Error: ' + mesg)


def AbortOnError():
  """Abort the program if errors had been reported.

  If the error message queue is nonempty, print the error messages
  to stderr and abort the problem with exit status 252.
  """

  if _error_messages:
    _error_messages.append('Errors detected.  Exiting Ashier...\n')
    print >> sys.stderr, '\n'.join(_error_messages)
    sys.exit(252)


def SplitNone(l):
  """Split a list using None elements as separator.

  Args:
    l: a list which may contain some None elements.

  Returns:
    A list of non-empty lists, each of which contains a maximal
    sequence of non-None elements from the argument list.
  """

  groups = itertools.groupby(l, lambda x: x is not None)
  return [list(g) for k, g in groups if k]


def RemoveRegexBindingGroups(regex):
  """Replace binding parentheses in a regular expression.

  Identify all non-escaped open parentheses in the input regular
  expression and replace them with non-binding open parentheses so
  that they do not interfere with substring extraction.

  Args:
    regex: regular expression that may contain parentheses.

  Returns:
    The same regular expression but without binding groups.
  """

  result = []
  escaped = False
  for ch in regex:
    result.append('(?:' if ch == '(' and not escaped else ch)
    escaped = not escaped if ch == '\\' else False
  return ''.join(result)
