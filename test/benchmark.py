#!/usr/bin/env python

import sys, commands, os, re

user_system_match = re.compile(r'(\d+\.\d+)user (\d+\.\d+)system').search

for command in sys.stdin:
    comment = command.find('#')
    if comment != -1:
        command = command[:comment]
    command = command.strip()
    if command == '':
        continue
    status, output = commands.getstatusoutput('LC_ALL=POSIX time ' + command)
    if status:
        print output
        print >> sys.stderr, command, 'failed with exit code', status
        sys.exit(status)
    match = user_system_match(output)
    assert match is not None
    user = float(match.group(1))
    system = float(match.group(2))
    redirect = command.find('>')
    if redirect != -1:
        outfilename = command[redirect+1:].lstrip()
        filesize = os.stat(outfilename)[6]
        # sys.stdout.write('%.2f+%.2f=%.2f\t' % (user, system, user + system))
        # sys.stdout.write('%.2f %d\t' % (user, filesize))
        command = command[:redirect].rstrip()
        print '%.2f+%.2f %d %s' % (user, system, filesize, command)
    else:
        print '%.2f+%.2f %s' % (user, system, command)
