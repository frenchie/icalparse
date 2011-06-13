#!/usr/bin/python

# Rules for tackling facebook and google calendar - I want visibility of the
# organiser... not useful Google!

import vobject
import sys

def facebookOrganiser(ics):
	'''Adds organiser details to the body of facebook calendars.'''

	cal = vobject.readOne(ics)

	if cal.contents.has_key('PRODID'):
		if not "Facebook" in cal.contents.prodid.value: return ics

	for event in cal.vevent_list:
		if not event.contents.has_key(u'organizer'): continue
		organizer = "Organised by: " + event.organizer.cn_param + " ("
		organizer += event.organizer.value.lstrip('MAILTO:') + ")\n\n"

		event.description.value = organizer + event.description.value

	return cal.serialize()

runRules = [facebookOrganiser]
