#!/usr/bin/env python3

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

import vobject

import icalparse
import parserrules


# ---------------------------------------------------------------------------
# ICS fixtures
# ---------------------------------------------------------------------------

MINIMAL_ICS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Test
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:minimal@test.com
END:VEVENT
END:VCALENDAR
"""

# Facebook fixtures
# Note: BusyTentativeOnly and whatPrivacy check for "Microsoft Exchange Server",
# not just "Microsoft". Use a prodid that contains the exact required substring.

FACEBOOK_ICS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:Birthday Party
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:fb-1@facebook.com
ORGANIZER;CN=Organizer:MAILTO:organizer@example.com
DESCRIPTION:Come celebrate!
END:VEVENT
END:VCALENDAR
"""

FACEBOOK_ICS_NO_CN = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:Party
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:fb-2@facebook.com
ORGANIZER:MAILTO:bob@example.com
DESCRIPTION:Party time
END:VEVENT
END:VCALENDAR
"""

FACEBOOK_ICS_WITH_CLASS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:Private Event
CLASS:PRIVATE
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:fb-3@facebook.com
END:VEVENT
END:VCALENDAR
"""

FACEBOOK_ICS_NAIVE_TZ = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:Naive Event
DTSTART:20240101T100000
DTEND:20240101T110000
UID:naive@facebook.com
END:VEVENT
END:VCALENDAR
"""

FACEBOOK_ICS_WITH_PARAMS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY;LANGUAGE=en:Test Event
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:params@facebook.com
END:VEVENT
END:VCALENDAR
"""

# Exchange fixtures — prodid must contain "Microsoft Exchange Server" for
# BusyTentativeOnly and whatPrivacy to activate.

EXCHANGE_ICS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Microsoft Corporation//Microsoft Exchange Server 2016//EN
BEGIN:VEVENT
SUMMARY:Busy Meeting
X-MICROSOFT-CDO-BUSYSTATUS:BUSY
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:busy@outlook.com
END:VEVENT
BEGIN:VEVENT
SUMMARY:Free Time
X-MICROSOFT-CDO-BUSYSTATUS:FREE
DTSTART:20240101T120000Z
DTEND:20240101T130000Z
UID:free@outlook.com
END:VEVENT
BEGIN:VEVENT
SUMMARY:Out of Office
X-MICROSOFT-CDO-BUSYSTATUS:OOF
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
UID:oof@outlook.com
END:VEVENT
BEGIN:VEVENT
SUMMARY:Tentative
X-MICROSOFT-CDO-BUSYSTATUS:TENTATIVE
DTSTART:20240101T160000Z
DTEND:20240101T170000Z
UID:tentative@outlook.com
END:VEVENT
END:VCALENDAR
"""

EXCHANGE_ICS_NO_STATUS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Microsoft Corporation//Microsoft Exchange Server 2016//EN
BEGIN:VEVENT
SUMMARY:No Status
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:nostatus@outlook.com
END:VEVENT
END:VCALENDAR
"""

EXCHANGE_ICS_WITH_CLASS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Microsoft Corporation//Microsoft Exchange Server 2016//EN
BEGIN:VEVENT
SUMMARY:Private
CLASS:PRIVATE
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:exchange-private@test.com
END:VEVENT
END:VCALENDAR
"""

# Google fixtures

GOOGLE_ICS_WITH_ALARM = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
SUMMARY:Google Event
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:google@gmail.com
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Reminder
TRIGGER:-PT10M
END:VALARM
END:VEVENT
END:VCALENDAR
"""

GOOGLE_ICS_WITH_APPLE_PROPS = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
SUMMARY:Google Event
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:google2@gmail.com
X-APPLE-TRAVEL-ADVISORY-BEHAVIOR:AUTOMATIC
X-APPLE-STRUCTURED-LOCATION:blah
END:VEVENT
END:VCALENDAR
"""


# ---------------------------------------------------------------------------
# icalparse tests
# ---------------------------------------------------------------------------

class TestGetContent(unittest.TestCase):

    def _mock_response(self, data=b'data', charset='utf-8'):
        res = MagicMock()
        res.read.return_value = data
        res.headers.get_content_charset.return_value = charset
        return res

    def test_stdin_returns_content_and_empty_encoding(self):
        with patch('sys.stdin', io.StringIO('calendar data')):
            content, encoding = icalparse.getContent(stdin=True)
        self.assertEqual(content, 'calendar data')
        self.assertEqual(encoding, '')

    def test_url_fetch_returns_bytes_and_encoding(self):
        with patch('urllib.request.urlopen', return_value=self._mock_response()) as mock_open:
            content, encoding = icalparse.getContent('https://example.com/cal.ics')
        mock_open.assert_called_once_with('https://example.com/cal.ics', timeout=30)
        self.assertEqual(content, b'data')
        self.assertEqual(encoding, 'utf-8')

    def test_url_fetch_uses_10mb_size_cap(self):
        res = self._mock_response()
        with patch('urllib.request.urlopen', return_value=res):
            icalparse.getContent('https://example.com/cal.ics')
        res.read.assert_called_once_with(10 * 1024 * 1024)

    def test_url_fetch_uses_30s_timeout(self):
        with patch('urllib.request.urlopen', return_value=self._mock_response()) as mock_open:
            icalparse.getContent('https://example.com/cal.ics')
        _, kwargs = mock_open.call_args
        self.assertEqual(mock_open.call_args[1].get('timeout') or mock_open.call_args[0][1], 30)

    def test_fetch_error_returns_empty_bytes(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('refused')):
            with patch('sys.stderr', new_callable=io.StringIO):
                content, encoding = icalparse.getContent('https://example.com/cal.ics')
        self.assertEqual(content, b'')

    def test_server_omits_charset_returns_none_encoding(self):
        res = self._mock_response(charset=None)
        with patch('urllib.request.urlopen', return_value=res):
            _, encoding = icalparse.getContent('https://example.com/cal.ics')
        self.assertIsNone(encoding)

    def test_bare_path_prepends_file_scheme(self):
        res = self._mock_response(data=b'', charset=None)
        with patch('urllib.request.urlopen', return_value=res) as mock_open:
            icalparse.getContent('somefile.ics')
        called_url = mock_open.call_args[0][0]
        self.assertTrue(called_url.startswith('file://'))


class TestGenerateRules(unittest.TestCase):

    def test_returns_list_of_callables(self):
        rules = icalparse.generateRules()
        self.assertIsInstance(rules, list)
        for rule in rules:
            self.assertTrue(callable(rule))

    def test_all_rules_originate_from_parserrules(self):
        for rule in icalparse.generateRules():
            self.assertEqual(rule.__module__, 'parserrules')

    def test_known_rules_all_present(self):
        names = {r.__name__ for r in icalparse.generateRules()}
        expected = {
            'facebookOrganiser', 'whatPrivacy', 'utcise', 'unwantedParams',
            'BusyTentativeOnly', 'stripGoogleReminders', 'stripGoogleAppleExtensions',
        }
        self.assertEqual(names, expected)

    def test_returns_empty_list_when_module_unavailable(self):
        with patch.dict(sys.modules, {'parserrules': None}):
            rules = icalparse.generateRules()
        self.assertEqual(rules, [])


class TestApplyRules(unittest.TestCase):

    def test_no_rules_returns_cal_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        result = icalparse.applyRules(cal, [])
        self.assertIs(result, cal)

    def test_none_rules_defaults_to_empty(self):
        cal = vobject.readOne(MINIMAL_ICS)
        result = icalparse.applyRules(cal)
        self.assertIs(result, cal)

    def test_rules_applied_in_order(self):
        order = []
        def rule_a(cal):
            order.append('a')
            return cal
        def rule_b(cal):
            order.append('b')
            return cal
        icalparse.applyRules(vobject.readOne(MINIMAL_ICS), [rule_a, rule_b])
        self.assertEqual(order, ['a', 'b'])

    def test_return_value_chained_between_rules(self):
        sentinel = object()
        received = []
        def rule_a(cal):
            return sentinel
        def rule_b(cal):
            received.append(cal)
            return cal
        icalparse.applyRules(vobject.readOne(MINIMAL_ICS), [rule_a, rule_b])
        self.assertIs(received[0], sentinel)

    def test_verbose_logs_rule_docstring(self):
        def my_rule(cal):
            '''Does the thing'''
            return cal
        with patch('sys.stderr', new_callable=io.StringIO) as err:
            icalparse.applyRules(vobject.readOne(MINIMAL_ICS), [my_rule], verbose=True)
        self.assertIn('Does the thing', err.getvalue())

    def test_verbose_falls_back_to_function_name(self):
        def unnamed_rule(cal):
            return cal
        with patch('sys.stderr', new_callable=io.StringIO) as err:
            icalparse.applyRules(vobject.readOne(MINIMAL_ICS), [unnamed_rule], verbose=True)
        self.assertIn('unnamed_rule', err.getvalue())


class TestWriteOutput(unittest.TestCase):

    def test_none_cal_exits(self):
        with patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                icalparse.writeOutput(None)

    def test_writes_vcalendar_to_stdout(self):
        cal = vobject.readOne(MINIMAL_ICS)
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            icalparse.writeOutput(cal)
        self.assertIn('BEGIN:VCALENDAR', captured.getvalue())


class TestRunCGI(unittest.TestCase):

    def _run_cgi(self, env, post_body=None):
        """Run runCGI() with patched environment and capture stdout."""
        captured = io.StringIO()
        try:
            with patch.dict(os.environ, env):
                stdin = io.StringIO(post_body or '')
                with patch('sys.stdin', stdin):
                    with patch('sys.stdout', captured):
                        icalparse.runCGI()
        except SystemExit:
            pass
        return captured.getvalue()

    def _mock_calendar_response(self, ics=MINIMAL_ICS, charset='utf-8'):
        res = MagicMock()
        res.read.return_value = ics.encode(charset)
        res.headers.get_content_charset.return_value = charset
        return res

    # --- Input validation ---

    def test_missing_uid_exits_with_content_type(self):
        out = self._run_cgi({'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'key=abc&service=google'})
        self.assertIn('Content-Type: text/calendar', out)

    def test_missing_key_exits_with_content_type(self):
        out = self._run_cgi({'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=abc&service=google'})
        self.assertIn('Content-Type: text/calendar', out)

    def test_unknown_service_exits(self):
        out = self._run_cgi({'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=a&key=b&service=badservice'})
        self.assertIn('Content-Type: text/calendar', out)

    # --- Valid requests ---

    def test_valid_get_returns_calendar(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=myuid&key=mykey&service=google'}
        with patch('urllib.request.urlopen', return_value=self._mock_calendar_response()):
            out = self._run_cgi(env)
        self.assertIn('Content-Type: text/calendar', out)
        self.assertIn('BEGIN:VCALENDAR', out)

    def test_valid_post_returns_calendar(self):
        body = 'uid=myuid&key=mykey&service=google'
        env = {'REQUEST_METHOD': 'POST', 'CONTENT_LENGTH': str(len(body))}
        with patch('urllib.request.urlopen', return_value=self._mock_calendar_response()):
            out = self._run_cgi(env, post_body=body)
        self.assertIn('Content-Type: text/calendar', out)

    def test_default_service_is_facebook(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=myuid&key=mykey'}
        with patch('urllib.request.urlopen', return_value=self._mock_calendar_response()) as mock_open:
            self._run_cgi(env)
        self.assertIn('facebook.com', mock_open.call_args[0][0])

    # --- Security: input sanitisation ---

    def test_slash_in_uid_is_percent_encoded(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=foo/bar&key=mykey&service=google'}
        with patch('urllib.request.urlopen', return_value=self._mock_calendar_response()) as mock_open:
            self._run_cgi(env)
        called_url = mock_open.call_args[0][0]
        self.assertIn('%2F', called_url)
        self.assertNotIn('foo/bar', called_url)

    def test_slash_in_key_is_percent_encoded(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=myuid&key=my/key&service=google'}
        with patch('urllib.request.urlopen', return_value=self._mock_calendar_response()) as mock_open:
            self._run_cgi(env)
        called_url = mock_open.call_args[0][0]
        self.assertIn('%2F', called_url)
        self.assertNotIn('my/key', called_url)

    def test_post_size_capped_at_64k(self):
        env = {'REQUEST_METHOD': 'POST', 'CONTENT_LENGTH': str(100 * 1024 * 1024)}
        fake_stdin = MagicMock()
        fake_stdin.read.return_value = ''
        with patch('sys.stdin', fake_stdin):
            with patch.dict(os.environ, env):
                with patch('sys.stdout', io.StringIO()):
                    try:
                        icalparse.runCGI()
                    except (SystemExit, Exception):
                        pass
        fake_stdin.read.assert_called_once_with(65536)

    def test_invalid_content_length_is_treated_as_zero(self):
        env = {'REQUEST_METHOD': 'POST', 'CONTENT_LENGTH': 'notanumber'}
        out = self._run_cgi(env, post_body='')
        self.assertIn('Content-Type: text/calendar', out)

    # --- Security: header injection via encoding ---

    def test_crlf_in_server_charset_not_reflected_in_headers(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=u&key=k&service=google'}
        res = MagicMock()
        res.read.return_value = MINIMAL_ICS.encode('utf-8')
        res.headers.get_content_charset.return_value = 'utf-8\r\nX-Injected: evil'
        with patch('urllib.request.urlopen', return_value=res):
            out = self._run_cgi(env)
        self.assertNotIn('X-Injected', out)

    def test_server_omitting_charset_defaults_to_utf8(self):
        env = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'uid=u&key=k&service=google'}
        res = MagicMock()
        res.read.return_value = MINIMAL_ICS.encode('utf-8')
        res.headers.get_content_charset.return_value = None
        with patch('urllib.request.urlopen', return_value=res):
            out = self._run_cgi(env)
        self.assertIn('utf-8', out)
        self.assertIn('BEGIN:VCALENDAR', out)


# ---------------------------------------------------------------------------
# parserrules tests
# ---------------------------------------------------------------------------

class TestFacebookOrganiser(unittest.TestCase):

    def test_non_facebook_calendar_not_modified(self):
        cal = vobject.readOne(MINIMAL_ICS)
        original_summary = cal.vevent_list[0].summary.value
        parserrules.facebookOrganiser(cal)
        self.assertEqual(cal.vevent_list[0].summary.value, original_summary)

    def test_organiser_with_cn_prepended_to_description(self):
        cal = vobject.readOne(FACEBOOK_ICS)
        parserrules.facebookOrganiser(cal)
        desc = cal.vevent_list[0].description.value
        self.assertTrue(desc.startswith('Organised by:'))
        self.assertIn('Organizer', desc)
        self.assertIn('organizer@example.com', desc)

    def test_original_description_preserved_after_organiser(self):
        cal = vobject.readOne(FACEBOOK_ICS)
        parserrules.facebookOrganiser(cal)
        self.assertIn('Come celebrate!', cal.vevent_list[0].description.value)

    def test_organiser_without_cn_uses_fallback(self):
        cal = vobject.readOne(FACEBOOK_ICS_NO_CN)
        parserrules.facebookOrganiser(cal)
        desc = cal.vevent_list[0].description.value
        self.assertTrue(desc.startswith('Organized by:'))
        self.assertIn('bob@example.com', desc)

    def test_event_without_organiser_not_modified(self):
        ics = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:No Organiser
DESCRIPTION:Original description
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:fb-noorg@facebook.com
END:VEVENT
END:VCALENDAR
"""
        cal = vobject.readOne(ics)
        parserrules.facebookOrganiser(cal)
        self.assertEqual(cal.vevent_list[0].description.value, 'Original description')

    def test_event_without_description_not_modified(self):
        ics = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Facebook//Facebook//EN
BEGIN:VEVENT
SUMMARY:No Description
ORGANIZER;CN=Someone:MAILTO:x@example.com
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:fb-nodesc@facebook.com
END:VEVENT
END:VCALENDAR
"""
        cal = vobject.readOne(ics)
        parserrules.facebookOrganiser(cal)
        self.assertNotIn('description', cal.vevent_list[0].contents)


class TestWhatPrivacy(unittest.TestCase):

    def test_non_matching_calendar_not_modified(self):
        cal = vobject.readOne(MINIMAL_ICS)
        parserrules.whatPrivacy(cal)
        self.assertNotIn('class', cal.vevent_list[0].contents)

    def test_facebook_private_class_becomes_public(self):
        cal = vobject.readOne(FACEBOOK_ICS_WITH_CLASS)
        parserrules.whatPrivacy(cal)
        self.assertEqual(cal.vevent_list[0].contents['class'][0].value, 'PUBLIC')

    def test_exchange_private_class_becomes_public(self):
        cal = vobject.readOne(EXCHANGE_ICS_WITH_CLASS)
        parserrules.whatPrivacy(cal)
        self.assertEqual(cal.vevent_list[0].contents['class'][0].value, 'PUBLIC')

    def test_event_without_class_not_affected(self):
        cal = vobject.readOne(FACEBOOK_ICS)
        parserrules.whatPrivacy(cal)
        self.assertNotIn('class', cal.vevent_list[0].contents)


class TestBusyTentativeOnly(unittest.TestCase):

    def test_non_exchange_calendar_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        parserrules.BusyTentativeOnly(cal)
        self.assertEqual(len(cal.vevent_list), 1)

    def test_busy_events_kept(self):
        cal = vobject.readOne(EXCHANGE_ICS)
        parserrules.BusyTentativeOnly(cal)
        summaries = [e.summary.value for e in cal.vevent_list]
        self.assertIn('Busy Meeting', summaries)

    def test_tentative_events_kept(self):
        cal = vobject.readOne(EXCHANGE_ICS)
        parserrules.BusyTentativeOnly(cal)
        summaries = [e.summary.value for e in cal.vevent_list]
        self.assertIn('Tentative', summaries)

    def test_free_events_removed(self):
        cal = vobject.readOne(EXCHANGE_ICS)
        parserrules.BusyTentativeOnly(cal)
        summaries = [e.summary.value for e in cal.vevent_list]
        self.assertNotIn('Free Time', summaries)

    def test_oof_events_removed(self):
        cal = vobject.readOne(EXCHANGE_ICS)
        parserrules.BusyTentativeOnly(cal)
        summaries = [e.summary.value for e in cal.vevent_list]
        self.assertNotIn('Out of Office', summaries)

    def test_event_without_status_kept(self):
        cal = vobject.readOne(EXCHANGE_ICS_NO_STATUS)
        parserrules.BusyTentativeOnly(cal)
        self.assertEqual(len(cal.vevent_list), 1)
        self.assertEqual(cal.vevent_list[0].summary.value, 'No Status')

    def test_only_busy_and_tentative_remain(self):
        cal = vobject.readOne(EXCHANGE_ICS)
        parserrules.BusyTentativeOnly(cal)
        self.assertEqual(len(cal.vevent_list), 2)


class TestStripGoogleReminders(unittest.TestCase):

    def test_non_google_calendar_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        parserrules.stripGoogleReminders(cal)
        self.assertEqual(len(cal.vevent_list), 1)

    def test_valarm_removed_from_google_event(self):
        cal = vobject.readOne(GOOGLE_ICS_WITH_ALARM)
        parserrules.stripGoogleReminders(cal)
        self.assertNotIn('valarm', cal.vevent_list[0].contents)

    def test_google_event_without_alarm_unaffected(self):
        ics = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
SUMMARY:No Alarm
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
UID:google-no-alarm@gmail.com
END:VEVENT
END:VCALENDAR
"""
        cal = vobject.readOne(ics)
        parserrules.stripGoogleReminders(cal)
        self.assertEqual(len(cal.vevent_list), 1)


class TestStripGoogleAppleExtensions(unittest.TestCase):

    def test_non_google_calendar_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        parserrules.stripGoogleAppleExtensions(cal)
        self.assertIn('summary', cal.vevent_list[0].contents)

    def test_apple_properties_removed(self):
        cal = vobject.readOne(GOOGLE_ICS_WITH_APPLE_PROPS)
        parserrules.stripGoogleAppleExtensions(cal)
        for key in cal.vevent_list[0].contents:
            self.assertFalse(key.startswith('x-apple'), f'apple property not removed: {key!r}')

    def test_standard_properties_preserved(self):
        cal = vobject.readOne(GOOGLE_ICS_WITH_APPLE_PROPS)
        parserrules.stripGoogleAppleExtensions(cal)
        event = cal.vevent_list[0]
        self.assertIn('summary', event.contents)
        self.assertIn('dtstart', event.contents)
        self.assertIn('dtend', event.contents)


class TestUtcise(unittest.TestCase):

    def test_non_facebook_calendar_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        result = parserrules.utcise(cal)
        self.assertIs(result, cal)

    def test_naive_datetime_becomes_timezone_aware(self):
        cal = vobject.readOne(FACEBOOK_ICS_NAIVE_TZ)
        parserrules.utcise(cal)
        dt = cal.vevent_list[0].dtstart.value
        self.assertIsNotNone(dt.tzinfo)

    def test_already_utc_datetime_not_double_converted(self):
        cal = vobject.readOne(FACEBOOK_ICS)
        original_dt = cal.vevent_list[0].dtstart.value
        parserrules.utcise(cal)
        result_dt = cal.vevent_list[0].dtstart.value
        self.assertEqual(original_dt, result_dt)


class TestUnwantedParams(unittest.TestCase):

    def test_non_facebook_calendar_unchanged(self):
        cal = vobject.readOne(MINIMAL_ICS)
        result = parserrules.unwantedParams(cal)
        self.assertIs(result, cal)

    def test_language_param_removed_from_facebook(self):
        cal = vobject.readOne(FACEBOOK_ICS_WITH_PARAMS)
        parserrules.unwantedParams(cal)
        summary = cal.vevent_list[0].summary
        self.assertNotIn('LANGUAGE', summary.params)


if __name__ == '__main__':
    unittest.main()
