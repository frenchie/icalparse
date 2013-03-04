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
import cgi
import icalparse
#import cgitb; cgitb.enable()

form = cgi.FieldStorage()

if __name__ == '__main__':
	if "uid" not in form or "key" not in form:
		print('Content-Type: text/html\n')
		sys.exit(0)
	try:
		uid = int(form['uid'].value)
		key = int(form['key'].value)
	except:
		print('Content-Type: text/html\n')
		sys.exit(0)

	url = 'http://www.facebook.com/ical/u.php?uid=%s&key=%s'%(uid,key)
	(content, encoding) = icalparse.getHTTPContent(url)

	cal = vobject.readOne(unicode(content, encoding))
	cal = icalparse.applyRules(cal, icalparse.generateRules(), False)

	print('Content-Type: text/calendar; charset=%s\n'%encoding)
	icalparse.writeOutput(cal)
