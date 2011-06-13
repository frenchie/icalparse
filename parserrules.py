#!/usr/bin/python

# Rules for tackling facebook and google calendar - I want visibility of the
# organiser... not useful Google!

import vobject

def facebookOrganiser(cal):
	'''Adds organiser details to the body of facebook calendars.'''

	if cal.contents.has_key(u'prodid'):
		if not "Facebook" in cal.prodid.value: return cal

	for event in cal.vevent_list:
		if not event.contents.has_key(u'organizer'): continue
		organizer = "Organised by: " + event.organizer.cn_param + " ("
		organizer += event.organizer.value.lstrip('MAILTO:') + ")\n\n"

		event.description.value = organizer + event.description.value

	return cal

def whatPrivacy(cal):
	'''Marks events public so google calendar doesn't have a sad about them.'''

	for event in cal.vevent_list:
		if event.contents.has_key(u'class'):
			del event.contents[u'class']
			# Bit of a hack as class is a reserved word in python
			event.add('class').value = "PUBLIC"

	return cal

def dropMSKeys(cal):
	'''Drops microsoft keys, good for outlook, just bandwidth when not.'''

	eventBlacklist = [x.lower() for x in [
		"X-ALT-DESC",
		"X-MICROSOFT-CDO-BUSYSTATUS",
		"X-MICROSOFT-CDO-IMPORTANCE",
		"X-MICROSOFT-DISALLOW-COUNTER",
		"X-MS-OLK-ALLOWEXTERNCHECK",
		"X-MS-OLK-AUTOSTARTCHECK",
		"X-MS-OLK-CONFTYPE",
		"X-MS-OLK-AUTOFILLLOCATION"
	]]

	vcalBlacklist = [x.lower() for x in [
	"X-CALEND",
	"X-CALSTART",
	"X-CLIPEND",
	"X-CLIPSTART",
	"X-MS-OLK-WKHRDAYS",
	"X-MS-OLK-WKHREND",
	"X-MS-OLK-WKHRSTART",
	"X-OWNER",
	"X-PRIMARY-CALENDAR",
	"X-PUBLISHED-TTL",
	"X-WR-CALDESC",
	"X-WR-CALNAME",
	"X-WR-RELCALID"
	]]

	for event in cal.vevent_list:
		for blacklist in eventBlacklist:
			if event.contents.has_key(blacklist): del event.contents[blacklist]

	for blacklist in vcalBlacklist:
		if cal.contents.has_key(blacklist): del cal.contents[blacklist]

	return cal
