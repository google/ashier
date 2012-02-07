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

This module defines reactive objects.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'

import itertools
import re

import directive


class Pattern(object):
  """Single-line pattern with substring extraction.

  A Pattern is the combination of one template directive and all its
  associated marker directives.  Those directives combined contain
  enough information for Ashier to infer a single-line (regular
  expression) pattern.

  Attributes:
    pattern: string representation of the pattern regex.
    bound_names: a list of marker names for the pattern.
  """

  def __init__(self, template, markers):
    regex = ''
    index = 0
    bound_names = []

    # Build a regular expression that matches the template string and
    # extracts the substrings indicated by the markers by traversing
    # the list of Marker objects in position-ascending order.  The
    # index variable points to the lowest template character position
    # that is not yet convered by the under-construction regular
    # expression in the regex variable.
    for m in sorted(markers, key=lambda m: m.start):

      # A marker should never extend beyond the end of the template.
      # If it does, report the problem back to the user.
      if m.finish > len(template.sample):
        m.ReportError('marker extends beyond template')
        continue

      # Current position is before the beginning of the next marker.
      # In this case, infer a regular expression to skip the unmarked
      # text in the slice [index:m.start] and fall through to the next
      # section (index == m.start).
      if index < m.start:
        regex += template.InferSkip(index, m.start)
        index = m.start

      # Current position matches the beginning of the next marker.  In
      # this case, infer a regular expression for the marker.
      if index == m.start:
        regex += '(' + m.InferRegex(template) + ')'
        bound_names.append(m.name)
        index = m.finish

      # Current position is beyond the beginning of the next marker.
      # In this case, report a user error because there must have been
      # two overlapping markers.
      else:
        m.ReportError('overlap with another marker')
        index = m.finish

    # Infer a regular expression that matches the unmarked template
    # text that follows the last marker.
    if index < len(template.sample):
      regex += template.InferSkip(index, len(template.sample))

    self.pattern = regex
    self.bound_names = bound_names
    self._regex = re.compile(self.pattern)

  def AttachEOLMarker(self):
    """Attach an EOL marker '$' to the pattern."""

    self.pattern += '$'
    self._regex = re.compile(self.pattern)

  def Match(self, text, bindings):
    """Match a string to a pattern.

    Check if the string argument matches the pattern and, if so,
    extact substrings into the bindings dictionary.

    Args:
      text: the string to match.
      bindings: dictionary to store extracted substrings.

    Returns:
      A Boolean value that indicates match success.
    """

    matches = self._regex.match(text)
    if matches:
      for index, name in enumerate(self.bound_names):
        if name:
          bindings[name] = matches.group(index+1)
      return True
    return False


class Reactive(object):
  """Action cued by string pattern matching.

  A Reactive object is the combination of a series of Patterns
  followed by zero or more Sends.  It is a self-contained unit that
  describes a (possibly multi-line) pattern to match and the actions
  to take once a match is found.
  """

  def __init__(self, nesting, spec):
    assert spec, 'Reactive called with empty argument'

    indent = spec[0].line.GetIndent()
    for elem in spec[1:]:
      if elem.line.GetIndent() != indent:
        elem.ReportError('indentation change in a group')
        break

    # Compute self._nesting, which should be the longest group
    # subsequence that has strictly increasing indentation and ends at
    # the current group.  Invariant: the nesting argument holds a
    # mutable duplicate copy of self._nesting of the last created
    # Reactive object.
    while nesting and nesting[-1][0] >= indent:
      nesting.pop()
    nesting.append((indent, spec[0].line.lineno))
    self._nesting = list(nesting)

    def IsTemplate(obj):
      return isinstance(obj, directive.Template)

    def IsMarker(obj):
      return isinstance(obj, directive.Marker)

    def IsSend(obj):
      return isinstance(obj, directive.Send)

    self._patterns = []
    index = 0

    while index < len(spec) and IsTemplate(spec[index]):
      markers = list(itertools.takewhile(IsMarker, spec[index+1:]))
      self._patterns.append(Pattern(spec[index], markers))
      index += len(markers)+1
    self._actions = list(itertools.takewhile(IsSend, spec[index:]))

    # Ashier interprets the final pattern in a group as a partial-line
    # pattern and all others as full-line patterns.  In accordance
    # with that interpretation, we add an EOL marker to each pattern
    # except for the last.
    for pattern in self._patterns[:-1]:
      pattern.AttachEOLMarker()

    if not self._patterns:
      spec[0].ReportError('group has no templates')

    if index+len(self._actions) < len(spec):
      non_action = spec[index+len(self._actions)]
      non_action.ReportError('template/marker after action')

    bound_names = set()
    for pat in self._patterns:
      bound_names.update(pat.bound_names)
    for send in self._actions:
      free_names = send.References().difference(bound_names)
      for name in free_names:
        send.ReportError('unbound name: %s' % name)

  def PatternSize(self):
    """Return pattern length (in lines)."""

    return len(self._patterns)

  def React(self, nesting, buf, bound, channels):
    """React if there is a match from line buffer.

    Args:
      nesting: persistent state to support nested matching.
        Initialize with a fresh empty mutable list and reuse the same
        list for subsequent calls.
      buf: a Buffer object that contains the terminal output to match.
      bound: integer index matching upper limit (non-inclusive).
      channels: dictionary that maps channel names (which are strings)
        to the corresponding writable file descriptors.

    Returns:
      An integer indicating the how the matching baseline should be
      adjusted.  If non-negative, the value indicates what the
      baseline *can* be raised to.  If negative, its absolute value
      indicates what the baseline *must* be raised to.
    """

    # If this Reactive object is inactive because one of its enclosing
    # objects had not been matched, do not continue with matching.
    # Return buf.GetBound() to indicate that this particular Reactive
    # object places no restrictions on how much the buffer baseline
    # can be raised.
    if nesting[:len(self._nesting)-1] != self._nesting[:-1]:
      return buf.GetBound()

    # If some of the lines needed for the current match no longer
    # exist in the buffer, do not continue with matching.  Instead,
    # request that the buffer baseline stay where it is (because there
    # is no evidence to exclude any line in the buffer from
    # contributing to a future match).
    start = bound-len(self._patterns)
    if start < buf.baseline:
      return buf.baseline

    bindings = dict()
    for index in xrange(start, bound):
      pattern = self._patterns[index-start]
      if not pattern.Match(buf.GetLine(index), bindings):

        # A negative match that occurred before the last buffered
        # (partial) line is definite because no new data can fix the
        # mismatch.  A negative match that occurred in the last
        # buffered (partial) line may become a positive match if more
        # data enters the buffer.  Allow the buffer baseline to
        # advance beyond start only if the negative match is definite.
        definite_mismatch = index < buf.GetBound()-1
        return start+1 if definite_mismatch else start

    # Positive match for all patterns: execute all actions and update
    # the current match nesting state.
    for send in self._actions:
      send.Send(channels, bindings)
    nesting[:] = self._nesting

    # If the last pattern is empty, retain the corresponding input
    # line in the buffer for future matches.  Otherwise, request
    # flushing all matched input lines out of the buffer.
    if not self._patterns[-1].pattern:
      return 1-bound
    return -bound
