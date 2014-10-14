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

This module defines configuration directives.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'

import os
import re
import utils


def CreateLines(filename):
  """Create Line objects from a text file.

  Args:
    filename: name of the file to read from.

  Returns:
    A list of Line objects read from the file.
  """

  lineno = 1
  lines = []
  try:
    with open(filename) as f:
      for line in f:
        lines.append(Line(filename, lineno, line))
        lineno += 1
    return lines
  except IOError as err:
    utils.ReportError(str(err))
    return ''


class Line(object):
  """Line in an Ashier configuration file.

  Attributes:
    lineno: line number in the configuration file.
    content: the content of the line as a string.
  """

  def __init__(self, filename, lineno, content):
    self.lineno = lineno
    self.content = content
    self._header = '%s:%d  ' % (filename, lineno)

  def GetIndent(self):
    """Compute the indentation level of the line.

    Returns:
      The number of tab-expanded leading spaces for the line.
    """

    expanded = self.content.expandtabs(8)
    return len(expanded)-len(expanded.lstrip())

  def StrippedContent(self):
    """Return stripped line content.

    Returns:
      String content of the line with leading spaces and the trailing
      newline (LF) stripped.
    """

    return self.content.lstrip().rstrip('\n')

  def WithIdentHeader(self, mesg):
    """Attach a line identification header to a string.

    Attach a header to the argument string (e.g., an error message) to
    identify the source file and line number for the line.

    Args:
      mesg: a string with information about the Line object.

    Returns:
      A string that consists of the input information string prefixed
      with an identifying header.
    """

    return self._header+mesg

  def ReportError(self, mesg):
    """Report an error that stems from this line.

    Args:
      mesg: the error message to report.
    """

    utils.ReportError(self.WithIdentHeader(mesg))


def ParseDirective(line):
  """Parse a line into a directive object.

  Args:
    line: a Line object to be parsed.

  Returns:
    A directive object (Template, Marker, or Send), or None if the
    line is blank, a comment, or malformed.
  """

  source = line.StrippedContent()

  if source.startswith('#') or not source:
    return None

  elif '\t' in source:
    line.ReportError('unexpected TAB in directive')

  elif source.startswith('>'):
    return Template(line, source[1:])

  elif source.startswith('?'):
    if source == '?':
      line.ReportError('empty marker directive')
    else:
      syntax = re.compile(r' *(\.+) *(\w+)? *(?:/(.+)/)? *$')
      matches = syntax.match(source[1:])
      if matches:
        start, finish = matches.span(1)
        name = matches.group(2)
        regex = matches.group(3) or ''
        return Marker(line, start, finish, name, regex)
      else:
        line.ReportError('malformed marker directive')

  elif source.startswith('!'):
    if source == '!':
      line.ReportError('empty action directive')
    else:
      syntax = re.compile(r' *(\w+) +"(.*)" *$')
      matches = syntax.match(source[1:])
      if matches:
        channel = matches.group(1)
        message = matches.group(2)
        return Send(line, channel, message)
      else:
        line.ReportError('malformed action directive')

  else:
    line.ReportError('unrecognized directive syntax')

  return None


class Template(object):
  """The template directive.

  The Template class represents template directives in Ashier
  configuration files.  Each template directive is a concrete example
  of a terminal output line that Ashier should try to match.

  Attributes:
    line: the Line object for the template directive
    sample: the example terminal output string from the template
  """

  def __init__(self, line, sample):
    self.line = line
    self.sample = sample
    self.ReportError = line.ReportError

  def InferSkip(self, start, finish):
    """Compute a regex that skips a fixed string.

    Compute a regex that skips a fixed string, but allow for the
    possibility that consecutive whitespace may grow or shrink.  The
    arguments should be interpreted as defining a slice.

    Args:
      start: beginning index of the string to skip.
      finish: end index beyond the string to skip.

    Returns:
      A regular expression that matches the specified string slice.
    """

    regex = ''
    for ch in re.sub(r'\s+', ' ', self.sample[start:finish]):
      regex += r'\s+' if ch == ' ' else re.escape(ch)

    # Verify that the inferred regular expression exactly matches the
    # given substring in the sample.  It is a program bug if the
    # inferred regex is malformed.  It is a program bug if the
    # inferred regex matches only a part of the given substring.  It
    # is a user error (bad marker alignment, most likely) if the
    # inferred regex matches beyond the end of the given substring.

    try:
      match = re.match(regex, self.sample[start:])
      assert match and match.end() >= finish-start, (
          self.line.WithIdentHeader(
              'skip pattern matches too few characters'))
      if match.end() > finish-start:
        self.ReportError('invalid boundary at column %d' % finish)
    except re.error:
      assert False, self.line.WithIdentHeader(
          'ill-formed regular expression')

    return regex


class Marker(object):
  """The marker directive.

  The Marker class represents marker directives in Ashier
  configuration files.  Each marker directive labels a specific part
  of a template as "variable" and optionally associates the variable
  part with a name or a matching regular expression (or both).

  Attributes:
    line: the Line object for the marker directive
    start: an integer pointing to the marker beginning position
    finish: an integer pointing to the marker end position
    name: the name to which the variable part is bound
  """

  def __init__(self, line, start, finish, name, regex):
    self.line = line
    self.start = start
    self.finish = finish
    self.name = name
    self._regex = utils.RemoveRegexBindingGroups(regex)
    self.ReportError = line.ReportError

  def InferRegex(self, template):
    """Infer a regular expression for a marker substring.

    Given a template object, infer a regular expression for the marked
    substring of the template sample string using simple heuristics.

    Args:
      template: a Template object containing the sample string.

    Returns:
      A regular expression that matches the marked substring, or an
      empty string if regular expression inference fails.
    """

    sample = template.sample
    assert self.finish <= len(sample), (
        'marker extends beyond template')

    if not self._regex:
      # A marker either extends to the end of template, in which case
      # it does not need to be delimited at the end...
      if len(sample) == self.finish:
        self._regex = '.+'

      # Or the marker needs to be delimited to separate it from the
      # remaining parts of the template, using the character (i.e.,
      # the delimiter) that follows the marked substring.
      elif len(sample) > self.finish:
        delimiter = sample[self.finish]

        # For the inferred regular expression to match the entire
        # marked substring, the delimiter character must not appear in
        # the marked substring itself.  If it does, report the problem
        # back to the user.
        if sample.count(delimiter, self.start, self.finish) == 0:

          # If the delimiter is a whitespace character, delimit the
          # regular expression with any whitespace character.  We want
          # to infer regular expressions that are flexible about
          # whitespace matching (especially since there is no
          # distinction betwen tabs and spaces in the template sample
          # due to tab expansion in the ParseDirective procedure).
          self._regex = '[^%s]+' % (
              r'\s' if delimiter.isspace() else delimiter,)
        else:
          self.ReportError('delimiter appears in the marker')

    # If self._regex is the empty string, an error had already been
    # reported to the user, and no further validation is necessary.
    if self._regex:

      # Verify that self._regex is well-formed and exactly matches the
      # marked substring.  We treat ill-formed regular expressions as
      # user error because the bad regular expressions are most likely
      # specified by the user (instead of inferred by this function).
      try:
        match = re.match(self._regex, sample[self.start:])
        if not match or match.end() != self.finish-self.start:
          self.ReportError('regex does not match marker')
      except re.error:
        self.ReportError('ill-formed regular expression')

    return self._regex


class Send(object):
  """The Send action directive.

  The Send class represents action directives in Ashier configuration
  files.  Each action directive requests Ashier to send a formatted
  string either to the controller process (channel "controller") or to
  the terminal (channel "terminal").

  Attributes:
    line: the Line object for the action directive
  """

  def __init__(self, line, channel, message):
    self.line = line
    self._channel = channel
    self._message = message
    self.ReportError = line.ReportError

    if channel not in ('controller', 'terminal'):
      self.ReportError('invalid channel name: %s' % (channel,))

  def References(self):
    """List variable references in the message.

    Returns:
      A set of variable names (without the leading '$') that are
      referenced in the message to be sent.
    """

    names = set()
    parts = re.split(r'(\$\w+)', self._message)
    for segment in parts:
      if segment.startswith('$'):
        names.add(segment[1:])
    return names

  def ExpandVariables(self, bindings):
    """Expand variables in the message.

    Args:
      bindings: a dictionary of variable bindings.

    Returns:
      The message to be sent, with variables of the form $var replaced
      by the strings they map to in the dictionary argument.
    """

    parts = re.split(r'(\$\w+)', self._message)
    for i in range(len(parts)):
      if parts[i].startswith('$'):
        name = parts[i][1:]
        parts[i] = bindings[name]
    return ''.join(parts)

  def Send(self, channels, bindings):
    """Send message as specified by Action directive.

    Args:
      channels: dictionary of channels to file descriptors.
      bindings: dictionary of bound names to strings.
    """

    try:
      os.write(channels[self._channel],
               self.ExpandVariables(bindings)+'\n')
    except OSError:
      # Silence all exceptions, which are most likely due to a
      # controller process that decides to exit early.
      pass
