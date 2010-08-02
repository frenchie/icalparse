#!/usr/bin/python
#
# Copyright (c) 2010 James French <frenchie@frenchie.id.au>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal# in the Software without restriction, including without limitation the rights
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

# This file describes a series of rules which will be called on an ics file as
# rule(key, value)

# Your functions are expected to return a (key, value) tuple or they will be
# treated as if they don't exist (ie, the line will go through unhindered).
# Returning any boolean false value other than a None will return the line from
# the final iCalendar file

# The doc string will be presented to the user when run as verbose, so
# please be polite

def markEventsPublic(key, value):
	'''Marking private events public'''
	# Required as google are strict about the CLASS:PRIVATE/CLASS:CONFIDENTIAL
	# lines and Facebook like to set them
	if key == 'CLASS': return (key, 'PUBLIC')
