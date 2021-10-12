#!/usr/bin/python
# vim: ts=4 sw=4 expandtab smarttab
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

    if 'prodid' in cal.contents:
        if not "Facebook" in cal.prodid.value: return cal

    for event in cal.vevent_list:
        if 'organizer' not in event.contents: continue
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

    if 'prodid' in cal.contents:
        if cal.prodid.value not in [
            "Microsoft Exchange Server",
            "Facebook"
            ]:
            return cal

    for event in cal.vevent_list:
        if 'class' in event.contents:
            # Bit of a hack as class is a reserved word in python
            del event.contents['class']
            event.add('class').value = "PUBLIC"

    return cal

def utcise(cal):
    '''Facebook suck at timezones, remove them'''

    if 'prodid' in cal.contents:
        if not "Facebook" in cal.prodid.value: return cal

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
    '''Remove unwanted Facebook parameters'''

    if 'prodid' in cal.contents:
        if not "Facebook" in cal.prodid.value: return cal

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

def BusyTentativeOnly(cal):
    '''Ignore events which are listed as Free, Out of Office or Working Elsewhere'''

    if 'prodid' in cal.contents:
        if not "Microsoft Exchange Server" in cal.prodid.value: return cal

    oldEvents = cal.vevent_list
    del cal.vevent_list

    events = []

    for event in oldEvents:
        # This should never happen from an outlook calendar, but just in case
        if 'x-microsoft-cdo-busystatus' not in event.contents:
            events.append(event)
        if event.x_microsoft_cdo_busystatus.value in [ "BUSY", "TENTATIVE" ]:
            events.append(event)

    cal.vevent_list = events
    return cal

def stripGoogleReminders(cal):
    '''Outlook chokes on google's reminders'''

    if 'prodid' in cal.contents:
        if not "Google Calendar" in cal.prodid.value: return cal

    for event in cal.vevent_list:
        if 'valarm' in event.contents:
            del event.valarm_list

    return cal
