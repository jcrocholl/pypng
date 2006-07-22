#!/usr/bin/env python

"""
Usage: benchmark.py < commands.sh

Benchmark some shell commands, print timing results and filesizes.

"""


__revision__ = '$Rev$'


import sys, commands, os, re


def strip_comment(line):
    """
    Remove comment from input line.
    """
    comment = line.find('#')
    if comment != -1:
        line = line[:comment]
    return line.strip()


variable_match = re.compile(r'(\w+)=(\S+|"(.+)")$').match
def set_variable(line, variables):
    """
    Set a variable (simulate shell environment).
    """
    match = variable_match(line)
    if match is None:
        return False
    varname, value, quoted = match.groups()
    if quoted:
        value = quoted
    variables[varname] = value
    return True


def expand_variables(line, variables):
    """
    Expand shell variables in command string.
    """
    for varname in variables:
        line = line.replace('$' + varname, variables[varname])
    return line


def split_outfile(line):
    """
    Split the output file from a command.
    """
    redirect = line.find('>')
    if redirect == -1:
        return line, None
    else:
        return line[:redirect].rstrip(), line[redirect+1:].lstrip()


def make_output_directory(outfile):
    """
    Make sure the output folder exists.
    """
    outdir = os.path.dirname(outfile)
    if outdir == '':
        return
    if os.path.exists(outdir):
        return
    os.makedirs(outdir)

user_system_match = re.compile(r'(\d+\.\d+)user (\d+\.\d+)system').search
def benchmark_command(line):
    """
    Run a command, return user and system times.
    """
    status, output = commands.getstatusoutput('LC_ALL=POSIX time ' + line)
    if status:
        print output
        print >> sys.stderr, line, 'failed with exit code', status
        sys.exit(status)
    match = user_system_match(output)
    assert match is not None
    user_time = float(match.group(1))
    system_time = float(match.group(2))
    return user_time, system_time


def process_file(infile):
    """
    Process commands from an input file.
    """
    variables = {}
    for line in infile:
        line = strip_comment(line)
        if line == '':
            continue
        if set_variable(line, variables):
            continue
        line = expand_variables(line, variables)
        command, outfile = split_outfile(line)
        make_output_directory(outfile)
        print '%.2f+%.2f' % benchmark_command(line),
        if outfile:
            print os.path.getsize(outfile),
        print command


if __name__ == '__main__':
    process_file(sys.stdin)
