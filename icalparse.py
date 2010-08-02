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
	return [unicode(x, 'utf-8') for x in oldcal.strip().split('\r\n')]


def lineFolder(oldcal, length=75):
	'''Folds content lines to a specified length, returns a list'''

	if length > 75:
		sys.stderr.write('WARN: lines > 75 octets are not RFC compliant\n')

	cal = []
	sl = length - 1

	for line in oldcal:
		line = line.encode('utf-8')
		# Line fits inside length, do nothing
		if len(line.rstrip()) <= length:
			cal.append(line)
		else:
			brokenline = [line[0:length]]
			ll = length
			while ll < len(line) + 1:
				brokenline.append(line[ll:sl+ll])
				ll += sl
			brokenline = '\r\n '.join(brokenline)
			cal.append(brokenline)

	return cal


def splitFields(cal):
	'''Takes a list of lines in a calendar file and returns a list of tuples	
	as (key, value) pairs'''

	ical = [tuple(x.split(':',1)) for x in cal]

	# Check that we got 2 items on every line
	for line in ical:
		if not len(line) == 2:
			raise InvalidICS, "Didn't find a content key on: %s"%(line)

	return ical


def joinFields(ical):
	'''Takes a list of tuples that make up a calendar file and returns it to a
	list of lines'''

	return [':'.join(x) for x in ical]


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
	except (urllib2.URLError, OSError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)
	return content


def getHTTPContent(url='',cache='.httplib2-cache'):
	'''This function attempts to play nice when retrieving content from HTTP
	services. It's what you should use in a CGI script.'''

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
	except (urllib2.URLError, OSError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	return ''


def generateRules():
	'''Attempts to load a series of rules into a list'''
	try:
		import parserrules
	except ImportError:
		return []

	rules = [getattr(parserrules, rule) for rule in dir(parserrules) if callable(getattr(parserrules, rule))]
	return rules


def applyRules(ical, rules=[], verbose=False):
	'Runs a series of rules on the lines in ical and mangles its output'

	for rule in rules:
		output = []
		if rule.__doc__ and verbose:
			print(rule.__doc__)
		for line in ical:
			try:
				out = rule(line[0],line[1])
			except TypeError, e:
				output.append(line)
				print(e)
				continue

			# Drop lines that are boolean False
			if not out and not out == None: continue

			# If the rule did something and is a tuple or a list we'll accept it
			# otherwise, pay no attention to the man behind the curtain
			try:
				if tuple(out) == out or list(out) == out and len(out) == 2:
					output.append(tuple(out))
				else:
					output.append(line)
			except TypeError, e:
				output.append(line)

		ical = output

	return ical


def writeOutput(cal, outfile=''):
	'''Takes a list of lines and outputs to the specified file'''

	if not cal:
		sys.stderr.write('Refusing to write out an empty file')
		sys.exit(0)

	if not outfile:
		out = sys.stdout
	else:
		try:
			out = open(outfile, 'w')
		except (IOError, OSError), e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)

	if cal[-1]: cal.append('')

	out.write('\r\n'.join(cal))

	if not out == sys.stdout:
		out.close()


if __name__ == '__main__':
	from optparse import OptionParser
	# If the user passed us a 'stdin' argument, we'll go with that,
	# otherwise we'll try for a url opener

	parser = OptionParser('usage: %prog [options] url')
	parser.add_option('-s', '--stdin', action='store_true', dest='stdin',
		default=False, help='Take a calendar from standard input')
	parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
		default=False, help='Be verbose when rules are being applied')
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
	ical = applyRules(splitFields(cal), generateRules(), options.verbose)
	output = lineFolder(joinFields(ical))
	writeOutput(output, options.outfile)
