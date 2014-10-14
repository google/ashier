# Ashier for Automating Terminal Interactions

Ashier is a program that serves the same purpose as
[expect](http://expect.sourceforge.net/): helping users script terminal
interactions.  It is a computer assistant that watches the terminal screen over
your shoulder and interacts with the terminal using its own keyboard; someone
to answer the boring questions and enter the tedious commands for you.  Unlike
expect, Ashier supports multiple programming languages and provides a readable
template language for terminal output matching.  These features make it easier
to create and to maintain scripted terminal interactions.

Ashier is not an official Google product.

## Example: wargames

`wargames` is a program that asks you to play a game and then tells you that
the only winning move is not to play.  This example shows how you can make
Ashier refuse `wargames` automatically.

First, create a file `wargames.ahr` with the following contents.  The first
line, which starts with `>`, is a template that tells Ashier what to look for
on the terminal.  Here, it tells Ashier to look for a line that starts with the
sentence "Would you like to play a game?".  The second line, which starts with
`!terminal`, tells Ashier how to react when it matches terminal output to the
template.  Here, it tells Ashier to type `no` into the terminal and press
`ENTER`.

    >Would you like to play a game?
    !terminal "no"

Then, enter the following command to run Ashier, which starts a new interactive
shell.  The `-c` option points Ashier to the configuration file you just
created.

    ashier -c wargames.ahr

When you run `/usr/games/wargames` in this shell, Ashier automatically answers
"no" to the "Would you like to play a game?" prompt.

To stop Ashier, type `exit` in the interactive shell.

## Example: ping

`ping` is a program that sends network packets to a remote host and reports the
responses.  It has a command line option to send a specific number of packets,
but no option to continue sending packets until it receives, say, 10 responses.
This example shows how you can implement that feature with Ashier.

This `ping` example differs from the `wargames` example in two ways.  First,
`wargames` has a fixed prompt, but `ping` responses vary in reported packet
size, source, sequence number, Time-to-Live value, and latency.  So Ashier
needs to match only some parts of the template and ignore differences in
others.  Second, `wargames` takes only a fixed `no` response, but here Ashier
needs to react differently to `ping` responses: do nothing for the first 9, and
press `Ctrl-C` for the 10th.  In other words, Ashier needs to support dynamic
behavior through custom stateful logic.

Ashier solves the first problem with variable markers, which appear on lines
2-6 in the `ping-output.ahr` configuration file (shown below).  Each variable
marker line starts with `?`, followed by an optional sequence of `SPACE`
characters, and then a sequence of `.` dots.  The dots on each variable marker
line marks the corresponding part of the template as a variable, which tells
Ashier to ignore differences there when matching terminal output with the
template.  Each variable marker can also have a name, which appears after the
dots.

    >64 bytes from slashdot.org (216.34.181.45): icmp_seq=3 ttl=230 time=94.4 ms
    ?..
    ?              ............................
    ?                                                     . seq
    ?                                                           ... ttl
    ?                                                                    .... time
    !controller "REPLY $seq $ttl $time"

Ashier solves the second problem with a controller process.  When Ashier
starts, it in turn starts another program in the background.  That running
program is the controller process, which implements dynamic behavior for
Ashier.  Ashier talks to the controller process by sending messages to its
standard input.  In return, the controller process may send data to standard
output, which Ashier forwards verbatim to the terminal as keystrokes.

Here, the last line of `ping-output.ahr` (above) tells Ashier to send a message
to the controller process (instead of typing into the terminal) when it matches
terminal output to the template.  The controller program `ping-react.py` (shown
below) reads these messages and dynamically generates keystrokes.  Since Ashier
starts with a new interactive shell, the controller process first enters a
shell command to run the `ping` program.  Then, it reads 10 Ashier messages
(each representing a `ping` response) from standard input and logs each message
to the output file.  After receiving all 10 messages, it sends the `Ctrl-C` key
combination to standard output, which terminates `ping` and drops the terminal
back to the interactive shell.  Finally, it enters the `exit` command to quit
the interactive shell and stop Ashier.

    #!/usr/bin/python
    
    import sys
    
    print '/bin/ping %s' % sys.argv[1]  # Run ping from the interactive shell
    
    with open(sys.argv[2], 'w') as output:  # Open output file for writing
      responses = 0
      while responses < 10:            # Loop until 10 responses
        line = sys.stdin.readline()    # Read Ashier controller message
        if line.startswith('REPLY '):  # Check message label
          output.write(line[6:])       # Write response statistics to file
          responses += 1               # Increment response count
    
    sys.stdout.write(chr(3))  # Terminate ping with Ctrl-C
    print 'exit'              # Quit the interactive shell

You can now enter the following command to run Ashier, which starts a new
interactive shell.  The `-c` option points Ashier to its configuration file,
and the remaining arguments specify the controller program `ping-react.py` and
its arguments.

    ashier -c ping-output.ahr ./ping-react.py google.com output.txt

In the new shell, Ashier automatically runs `ping` and writes the statistics of
each response to `output.txt`.  When it counts 10 responses, it terminates
`ping` with `Ctrl-C` and types `exit` to quit the new interactive shell.
