#!/usr/local/bin/python

import atexit, os, rfc822, re, time, errno, tempfile, types
from pty import STDOUT_FILENO, STDERR_FILENO

#MFCNG_ROOT = '/tmp/MFCns'
MFCNG_ROOT = '/home/sobomax/MFCns'
MFCNG_TMP = os.path.join(MFCNG_ROOT, 'tmp')
MFCNG_SPOOL = os.path.join(MFCNG_ROOT, 'spool')
MFCNG_QUEUE = os.path.join(MFCNG_ROOT, 'queue')
MFCNG_LOGFILE = os.path.join(MFCNG_ROOT, 'log/MFCns.log')
MFC_PTRN = '^  [ \t]*MFC[ \t]+(after|in):[ \t]*(?P<ndays>[0-9]+)[ \t]*(?P<measr>days?|weeks?)?[ \t]*$'
SECSADAY = 24*60*60
MAILCMD = '/usr/local/bin/mailsend -H'


def sendnote(to, subject, content):
	tempfile.tempdir = MFCNG_TMP
	tempname = tempfile.mktemp()
	file = open(tempname, 'w')

	template = map(lambda str: str + '\n', \
		('From: "Maxim Sobolev" <sobomax@FreeBSD.org>',				\
		 'Subject: Pending MFC Reminder [%s]' % subject,			\
		 '',									\
		 'Dear %s,' % to[0],							\
		 '',									\
		 'As you have requested, I would like to notify you that you have',	\
		 'committed a change that may be MFC\'ed now, as a testing period',	\
		 'specified at the time of that commit is over.',			\
		 '',									\
		 'For reference purposes following is a copy of your original',		\
		 'commit message.',							\
		 '',									\
		 'Regards,',								\
		 '',									\
		 'Maxim "MFC Reminder" Sobolev',					\
		 'P.S. Please contact Maxim Sobolev <sobomax@FreeBSD.org> if you',	\
		 'believe that you received this message due to an error.',		\
		 ''))
	template.extend(content)
	file.writelines(template)
	file.close()
	cmdline = '%s %s < %s' % (MAILCMD, to[1], tempname)
	exitstat = os.system(cmdline)
	if os.WIFEXITED(exitstat):
		exitval = os.WEXITSTATUS(exitstat)
		if exitval != 0:
			os.unlink(tempname)
			raise IOError('can\'t send a message: external command returned non-zero error code')
	os.unlink(tempname)

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
	args.insert(0, stime())
	args = tuple(args)
	print format % args

# Prepare environment

log = open(MFCNG_LOGFILE, 'a')
logfd = log.fileno()
os.dup2(logfd, STDOUT_FILENO)
os.dup2(logfd, STDERR_FILENO)
lprintf('MFCns_handler started')
atexit.register(cleanup)

# Part I. Spool dir processing

mfc_rex = re.compile(MFC_PTRN)

for filename in os.listdir(MFCNG_SPOOL):
	filename = os.path.join(MFCNG_SPOOL, filename)
	if not os.path.isfile(filename):
		lprintf('%s: not a file found in the spool directory', filename)
		continue

	file = open(filename, 'r')
	message = rfc822.Message(file)

	date = list(message.getdate('Date'))

	message.rewindbody()
	content = file.readlines()
	file.close()

	mfc_in = 0
	for line in content:
		result = mfc_rex.match(line)
		if result == None:
			continue
		mfc_in = int(result.group('ndays'))
		if result.group('measr')[0:4] == 'week':
			mfc_in *= 7
	if mfc_in <= 0:
		lprintf('%s: doesn\'t look like a MFC notification request', filename)
		continue

	date[3] = date[4] = date[5] = 0
	timestamp = time.mktime(tuple(date))
	timestamp += mfc_in * SECSADAY
	date = time.localtime(timestamp)
	strdate = '%d%02d%02d' % tuple(date[0:3])

	destdir = os.path.join(MFCNG_QUEUE, strdate)
	if not os.path.exists(destdir):
		os.mkdir(destdir)
	if not os.path.isdir(destdir):
		raise IOError(errno.ENOTDIR, 'Not a directory', destdir)

	os.rename(filename, os.path.join(destdir, os.path.basename(filename)))


# Part II. Queue processing

timestamp = time.time()
cdate = time.localtime(timestamp)
today = int('%d%02d%02d' % tuple(cdate[0:3]))

for dir in os.listdir(MFCNG_QUEUE):
	fdir = os.path.join(MFCNG_QUEUE, dir)
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
		sendnote(to, subject, content)
		lprintf('MFC notification sent to "%s" <%s>', to)
		os.unlink(filename)

	if len(os.listdir(fdir)) == 0:
		os.rmdir(fdir)
	else:
		lprintf('%s: directory can\'t be deleted because it is not empty', fdir)

