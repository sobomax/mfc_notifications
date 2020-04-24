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

import atexit, os, re, time, errno, types, socket
from email import policy, message_from_bytes
from email.utils import parsedate, parseaddr
from subprocess import Popen, PIPE
from pty import STDOUT_FILENO, STDERR_FILENO

def isstr(obj):
    try:
        return (isinstance(obj, basestring))
    except NameError:
        return (isinstance(obj, str))

MFCNS_ROOT = '/home/sobomax/MFCns'
MAILCMD = '/usr/sbin/sendmail'

# XXX (for debugging purposes)
if  socket.gethostname() == 'notebook':
    MFCNS_ROOT = '/tmp/MFCns'
    MAILCMD = os.path.join(MFCNS_ROOT, 'testsend')

MFCNS_TMP = os.path.join(MFCNS_ROOT, 'tmp')
MFCNS_SPOOL = os.path.join(MFCNS_ROOT, 'spool')
MFCNS_QUEUE = os.path.join(MFCNS_ROOT, 'queue')
MFCNS_LOGFILE = os.path.join(MFCNS_ROOT, 'log/MFCns.log')
MFC_PTRN = '^  [ \t]*MFC[ \t]+([Aa]fter|[Ii]n):[ \t]*(?P<ndays>[0-9]+)[ \t]*(?P<measr>days?|weeks?|months?)?[ \t]*$'
MFC_TRAL = '^To Unsubscribe: send mail to majordomo@FreeBSD\\.org'
SECSADAY = 24*60*60

# Pause between sending notifications
SENDBREAK = 10

def sendnote(to, subject, branch, content):
    template = [x + '\n' for x in \
        ('From: MFC Notification Service <mfc-notifications@FreeBSD.org>',    \
         'To: %s <%s>' % to,                            \
         'Subject: Pending MFC Reminder [%s]' % subject,            \
         'X-FreeBSD-CVS-Branch: %s' % branch, \
         '',                                    \
         'Dear %s,' % to[0],                            \
         '',                                    \
         'As you have requested, I would like to notify you that you have',    \
         'committed a change that may be MFC\'ed now, as a testing period',    \
         'specified at the time of that commit is over.',            \
         '',                                    \
         'For reference purposes following is a copy of your original',        \
         'commit message.',                            \
         '',                                    \
         'Regards,',                                \
         '',                                    \
         'Maxim "MFC Reminder" Sobolev',                    \
         'P.S. Please contact Maxim Sobolev <sobomax@FreeBSD.org> if you',    \
         'believe that you received this message due to an error.',        \
         'P.P.S. Source code for this service is available at:',    \
         'https://github.com/sobomax/mfc_notifications',        \
         'Have a feature in mind? Pull requests are always very welcome!',  \
         'P.P.P.S. https://mfc.kernelnomicon.org is your friend!',
         '')]
    template.extend(content)
    template = [x.encode('utf-8') for x in template]

    pipe = Popen((MAILCMD, to[1]), stdout = PIPE, stdin = PIPE)
    pipe.stdin.writelines(template)
    for stream in (pipe.stdout, pipe.stdin):
        stream.close()
    if pipe.wait() != 0:
        raise IOError('can\'t send a message: external command returned non-zero error code')

def stime():
    return time.ctime(time.time())

def cleanup():
    lprintf('MFCns_handler finished')

def lprintf(fmt, args = ''):
    fmt = '%s: ' + fmt
    if isstr(args):
        if len(args) > 0:
            args = [args]
        else:
            args = []
    elif isinstance(args, tuple):
        args = list(args)
    elif type(args) in (types.IntType, types.LongType, types.FloatType):
        args = [args]
    args.insert(0, stime())
    args = tuple(args)
    print(fmt % args)


def main():    
    # Part 0. Prepare environment

    log = open(MFCNS_LOGFILE, 'a')
    logfd = log.fileno()
    os.dup2(logfd, STDOUT_FILENO)
    os.dup2(logfd, STDERR_FILENO)
    lprintf('MFCns_handler started')
    atexit.register(cleanup)


    # Part I. Spool dir processing

    mfc_rex = re.compile(MFC_PTRN)

    for filename in os.listdir(MFCNS_SPOOL):
        filename = os.path.join(MFCNS_SPOOL, filename)
        if not os.path.isfile(filename):
            lprintf('%s: not a file found in the spool directory', filename)
            continue

        lprintf('Processing "%s"...', filename)

        fdes = open(filename, 'rb')
        fcon = fdes.read()
        message = message_from_bytes(fcon, policy = policy.default)
        fdes.close()

        date = list(parsedate(message['Date']))

        content = message.get_body().get_content().splitlines()

        mfc_in = -1
        for line in content:
            result = mfc_rex.match(line)
            if result == None:
                continue
            mfc_in = int(result.group('ndays'))
            measure = result.group('measr')
            if measure == None:
                pass
            elif measure[0:4] == 'week':
                mfc_in *= 7
            elif measure[0:5] == 'month':
                mfc_in *= 30
        if mfc_in < 0:
            lprintf('%s: doesn\'t look like a MFC notification request', filename)
            continue

        date[3] = date[4] = date[5] = 0
        timestamp = time.mktime(tuple(date))
        timestamp += mfc_in * SECSADAY
        date = time.localtime(timestamp)
        strdate = '%d%02d%02d' % tuple(date[0:3])

        destdir = os.path.join(MFCNS_QUEUE, strdate)
        if not os.path.exists(destdir):
            os.mkdir(destdir)
        if not os.path.isdir(destdir):
            raise IOError(errno.ENOTDIR, 'Not a directory', destdir)

        os.rename(filename, os.path.join(destdir, os.path.basename(filename)))


    # Part II. Queue processing

    timestamp = time.time()
    cdate = time.localtime(timestamp)
    today = int('%d%02d%02d' % tuple(cdate[0:3]))
    mfc_tral_rex = re.compile(MFC_TRAL)
    do_sleep = 0

    for dname in os.listdir(MFCNS_QUEUE):
        fdir = os.path.join(MFCNS_QUEUE, dname)
        if not (os.path.isdir(fdir) and len(dname) == 8 and int(dname) <= today):
            continue

        for filename in os.listdir(fdir):
            if do_sleep == 1:
                time.sleep(SENDBREAK)
            filename = os.path.join(fdir, filename)
            if not os.path.isfile(filename):
                lprintf('%s: not a file found in the queue directory', filename)
                continue

            lprintf('Processing "%s"...', filename)

            fdes = open(filename, 'rb')
            fcon = fdes.read()
            message = message_from_bytes(fcon, policy = policy.default)
            fdes.close()
            to = parseaddr(message['From'])
            subject = message['Subject']
            branch = message.get('X-FreeBSD-CVS-Branch', None)
            if branch == None:
                branch = message['X-SVN-Group']
            content = message.get_body().get_content().splitlines(keepends = True)

            i = 0
            for line in content:
                result = mfc_tral_rex.match(line)
                if result != None:
                    content = content[:i]
                    break
                i += 1

            sendnote(to, subject, branch, content)
            lprintf('MFC notification sent to "%s" <%s>', to)
            os.unlink(filename)
            do_sleep = 1

        if len(os.listdir(fdir)) == 0:
            os.rmdir(fdir)
        else:
            lprintf('%s: directory can\'t be deleted because it is not empty', fdir)


# Allow this module to be imported
if __name__ == '__main__':
    main()    
