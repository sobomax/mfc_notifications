#!/usr/local/bin/python
#
# ---------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42, (c) Poul-Henning Kamp): Maxim
# Sobolev <sobomax@FreeBSD.org> wrote this file. As long as you retain
# this  notice you can  do whatever you  want with this stuff. If we meet
# some day, and you think this stuff is worth it, you can buy me a beer in
# return.
#
# Maxim Sobolev
# ---------------------------------------------------------------------------
#
# $FreeBSD$
#

import re, sys
from MFCns_handler import MFCNS_LOGFILE


SENT_PTRN = '(?P<date>.+): MFC notification sent to "(?P<name>.+)" <(?P<addr>\\S+)@FreeBSD.org>'

def locatemax(stats):
    maxlines = -1
    maxhandle = ''
    for handle in stats.keys():
        nlines = stats[handle]
        if nlines < maxlines:
            continue
        if nlines > maxlines:
            maxlines = nlines
            maxhandle = handle
            continue
        if maxhandle > handle:
            maxlines = nlines
            maxhandle = handle
    return (maxhandle, maxlines)

def main():
    sent_rex = re.compile(SENT_PTRN)
    content = open(MFCNS_LOGFILE).readlines()

    log = []
    statsbyname = {}
    total = 0
    for line in content:
        result = sent_rex.match(line)
        if result == None:
            continue
        total += 1
        logentry = result.group('date').replace('  ', ' '), \
            result.group('name'), result.group('addr')
        if statsbyname.has_key(logentry[2]):
            statsbyname[logentry[2]] += 1
        else:
            statsbyname[logentry[2]] = 1
        log.append(logentry)

    print 'MFC Notification Service Statistics'
    print '-----------------------------------\n'
    print 'Period: %s - %s' % (log[0][0], log[-1][0])
    print 'Total number of notifications sent: %d' % total

    if total == 0:
        sys.exit(0)

    print '\n%s\t%s\t%s'   % ('Committer', 'MFCs', '% total')
    print '%s\t%s\t%s\n' % ('---------', '----', '-------')

    while len(statsbyname) != 0:
        handle, number = locatemax(statsbyname)
        if len(handle) >= 8:
            tab = '\t'
        else:
            tab = '\t\t'
        print '%s%s%4d\t%7.2f' % (handle, tab, number, 100.0 * number / total)
        del statsbyname[handle]

if __name__ == '__main__':
    main()
