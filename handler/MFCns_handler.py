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

import atexit, os, rfc822, re, time, errno, types, socket, popen2
from pty import STDOUT_FILENO, STDERR_FILENO


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
MFC_PTRN = '^  [ \t]*MFC[ \t]+(after|in):[ \t]*(?P<ndays>[0-9]+)[ \t]*(?P<measr>days?|weeks?|months?)?[ \t]*$'
MFC_TRAL = '^To Unsubscribe: send mail to majordomo@FreeBSD\\.org'
SECSADAY = 24*60*60

def sendnote(to, subject, content):
    template = map(lambda str: str + '\n', \
        ('From: MFC Notification Service <mfc-notifications@FreeBSD.org>',    \
         'To: %s <%s>' % to,                            \
         'Subject: Pending MFC Reminder [%s]' % subject,            \
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
         ''))
    template.extend(content)

    cmdline = '%s %s' % (MAILCMD, to[1])
    pipe = popen2.Popen4(cmdline)
    pipe.tochild.writelines(template)
    for stream in (pipe.fromchild, pipe.tochild):
        stream.close()
    if pipe.wait() != 0:
        raise IOError('can\'t send a message: external command returned non-zero error code')

def stime():
    return time.ctime(time.time())

def cleanup():
    lprintf('MFCns_handler finished')

def lprintf(format, args = ''):
    format = '%s: ' + format
    if type(args) == types.StringType:
        if len(args) > 0:
            args = [args]
        else:
            args = []
    elif type(args) == types.TupleType:
        args = list(args)
    elif type(args) in (types.IntType, types.LongType, types.FloatType):
        args = [args]
    args.insert(0, stime())
    args = tuple(args)
    print format % args


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

        file = open(filename, 'r')
        message = rfc822.Message(file)

        date = list(message.getdate('Date'))

        message.rewindbody()
        content = file.readlines()
        file.close()

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

    for dir in os.listdir(MFCNS_QUEUE):
        fdir = os.path.join(MFCNS_QUEUE, dir)
        if not (os.path.isdir(fdir) and len(dir) == 8 and int(dir) <= today):
            continue

        for filename in os.listdir(fdir):
            filename = os.path.join(fdir, filename)
            if not os.path.isfile(filename):
                lprintf('%s: not a file found in the queue directory', filename)
                continue

            file = open(filename, 'r')
            message = rfc822.Message(file)
            to = message.getaddr('From')
            subject = message.getheader('Subject')
            message.rewindbody()
            content = file.readlines()
            file.close

            i = 0
            for line in content:
                result = mfc_tral_rex.match(line)
                if result != None:
                    content = content[:i]
                    break
                i += 1

            sendnote(to, subject, content)
            lprintf('MFC notification sent to "%s" <%s>', to)
            os.unlink(filename)

        if len(os.listdir(fdir)) == 0:
            os.rmdir(fdir)
        else:
            lprintf('%s: directory can\'t be deleted because it is not empty', fdir)


# Allow this module to be imported
if __name__ == '__main__':
    main()    
