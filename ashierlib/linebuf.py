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

This module defines buffer objects for holding terminal output.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'


class Buffer(object):
  """A FIFO buffer that holds lines of text.

  Attributes:
    baseline: the index of the earliest buffered line.
  """

  # Invariants:
  #   len(self._lines) > 0
  #   self.baseline is the index of the earliest buffered line
  #   self.GetBound() is the index of the latest buffered line +1
  #   self.GetBound() >= self.baseline
  #   self._lines[:-1] stores completed lines
  #   self._lines[-1] stores the (latest) partial line
  #   self._lines[index+1] is the line numbered (self.baseline+index)
  #   self._lines[0] is inaccessible
  #   self.GetLine(lineno) requires self.baseline <= lineno
  #   self.GetLine(lineno) requires self.GetBound() > lineno

  def __init__(self):
    self.baseline = 1
    self._lines = ['']*2

  def GetBound(self):
    """Get the non-inclusive line number upper bound.

    Returns:
      The non-inclusive line number upper bound for lines currently
      stored in the buffer.
    """

    return self.baseline+len(self._lines)-1

  def AppendRawData(self, content):
    """Add raw (not-yet-split) text data to the buffer.

    Break raw strings (as captured from PTY device) into lines and add
    them into the buffer.

    Args:
      content: raw text data from PTY device.
    """

    # Break incoming raw PTY output into lines with '\n' and then
    # strip all occurrences of \r from the end of each line.  Since
    # the last line in self._lines always stores a partial line, the
    # first line of the incoming PTY output should be added to the end
    # of self._lines[-1].

    lines = (self._lines[-1]+content).split('\n')
    for index in range(len(lines)-1):
      lines[index] = lines[index].rstrip('\r')
    self._lines[-1:] = lines

  def UpdateBaseline(self, new_baseline):
    """Update the low-end of the buffer range.

    Using this function to set a higher baseline number removes from
    the buffer the lines numbered lower than the new baseline.  The
    argument should be no lower than self.baseline and no higher than
    self.GetBound().

    Args:
      new_baseline: new baseline number.
    """

    assert new_baseline >= self.baseline, (
        'new_baseline < self.baseline')
    assert new_baseline <= self.GetBound(), (
        'new_baseline > self.GetBound()')

    del self._lines[:new_baseline-self.baseline]
    self.baseline = new_baseline

  def GetLine(self, lineno):
    """Get a line of text from the buffer.

    Returns a line in the buffer.  The argument should be lower than
    self.GetBound() but not lower than self.baseline.

    Args:
      lineno: index number of the line to retrieve.

    Returns:
      The line with the specified index number.
    """

    assert lineno >= self.baseline, 'lineno < self.baseline'
    assert lineno < self.GetBound(), 'lineno >= self.GetBound()'

    return self._lines[lineno-self.baseline+1]
