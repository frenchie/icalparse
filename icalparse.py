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

class InvalidICS(Exception): pass
class notJoined(Exception): pass

# RFC5545 and RFC5546 iCalendar registries contain upper case letters
# and dashes only and are separated from the value by a colon (:)
icalEntry = re.compile('^[A-Z\-]+:.*')

def lineJoiner(oldcal):
	'''Takes a string containing a calendar and returns an array of its lines'''

	if list(oldcal) == oldcal:
		oldcal = '\r\n'.join(oldcal)

	# RFC2445 This sequence defines a content 'fold' and needs to be stripped
	# from the output before writing the file
	oldcal.replace('\r\n ', '')
	return oldcal.split('\r\n')


def lineFolder(oldcal, length=75):
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
	from optparse import OptionParser
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
	elif not options.stdin:
		url = args[0]
	else:
		url = ''

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
	# really care about this cache (A lot of ics files seem to be generated with
	# php which hates caching with a passion).
	h = False
	if 'httplib2' in sys.modules:
		try: h = httplib2.Http('.httplib2-cache')
		except OSError: h = httplib2.Http()

	# Load urllib2 if this is not a stdin
	if not options.stdin and (not http or not 'httplib2' in sys.modules):
		import urllib2

	try:
		content = u and (h and h.request(url)[1] or urllib2.urlopen(url).read())
	except (ValueError, urllib2.URLError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	if not u and not options.stdin:
		try: content = open(os.path.abspath(url),'r').read()
		except (IOError, OSError), e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)

	if options.stdin:
		content = sys.stdin.read()

	# RFC5545 and RFC5546 New calendars should be generated UTF-8 and we need to
	# be able to read ANSI as well. This should take care of us.
	content = unicode(content, encoding='utf-8')

	#return content
