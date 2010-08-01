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

	parser = OptionParser()
	parser.add_option('-s', '--stdin', action='store_true', dest='stdin',
		default=False, help='Take a calendar from standard input')
	parser.add_option('-o', '--output', dest='outfile', default='',
		help='Specify output file (defaults to standard output)')

	(options, args) = parser.parse_args()

	if not options.stdin:
		try:
			import httplib2
			urllib = False
		except ImportError:
			try:
				import urllib
				urllib = True
			except ImportError:
				sys.stderr.write('Failed to find a suitable http downloader\n')
				raise

