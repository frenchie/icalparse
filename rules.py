#!/usr/bin/python

# This file describes a series of rules which will be called on an ics file as
# rule(key, value)

# Your functions are expected to return a (key, value) tuple or they will be treated as
# if they don't exist (ie, the line will go through unhindered). Returning a value which
# is boolean False will remove the offending line from the final  ICS. The easiest way
# to pass a line back without changing it is to return True.

# The doc string will be presented to the user when run as verbose, so please be polite

def markEventsPublic(key, value):
	'''Marking private events public'''
	# Required as google are strict about the CLASS:PRIVATE/CLASS:CONFIDENTIAL lines
	if key == 'CLASS':
		return (key, 'PUBLIC')
	return True
