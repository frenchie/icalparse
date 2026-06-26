# icalparse

A Python CGI script that fetches and cleans up iCalendar feeds from hosted services before serving them to calendar clients.

## What it does

Calendar services like Google Calendar, Facebook, and Outlook/Exchange export iCalendar feeds with quirks that cause problems in other clients. icalparse fetches those feeds and applies a set of rules to fix them:

- **Facebook** — adds organiser details to event descriptions, converts naive datetimes to UTC, removes junk parameters, marks events public
- **Google Calendar** — strips VALARM reminders (which cause Outlook to complain) and Apple-specific extensions
- **Outlook/Exchange** — filters out Free, Out of Office, and Working Elsewhere events so only Busy and Tentative events are proxied; marks events public

## Usage

### As a CGI script

Deploy `icalparse.py` as a CGI script. Pass the service, uid, and key as query parameters:

```
https://yourserver/cgi-bin/icalparse.py?service=google&uid=<uid>&key=<key>
```

Supported services:

| `service` | Upstream URL template |
|---|---|
| `google` | `https://calendar.google.com/calendar/ical/<uid>/<key>/basic.ics` |
| `outlook` | `https://outlook.office365.com/owa/calendar/<uid>/<key>/calendar.ics` |
| `facebook` | `http://www.facebook.com/ical/u.php?uid=<uid>&key=<key>` |

`facebook` is the default if `service` is omitted.

### From the command line

```
usage: icalparse.py [-h] [-i] [-v] [-o OUTFILE] [-m ENCODING] [-t TIMEZONE] [url]

positional arguments:
  url                   URL (or local path) of the calendar to fetch

options:
  -i, --stdin           Take a calendar from standard input
  -v, --verbose         Be verbose when rules are being applied
  -o OUTFILE            Specify output file (defaults to standard output)
  -m ENCODING           Specify a character encoding
  -t TIMEZONE           Specify a default timezone for calendars that omit one
```

## Adding rules

Rules live in `parserrules.py`. Each top-level function that takes a `cal` argument and returns a `cal` object is automatically picked up. The docstring is shown when running with `--verbose`.

```python
def myRule(cal):
    '''What this rule does.'''
    # modify cal here
    return cal
```

## Requirements

- Python 3.x
- [vobject](https://github.com/eventable/vobject)
- [pytz](https://pythonhosted.org/pytz/) (for the Facebook timezone rule)

## Running the tests

```
python3 -m pytest tests.py
```

## License

MIT
