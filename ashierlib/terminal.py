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

This module defines procedures for terminal interaction.
"""

__author__ = 'cklin@google.com (Chuan-kai Lin)'

import atexit
import errno
import fcntl
import os
import pty
import select
import signal
import sys
import termios
import tty


def SetTerminalRaw(fd, restore=False):
  """Set controlling terminal to raw mode.

  Set controlling terminal to raw mode and, if requested, register an
  exit handler to restore controlling terminal attribute on exit.

  Args:
    fd: file descriptor of the controlling terminal.
    restore: whether terminal mode should be restored on exit

  Returns:
    None.
  """

  if restore:
    when = termios.TCSAFLUSH
    orig_attr = termios.tcgetattr(fd)
    atexit.register(lambda: termios.tcsetattr(fd, when, orig_attr))
  tty.setraw(fd)


def MatchWindowSize(master, slave):
  """Keep window sizes of two terminals in sync.

  Copy window size information from one terminal to another and
  register a signal hander to update window size information on
  the second terminal when window size of the first changes.

  Args:
    master: file descriptor of the terminal to observe.
    slave: file descriptor of the terminal to update.

  Returns:
    None.
  """

  def _CopyWindowSize():
    window_size = fcntl.ioctl(master, termios.TIOCGWINSZ, '00000000')
    fcntl.ioctl(slave, termios.TIOCSWINSZ, window_size)
    signal.signal(signal.SIGWINCH, lambda s, f: _CopyWindowSize())

  _CopyWindowSize()


def SpawnPTY(argv):
  """Spawn a process and connect its controlling terminal to a PTY.

  Create a new PTY device and spawn a process with the controlling
  terminal of the child process set to the slave end of the new PTY.

  Args:
    argv: arguments (including executable name) for the child process.

  Returns:
    A pair containing the PID of the child process and the file
    descriptor for the master end of the new PTY device.
  """

  assert argv, 'SpawnPTY: argv is an empty list'

  (pid, fd) = pty.fork()
  if pid == 0:
    try:
      os.execvp(argv[0], argv)
    except OSError as err:
      print "# Error: cannot execute program '%s'" % argv[0]
      print '# %s\n%s' % (str(err), chr(4))
      sys.exit(1)
  return (pid, fd)


def CopyData(from_fd, to_fd, size=1024):
  """Copy data from one file descriptor to another.

  Copy no more than the specified amount of data from one file
  descriptor to another.

  Args:
    from_fd: file descriptor to read the data from.
    to_fd: file descriptor to write the data to.
    size: the maximum number of bytes to copy (default 1024).

  Returns:
    A string that contains the bytes read and copied.
  """

  data = os.read(from_fd, size)
  os.write(to_fd, data)
  return data


def AsyncIOLoop(dispatch_dict):
  """Dispatch asynchronous I/O events.

  Wait for data to become available for reading in a file descriptor
  and then invoke the corresponding event handler.

  Args:
    dispatch_dict: a dictionary that maps file descriptors to event
      handler functions (which take event mask as the only argument).

  Returns:
    None.
  """

  # Unlike poll, epoll handles closed file descriptors gracefully.
  po = select.epoll()
  for fd in dispatch_dict:
    po.register(fd, select.POLLIN)

  while True:
    try:
      for ready_fd, event in po.poll():
        dispatch_dict[ready_fd](event)
    except (IOError, select.error) as (err, _):
      if err != errno.EINTR:
        raise

