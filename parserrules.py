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

# This file describes a series of rules which must handle a vobject object and
# return it to the calling script

# The doc string will be presented to the user when run as verbose, so
# please be polite

import vobject

ruleConfig = {}
ruleConfig["defaultTZ"] = "UTC"

def facebookOrganiser(cal):
	'''Adds organiser details to the body of facebook calendars.'''

	if cal.contents.has_key(u'prodid'):
		if not "Facebook" in cal.prodid.value: return cal

	for event in cal.vevent_list:
		if not event.contents.has_key(u'organizer'): continue
		try:
			a = event.organizer.cn_paramlist
			organizer = "Organised by: " + event.organizer.cn_param + " ("
			organizer += event.organizer.value.lstrip('MAILTO:') + ")\n\n"
			event.description.value = organizer + event.description.value
		except AttributeError:
			organizer = "Organized by: " + event.organizer.value
			event.description.value = organizer + "\n\n" + event.description.value
	return cal

def whatPrivacy(cal):
	'''Marks events public so google calendar doesn't have a sad about them.'''

	for event in cal.vevent_list:
		if event.contents.has_key(u'class'):
			# Bit of a hack as class is a reserved word in python
			del event.contents[u'class']
			event.add('class').value = "PUBLIC"

	return cal

def dropAttributes(cal):
	'''Removing unwanted metadata'''

	eventBlacklist = [x.lower() for x in [
		"X-ALT-DESC",
		"X-MICROSOFT-CDO-BUSYSTATUS",
		"X-MICROSOFT-CDO-IMPORTANCE",
		"X-MICROSOFT-DISALLOW-COUNTER",
		"X-MS-OLK-ALLOWEXTERNCHECK",
		"X-MS-OLK-AUTOSTARTCHECK",
		"X-MS-OLK-CONFTYPE",
		"X-MS-OLK-AUTOFILLLOCATION",
		"TRANSP",
		"SEQUENCE",
		"PRIORITY"
	]]

	mainBlacklist = [x.lower() for x in [
		"X-CLIPSTART",
		"X-CALSTART",
		"X-OWNER",
		"X-MS-OLK-WKHRSTART",
		"X-MS-OLK-WKHREND",
		"X-WR-RELCALID",
		"X-MS-OLK-WKHRDAYS",
		"X-MS-OLK-APPTSEQTIME",
		"X-CLIPEND",
		"X-CALEND",
		"VTIMEZONE",
		"X-PRIMARY-CALENDAR"
	]]

	for event in cal.vevent_list:
		for blacklist in eventBlacklist:
			if event.contents.has_key(blacklist): del event.contents[blacklist]

	for blkl in mainBlacklist:
		while blkl in cal.contents: del cal.contents[blkl]

	return cal

def exDate(cal):
	'''Replacing multi-value EXDATES with multiple single-value EXDATES'''

	from datetime import datetime
	from pytz import timezone

	default = timezone(ruleConfig["defaultTZ"])

	for event in cal.vevent_list:
		if not event.contents.has_key(u'exdate'): continue
		dates = event.exdate.value

		del event.contents[u'exdate']

		for date in dates:
			if isinstance(date, datetime):
				if date.tzinfo is None: date = date.replace(tzinfo = default)
				date = date.astimezone(vobject.icalendar.utc)
			entry = event.add(u'exdate')
			entry.value = [date]

	return cal

def utcise(cal):
	'''Removing local timezones in favour of UTC. If the remote calendar specifies a timezone
	then use it, otherwise assume it's in the user-specified or default values'''

	from datetime import datetime
	from pytz import timezone

	default = timezone(ruleConfig["defaultTZ"])

	for event in cal.vevent_list:
		dtstart = getattr(event, 'dtstart', None)
		dtend = getattr(event, 'dtend', None)

		for i in (dtstart, dtend):
			if not i: continue
			dt = i.value
			if isinstance(dt, datetime):
				if dt.tzinfo is None: dt = dt.replace(tzinfo = default)
				i.value = dt.astimezone(vobject.icalendar.utc)

	return cal

def unwantedParams(cal):
	'''Removing unwanted parameters'''

	blklist = [
		"LANGUAGE",
		"X-VOBJ-ORIGINAL-TZID",
		"TZID"
	]

	for event in cal.vevent_list:
		for attr in event.contents:
			attr = getattr(event, attr)
			try:
				for i in blklist:
					while i in attr.params: del attr.params[i]
			except AttributeError: continue

	return cal

def exDate(cal):
	'''Changes multi-EXDATE into singles (apple can't obey even simple specs).
	If the remote calendar specifies a timezone then use it, otherwise use the user specified value'''

	for event in cal.vevent_list:
		if not event.contents.has_key(u'exdate'): continue
		dates = event.exdate.value
		try: tzid = event.exdate.tzid_param
		except AttributeError: tzid = ''

		del event.contents[u'exdate']

		for date in dates:
			entry = event.add(u'exdate')
			entry.value = [date]
			if tzid: entry.tzid_param = tzid

	return cal
