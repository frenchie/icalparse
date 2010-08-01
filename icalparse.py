#!/usr/bin/python
#
# Copyright (c) 2010 James French <frenchie@frenchie.id.au>
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

import sys
import re
import urlparse
import os
from optparse import OptionParser

class InvalidICS(Exception): pass
class notJoined(Exception): pass

# RFC5545 and RFC5546 iCalendar registries contain upper case letters
# and dashes only and are separated from the value by a colon (:)
icalEntry = re.compile('^[A-Z\-]+:.*')

def lineJoiner(oldcal):
	'''Unfolds a calendar so that items can be parsed'''

	cal = []

	# Strip newlines (
	for line in oldcal:
		line = line.rstrip('\r\n')

		# Reassemble broken Lines
		if not line:
			if not cal: continue
			else: cal[-1] += '\\n'
		elif line[0] == ' ':
			if not cal: raise InvalidICS, 'First line of ICS must be element'
			line = line[1:len(line)]
			cal[-1] += line
		elif not icalEntry.match(line):
			if not cal: raise InvalidICS, 'First line of ICS must be element'
			cal[-1] += '\\n' + line
		else:
			if cal: cal[-1] += '\r\n'
			cal.append(line)

	cal[-1] += '\r\n'

	return cal

def lineSplitter(oldcal, length=75):
	'''Folds content lines to a specified length, returns a list'''

	cal = []
	sl = length - 1

	for line in oldcal:
		# Line & line ending line ending fit inside length, do nothing
		if len(line.rstrip()) <= length:
			cal.append(line)
		else:
			brokenline = [line[0:length] + '\r\n']
			ll = length
			while ll < len(line.rstrip('\r\n')) + 1:
				brokenline.append(' ' + line[ll:sl+ll].rstrip('\r\n') + '\r\n')
				ll += sl
			cal += brokenline

	return cal

if __name__ == '__main__':
	# If the user passed us a 'stdin' argument, we'll go with that,
	# otherwise we'll try for a url opener

	parser = OptionParser('usage: %prog [options] url')
	parser.add_option('-s', '--stdin', action='store_true', dest='stdin',
		default=False, help='Take a calendar from standard input')
	parser.add_option('-o', '--output', dest='outfile', default='',
		help='Specify output file (defaults to standard output)')

	(options, args) = parser.parse_args()

	if not args and not options.stdin:
		parser.print_usage()
		sys.exit(0)

	url = args[0]

	# Work out what url parsers we're going to need based on what the user
	# gave us on the command line - we do like files after all
	parsedURL = urlparse.urlparse(url)
	http = 'http' in parsedURL[0]

	if not parsedURL[0]: u = False
	else: u = True

	if not options.stdin and http:
		try:
			import httplib2
		except ImportError:
			import urllib2

	# Try and play nice with HTTP servers unless something goes wrong. We don't
	# really care about this cache so it can be somewhere volatile
	h = False
	if 'httplib2' in sys.modules:
		try: h = httplib2.Http('.httplib2-cache')
		except OSError: h = httplib2.Http()

	if not options.stdin and (not http or not 'httplib2' in sys.modules):
		import urllib2

	try:
		content = u and (h and h.request(url)[1] or urllib2.urlopen(url).read())
	except (ValueError, urllib2.URLError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	if not u:
		try: content = open(os.path.abspath(url),'r').read()
		except (IOError, OSError), e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)

	# RFC5545 and RFC5546 Calendars should be generated UTF-8 and we need to
	# be able to read ANSI as well. This should take care of us.
	content = unicode(content, encoding='utf-8')
