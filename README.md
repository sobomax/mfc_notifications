# Merge Fom Current ("MFC") notification service ("MFCns") for the [FreeBSD Project](https://freebsd.org).

## Introduction

At the some point of FreeBSD development it became apparent that in order
to help developers to perform timely features merge from the developent
branch (aka FreeBSD-CURRENT) into stable branch (aka FreeBSD-STABLE) some
form of automatic system, which will track outstanding merges and notify
appropriate developer when the time for a merge has come, is necessary.
Otherwise, developers are often stick with two extreme cases: some of them
forget to merge changes, even those that are clearly safe to merge, while
some performing merge shorly after committing the change into a development
branch fearing that if the merge is delayed they will forget to do it at
all. Both those cases introduce problems to the Project, because in the
former case stable branch experiences feature stagnation, while the latter
leads to stability degradation, as the features are often being merged
without proper testing in the development branch.

To address the problem the MFCns service was created. It works as follows:
when committing a change to a development branch a developer specifies a
time period during which the appropriate change has to be tested before
being merged into a stable branch. The system notes this request and after
this time period is over, it notifies the developer about that fact. It is
important to emphasise that the final decision as to whether to merge
change in question or not is up to the developer, because at that time he
might have received an information that makes a merge undesirable (e.g. bug
report from user who experieces problem with the change, security advisory
from a security officer, negative feedback from other developers and so
on).

## Design

When designing the MFCns the following goals were attacked:

1. The service should be triggered by the presence of the special field in
   the commit message;
1. due to the fact that it will have to parse all commit messages it should
   be speed-efficient during initial selection of messages, when it have
   to separate few messages which cointain that special field from a much
   larger number of those that do not;
1. it should be robust enough to minimise possibility of the accidental
   match and provide some form of resilence, so that if the service is
   halted for some reason (e.g. machine maintenance, program error etc.)
   already queued notifications aren't lost and will be sent once the
   operation of the service is resumed.

## Implementation

The service is implemented in two parts. First part written in C is a
simple mail filter, which reads mail message (one a time) from the standard
input, looks for a set of patterns and if all conditions are satisfied
writes copy of message into a specially designated `spool` folder. To avoid
using locks the filter initially writes message into a temporary folder and
then moves it into a `spool` folder using rename(2) system call, which is
guranteed to be atomic operation. Obviously this means that both temporary
and `spool` folders have to reside on the same filesystem, so please keep
this in mind if you are going to use the service elsewhere. The name of the
file in the `spool` directory is generated using value in the "Message-ID"
field of the message, allowing to avoid duplicated notification if for
some reason more than one copy of the same commit message will be received
by the filter. Since e-mail messages is considered as an "unsafe" medium,
the filter puts significant restrictions on the part of the "Message-ID"
field to be used as the filename, so that it is impossible to use forged
message to overwrite a file outside of the `spool` directory.

The second part of the service does most of the job, which includes spool
and queue processing and sending reminders. Since this part is not
speed-critical (it only invoked once a day), it was implemented in Python.
Its operation consists of the following phases:

- spool processing. At this stage the service parses all messages in the
  `spool` folder, identifies the date at which each notification is to be
  delivered and moves messages into the `queue` directory. In the `queue`
  folder messages are placed into subfolders named by the date when each
  notification is due (YYYYMMDD), so that all notifications which should be
  delivered at the same date end up in the same subfolder. Such design
  simplifies future queue processing as well as gurantees that each message
  is parsed only twice - first time when it is moved from the `spool` to
  `queue` to calculate the date when notification have to be sent and
  second time when the service actually sends a notification to identify to
  whom send it;
- queue processing. At this stage the service inspects the `queue`
  directory and identifies which notifications are ready to be sent. It
  parses each request from the `ready` subset, identifies recepient,
  generates outgoing message and sends it out. Once notification is sent
  the notification request is deleted from the `queue`.

## Security

Since e-mail is widely known as a not very safe medium, the service was
designed with security in mind, however no formal security audit was
performed yet. The part of the service written in C doesn't use any
statically allocated string buffers, so it should not be vulnerable to
various smash-the-stack attacks, while part written in Python was specially
tailored to not pass any of the shell metacharacters to a subshell invoked
for sending notification.  All this makes a potential attack pretty
meaningless, because all that an attacker could do is to make service
sending fake MFC notifications, but he can do this even without any help
from the service.

## Obtaining the code

https://github.com/sobomax/mfc_notifications

## Feedback

If you have any questions/suggestions/requests please don't hesitate to
contact Maxim Sobolev <sobomax@FreeBSD.org>. Also, if possible, drop me a
line if you will find this code useful somewhere outside of the FreeBSD
Project.

-- Maxim Sobolev <sobomax@FreeBSD.org>
