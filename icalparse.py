#!/usr/bin/python
#
# Copyright (c) 2011 James French <frenchie@frenchie.id.au>
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
import vobject
from cgi import parse_header


def getContent(url='',stdin=False):
	'''Generic content retriever, DO NOT use this function in a CGI script as
	it can read from the local disk (which you probably don't want it to).
	'''

	encoding = '' # If we don't populate this, the script will assume UTF-8

	# Special case, if this is a HTTP url, return the data from it using
	# the HTTP functions which attempt to play a bit nicer.
	parsedURL = urlparse.urlparse(url)
	if 'http' in parsedURL[0]: return getHTTPContent(url)

	if stdin:
		content = sys.stdin.read()
		return (content, encoding)

	if not parsedURL[0]: url = 'file://' + os.path.abspath(url)

	# If we've survived, use python's generic URL opening library to handle it
	import urllib2
	try:
		res = urllib2.urlopen(url)
		content = res.read()
		ct = res.info().getplist()
		res.close()
	except (urllib2.URLError, OSError), e:
		sys.stderr.write('%s\n'%e)
		sys.exit(1)

	for param in ct:
		if 'charset' in param:
			encoding = param.split('=')[1]
			break

	return (content, encoding)


def getHTTPContent(url='',cache='.httplib2-cache'):
	'''This function attempts to play nice when retrieving content from HTTP
	services. It's what you should use in a CGI script.'''

	try:
		import httplib2
	except ImportError:
		import urllib2

	if not url: return ('','')

	if not 'http' in urlparse.urlparse(url)[0]: return ('','')

	if 'httplib2' in sys.modules:
		try: h = httplib2.Http('.httplib2-cache')
		except OSError: h = httplib2.Http()
	else: h = False

	if h:
		try:
			req = h.request(url)
		except ValueError, e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)

		resp, content = req
		if 'content-type' in resp:
			ct = 'Content-Type: %s'%req[0]['content-type']
			ct = parse_header(ct)
			if 'charset' in ct[1]: encoding = ct[1]['charset']
			else: encoding = ''
		else:
			ct = ''
			encoding = ''

	else:
		try:
			req = urllib2.urlopen(url)
		except urllib2.URLError, e:
			sys.stderr.write('%s\n'%e)
			sys.exit(1)

		content = req.read()
		ct = req.info().getplist()
		for param in ct:
			if 'charset' in param:
				encoding = param.split('=')[1]
				break

	return (content, encoding)


def generateRules(ruleConfig):
	'''Attempts to load a series of rules into a list'''
	try:
		import parserrules
	except ImportError:
		return []

	for conf in ruleConfig:
		parserrules.ruleConfig[conf] = ruleConfig[conf]

	rules = [getattr(parserrules, rule) for rule in dir(parserrules) if callable(getattr(parserrules, rule))]
	return rules


def applyRules(cal, rules=[], verbose=False):
	'Runs a series of rules on the lines in ical and mangles its output'

	for rule in rules:
		cal = rule(cal)

	return cal

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

	cal.serialize(out)

	if not out == sys.stdout:
		out.close()

if __name__ == '__main__':
	# Only load options parsing if this script was called directly, skip it
	# if it's being called as a module.
	from optparse import OptionParser

	parser = OptionParser('usage: %prog [options] url')
	parser.add_option('-s', '--stdin', action='store_true', dest='stdin',
		default=False, help='Take a calendar from standard input')
	parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
		default=False, help='Be verbose when rules are being applied')
	parser.add_option('-o', '--output', dest='outfile', default='',
		help='Specify output file (defaults to standard output)')
	parser.add_option('-m','--encoding', dest='encoding', default='',
		help='Specify a different character encoding'
		'(ignored if the remote server also specifies one)')
	parser.add_option('-t','--timezone', dest='timezone', default='Australia/Perth',
		help='Specify a timezone to use if the remote calendar doesn\'t set it properly')

	(options, args) = parser.parse_args()

	# Ensure the rules process using the desired timezone
	ruleConfig = {}
	ruleConfig["defaultTZ"] = options.timezone

	# If the user passed us a 'stdin' argument, we'll go with that,
	# otherwise we'll try for a url opener
	if not args and not options.stdin:
		parser.print_usage()
		sys.exit(0)
	elif not options.stdin:
		url = args[0]
	else:
		url = ''

	(content, encoding) = getContent(url, options.stdin)
	encoding = encoding or options.encoding or 'utf-8'

	cal = vobject.readOne(unicode(content, encoding))
	cal = applyRules(cal, generateRules(ruleConfig), options.verbose)

	writeOutput(cal, options.outfile)
