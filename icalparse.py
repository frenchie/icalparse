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
import urlparse
import os


class InvalidICS(Exception): pass
class notJoined(Exception): pass
class IncompleteICS(InvalidICS): pass


def lineJoiner(oldcal):
	'''Takes a string containing a calendar and returns an array of its lines'''

	if not oldcal[0:15] == 'BEGIN:VCALENDAR':
		raise InvalidICS, "Does not appear to be a valid ICS file"

	if not 'END:VCALENDAR' in oldcal[-15:-1]:
		raise IncompleteICS, "File appears to be incomplete"

	if list(oldcal) == oldcal:
		oldcal = '\r\n'.join(oldcal)

	oldcal = oldcal.replace('\r\n ', '').replace('\r\n\t','')
	return oldcal.strip().split('\r\n')


def lineFolder(oldcal, length=75):
	'''Folds content lines to a specified length, returns a list'''

	if length > 75:
		sys.stderr.write('WARN: lines > 75 octets are not RFC compliant\n')

	cal = []
	sl = length - 1

	for line in oldcal:
		# Line fits inside length, do nothing
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


def getContent(url='',stdin=False):
	'''Generic content retriever, DO NOT use this function in a CGI script as
	it can read from the local disk (which you probably don't want it to).
	'''

	# Special case, if this is a HTTP url, return the data from it using
	# the HTTP functions which attempt to play a bit nicer.
	parsedURL = urlparse.urlparse(url)
	if 'http' in parsedURL[0]: return getHTTPContent(url)

	if stdin:
		content = sys.stdin.read()
		return content

	if not parsedURL[0]:
		try: content = open(os.path.abspath(url),'r').read()
		except (IOError, OSError), e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)
		return content

	# If we've survived, use python's generic URL opening library to handle it
	import urllib2
	try:
		res = urllib2.urlopen(url)
		content = res.read()
		res.close()
	except (urllib2.URLError, ValueError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)
	return content


def getHTTPContent(url='',cache='.httplib2-cache'):
	'''This function attempts to play nice when retrieving content from HTTP
	services. It's what you should use in a CGI script. It will (by default)
	slurp the first 20 bytes of the file and check that we are indeed looking
	at an ICS file before going for broke.'''

	try:
		import httplib2
	except ImportError:
		import urllib2

	if not url: return ''

	if 'httplib2' in sys.modules:
		try: h = httplib2.Http('.httplib2-cache')
		except OSError: h = httplib2.Http()
	else: h = False

	try:
		if h: content = h.request(url)[1]
		return content
	except ValueError, e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	try:
		content = urllib2.urlopen(url).read()
		return content
	except urllib2.URLError, e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	return ''

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

	content = getContent(url, options.stdin)
	cal = lineJoiner(content)
	print cal
