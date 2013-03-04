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
import vobject
import icalparse
import re
import cgitb; cgitb.enable()

def exitQuiet(exitstate=0):
	print('Content-Type: text/html\n')
	sys.exit(exitstate)

if __name__ == '__main__':
	form = cgi.FieldStorage()
	if "uid" not in form or "key" not in form:
		print('Content-Type: text/html\n')
		sys.exit(0)
	try:
		# UID should be numeric, if it's not we have someone playing games
		uid = int(form['uid'].value)
	except:
		exitQuiet()

	# The user's key will be a 16 character string
	key = form['key'].value
	re.search('[&?]+', key) and exitQuiet()
	len(key) == 16 or exitQuiet()
	
	# Historically facebook has been notoriously bad at setting timzeones
	# in their stuff so this should be a user setting. If it is set in
	# their calendar it'll  be used otherwise if the user feeds crap or
	# nothing just assume they want Australia/Perth
	tz = ""
	if "tz" in form:
		from pytz import timezone
		try:
			timezone(form['tz'].value)
			tz = form['tz'].value
		except: pass
	
	ruleConfig = {}
	ruleConfig["defaultTZ"] = tz or "Australia/Perth"
				
	# Okay, we're happy that the input is sane, lets serve up some data
	url = 'http://www.facebook.com/ical/u.php?uid=%d&key=%s'%(uid,key)
	(content, encoding) = icalparse.getHTTPContent(url)

	cal = vobject.readOne(unicode(content, encoding))
	cal = icalparse.applyRules(cal, icalparse.generateRules(ruleConfig), False)

	print('Content-Type: text/html; charset=%s\n'%encoding)
	icalparse.writeOutput(cal)
