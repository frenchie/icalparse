#!/usr/bin/env python
# vim: ts=4 sw=4 expandtab smarttab
#
# Copyright (c) 2013 James French <frenchie@frenchie.id.au>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys, os
import urllib.parse, urllib.request, urllib.error
import vobject
from cgi import parse_header
from types import FunctionType

debug = False

services = {}

services["outlook"] = { "url": "https://outlook.office365.com/owa/calendar/%s/%s/calendar.ics" }
services["google"] = { "url": "https://calendar.google.com/calendar/ical/%s/%s/basic.ics" }
services["facebook"] = { "url": "http://www.facebook.com/ical/u.php?uid=%s&key=%s" }

def getContent(url='',stdin=False):
    '''Generic URL opening function.

    WARNING: do not call this directly with user input from a CGI script
    as it will happily open file:// URLs. Escape user input or better still
    write a function that builds a sandboxed URL based on limited user input
    '''

    encoding = ''

    if stdin:
        content = sys.stdin.read()
        return (content, encoding)

    parsedURL = urllib.parse.urlparse(url)
    if not parsedURL[0]: url = 'file://' + os.path.abspath(url)

    try:
        res = urllib.request.urlopen(url)
        content = res.read()
        encoding = res.headers.get_content_charset()
        res.close()
    except (urllib.error.URLError, OSError) as e:
        sys.stderr.write('%s\n'%e)
    return (content, encoding)

def generateRules():
    '''Attempts to load a series of rules into a list. This function is smarter
    than the average bear and will ignore modules and functions imported into
    the rules file.
    '''

    try:
        import parserrules
    except ImportError:
        return []

    rules = [ getattr(parserrules, rule) for rule in dir(parserrules) ]
    rules = [ rule for rule in rules
        if type(rule) is FunctionType and rule.__module__ == "parserrules" ]

    return rules


def applyRules(cal, rules=[], verbose=False):
    '''Runs a series of rules on the lines in ical and mangles its output
    '''

    for rule in rules:
        cal = rule(cal)

    return cal


def writeOutput(cal, outfile=''):
    '''Takes a list of lines and outputs to the specified file
    '''

    if not cal:
        sys.stderr.write('Refusing to write out an empty file')
        sys.exit(0)

    if not outfile:
        out = sys.stdout
    else:
        try:
            out = open(outfile, 'w')
        except (IOError, OSError) as e:
            sys.stderr.write('%s\n'%e)
            sys.exit(1)

    cal.serialize(out)

    if not out == sys.stdout:
        out.close()


def runLocal():
    '''Main run function if this script is called locally
    '''

    from optparse import OptionParser

    parser = OptionParser('usage: %prog [options] url')
    parser.add_option('-s', '--service', action='store_true', dest='service',
        default=None, help='Specify a service to run rules against')
    parser.add_option('-i', '--stdin', action='store_true', dest='stdin',
        default=False, help='Take a calendar from standard input')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
        default=False, help='Be verbose when rules are being applied')
    parser.add_option('-o', '--output', dest='outfile', default='',
        help='Specify output file (defaults to standard output)')
    parser.add_option('-m','--encoding', dest='encoding', default='',
        help='Specify a different character encoding'
        '(ignored if the remote server also specifies one)')
    parser.add_option('-t','--timezone', dest='timezone', default='',
        help='Specify a timezone to use if the remote calendar doesn\'t '
        'set it properly')

    (options, args) = parser.parse_args()

    # Use stdin if requested, otherwise open a url
    if not args and not options.stdin:
        parser.print_usage()
        sys.exit(0)
    elif not options.stdin:
        url = args[0]
    else:
        url = ''

    (content, encoding) = getContent(url, options.stdin)
    encoding = encoding or options.encoding or 'utf-8'

    cal = vobject.readOne(str(content, encoding))
    cal = applyRules(cal, generateRules(), options.verbose)

    writeOutput(cal, options.outfile)


def exitQuiet(exitstate=0):
    '''When called as a CGI script, exit quietly if theres any errors
    '''

    print('Content-Type: text/calendar\n')
    sys.exit(exitstate)


def runCGI():
    '''Function called when run as a CGI script.
    '''

    import cgi
    if debug: import cgitb; cgitb.enable()

    form = cgi.FieldStorage()
    if "uid" not in form or "key" not in form:
        exitQuiet()

    if "service" in form:
        if not form["service"].value in services:
            exitQuiet()
        sn = form["service"].value
    else: sn = "outlook"

    service = services[sn]

    # More sanity required here
    uid = urllib.parse.quote(form["uid"].value)
    key = urllib.parse.quote(form["key"].value)

    url = service["url"]%(uid,key)

    # Okay, we're happy that the input is sane, lets serve up some data
    (content, encoding) = getContent(url)

    try:
        cal = vobject.readOne(str(content, encoding))
    except:
        print(('Content-Type: text/plain; charset=%s\n'%encoding))
        print(content.decode(encoding))
        sys.exit(0)

    cal = applyRules(cal, generateRules(), False)

    print(('Content-Type: text/calendar; charset=%s\n'%encoding))
    writeOutput(cal)

if __name__ == '__main__':

    # Detect if this script has been called by CGI and proceed accordingly
    if 'REQUEST_METHOD' in os.environ:
        runCGI()
    else:
        runLocal()
