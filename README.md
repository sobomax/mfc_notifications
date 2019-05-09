# Merge From CURRENT ("MFC") notification service ("MFCns") for the [FreeBSD Project](https://freebsd.org).

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

## Usage Statistics

```
MFC Notification Service Statistics
-----------------------------------

Period: Wed May 9 00:22:02 2001 - Thu May 9 00:23:03 2019
Total number of notifications sent: 41356

Committer	MFCs	% total
---------	----	-------

kib		2998	   7.25
jhb		1544	   3.73
hselasky	1462	   3.54
ngie		1426	   3.45
rwatson		1217	   2.94
mav		1007	   2.43
trasz		 953	   2.30
markj		 938	   2.27
pjd		 922	   2.23
avg		 902	   2.18
delphij		 861	   2.08
dim		 724	   1.75
sephe		 703	   1.70
tuexen		 665	   1.61
bz		 652	   1.58
brueffer	 581	   1.40
bdrewery	 564	   1.36
pfg		 540	   1.31
ae		 539	   1.30
des		 509	   1.23
marius		 474	   1.15
rmacklem	 469	   1.13
emaste		 439	   1.06
np		 430	   1.04
asomers		 429	   1.04
arybchik	 409	   0.99
gjb		 400	   0.97
eadler		 390	   0.94
sam		 385	   0.93
ume		 357	   0.86
alc		 345	   0.83
maxim		 332	   0.80
mm		 311	   0.75
mjacob		 271	   0.66
nwhitehorn	 260	   0.63
sobomax		 257	   0.62
jilles		 229	   0.55
brooks		 211	   0.51
bapt		 210	   0.51
yar		 204	   0.49
ru		 201	   0.49
dteske		 196	   0.47
sbruno		 192	   0.46
smh		 189	   0.46
jhibbits	 186	   0.45
rpaulo		 183	   0.44
luigi		 182	   0.44
emax		 180	   0.44
gad		 180	   0.44
cy		 174	   0.42
dchagin		 171	   0.41
gavin		 170	   0.41
ken		 167	   0.40
brian		 161	   0.39
cperciva	 161	   0.39
trociny		 161	   0.39
kevans		 157	   0.38
melifaro	 157	   0.38
simon		 157	   0.38
julian		 154	   0.37
imp		 152	   0.37
andrew		 150	   0.36
pluknet		 144	   0.35
mjg		 136	   0.33
gnn		 134	   0.32
kmacy		 134	   0.32
njl		 133	   0.32
keramida	 131	   0.32
rnoland		 131	   0.32
ed		 130	   0.31
kientzle	 128	   0.31
gshapiro	 126	   0.30
marcel		 125	   0.30
jimharris	 122	   0.29
avos		 120	   0.29
scottl		 119	   0.29
dumbbell	 117	   0.28
rstone		 116	   0.28
bms		 115	   0.28
jkim		 115	   0.28
andre		 113	   0.27
manu		 113	   0.27
vangyzen	 109	   0.26
csjp		 108	   0.26
truckman	 107	   0.26
dwmalone	 106	   0.26
attilio		 104	   0.25
yongari		 103	   0.25
edwin		 102	   0.25
schweikh	 101	   0.24
rrs		  99	   0.24
gonzo		  98	   0.24
jmg		  98	   0.24
glebius		  97	   0.23
bschmidt	  92	   0.22
kp		  91	   0.22
joerg		  90	   0.22
mlaier		  90	   0.22
dillon		  89	   0.22
silby		  88	   0.21
thompsa		  88	   0.21
kris		  86	   0.21
mckusick	  86	   0.21
lstewart	  85	   0.21
mmel		  83	   0.20
allanjude	  82	   0.20
hrs		  80	   0.19
slavash		  77	   0.19
flz		  73	   0.18
philip		  72	   0.17
grehan		  71	   0.17
neel		  71	   0.17
davidcs		  69	   0.17
iedowse		  69	   0.17
wblock		  69	   0.17
kadesai		  66	   0.16
brucec		  65	   0.16
bryanv		  64	   0.15
cognet		  64	   0.15
dds		  64	   0.15
matteo		  63	   0.15
remko		  63	   0.15
sevan		  62	   0.15
will		  62	   0.15
ache		  61	   0.15
eugen		  61	   0.15
loos		  61	   0.15
nyan		  60	   0.15
fabient		  58	   0.14
ariff		  57	   0.14
gibbs		  56	   0.14
suz		  56	   0.14
jh		  55	   0.13
kensmith	  55	   0.13
ceri		  53	   0.13
jamie		  53	   0.13
stas		  53	   0.13
oleg		  50	   0.12
adrian		  48	   0.12
qingli		  48	   0.12
roam		  47	   0.11
royger		  47	   0.11
tjr		  46	   0.11
amdmi3		  45	   0.11
n_hibma		  45	   0.11
wulf		  45	   0.11
bcr		  44	   0.11
cjc		  44	   0.11
antoine		  43	   0.10
oshogbo		  43	   0.10
se		  42	   0.10
archie		  41	   0.10
erj		  41	   0.10
jfv		  41	   0.10
mikeh		  41	   0.10
pkelsey		  41	   0.10
danger		  40	   0.10
hiren		  40	   0.10
murray		  40	   0.10
zec		  40	   0.10
gabor		  39	   0.09
jkoshy		  39	   0.09
jpaetzel	  39	   0.09
mdf		  39	   0.09
tijl		  38	   0.09
grog		  37	   0.09
jdp		  37	   0.09
jmallett	  37	   0.09
jtl		  37	   0.09
rodrigc		  37	   0.09
iwasaki		  36	   0.09
mbr		  36	   0.09
thomas		  36	   0.09
pav		  35	   0.08
vmaffione	  35	   0.08
fsu		  34	   0.08
kaiw		  33	   0.08
sanpei		  33	   0.08
bmah		  32	   0.08
dab		  32	   0.08
gallatin	  32	   0.08
netchild	  32	   0.08
simokawa	  32	   0.08
uqs		  32	   0.08
dfr		  31	   0.07
ambrisko	  30	   0.07
mtm		  30	   0.07
ray		  30	   0.07
fjoe		  29	   0.07
krion		  29	   0.07
roberto		  29	   0.07
avatar		  28	   0.07
davidxu		  28	   0.07
rik		  28	   0.07
zont		  28	   0.07
dexuan		  27	   0.07
pdeuskar	  27	   0.07
araujo		  26	   0.06
bp		  26	   0.06
jeff		  26	   0.06
semenu		  26	   0.06
davidch		  25	   0.06
marck		  25	   0.06
mike		  25	   0.06
ups		  24	   0.06
wollman		  24	   0.06
lidl		  23	   0.06
mux		  23	   0.06
scf		  23	   0.06
damien		  22	   0.05
kan		  22	   0.05
markus		  22	   0.05
mmacy		  22	   0.05
shurd		  22	   0.05
wilko		  22	   0.05
daichi		  21	   0.05
lulf		  21	   0.05
rgrimes		  21	   0.05
rpokala		  21	   0.05
slm		  21	   0.05
das		  20	   0.05
garga		  20	   0.05
jmmv		  20	   0.05
bde		  19	   0.05
jhay		  19	   0.05
jlh		  19	   0.05
joe		  19	   0.05
mp		  19	   0.05
raj		  19	   0.05
theraven	  19	   0.05
trhodes		  19	   0.05
weongyo		  19	   0.05
cem		  18	   0.04
phk		  18	   0.04
yokota		  18	   0.04
alfred		  17	   0.04
guido		  17	   0.04
harti		  17	   0.04
blackend	  16	   0.04
hm		  16	   0.04
kevlo		  16	   0.04
pirzyk		  16	   0.04
stevek		  16	   0.04
jah		  15	   0.04
pho		  15	   0.04
ssouhlal	  15	   0.04
tsoome		  15	   0.04
issyl0		  14	   0.03
jesper		  14	   0.03
mr		  14	   0.03
rse		  14	   0.03
cokane		  13	   0.03
matusita	  13	   0.03
ps		  13	   0.03
rafan		  13	   0.03
akiyama		  12	   0.03
andreast	  12	   0.03
gj		  12	   0.03
jon		  12	   0.03
kbyanc		  12	   0.03
mdodd		  12	   0.03
orion		  12	   0.03
rink		  12	   0.03
sheldonh	  12	   0.03
vanhu		  12	   0.03
asmodai		  11	   0.03
brd		  11	   0.03
dcs		  11	   0.03
eri		  11	   0.03
ivoras		  11	   0.03
jcamou		  11	   0.03
jch		  11	   0.03
johan		  11	   0.03
le		  11	   0.03
sumikawa	  11	   0.03
wes		  11	   0.03
zack		  11	   0.03
gordon		  10	   0.02
ian		  10	   0.02
rmh		  10	   0.02
stefanf		  10	   0.02
wkoszek		  10	   0.02
ygy		  10	   0.02
0mp		   9	   0.02
davide		   9	   0.02
fanf		   9	   0.02
kuriyama	   9	   0.02
pb		   9	   0.02
rea		   9	   0.02
tmm		   9	   0.02
zeising		   9	   0.02
badger		   8	   0.02
benno		   8	   0.02
chuck		   8	   0.02
darrenr		   8	   0.02
dwhite		   8	   0.02
erwin		   8	   0.02
green		   8	   0.02
jkh		   8	   0.02
jonathan	   8	   0.02
jwd		   8	   0.02
marcus		   8	   0.02
marks		   8	   0.02
phantom		   8	   0.02
randi		   8	   0.02
anholt		   7	   0.02
bsd		   7	   0.02
deischen	   7	   0.02
eik		   7	   0.02
garys		   7	   0.02
karels		   7	   0.02
mmokhi		   7	   0.02
peterj		   7	   0.02
sepotvin	   7	   0.02
tobez		   7	   0.02
bjk		   6	   0.01
den		   6	   0.01
dg		   6	   0.01
dhartmei	   6	   0.01
feld		   6	   0.01
fenner		   6	   0.01
gahr		   6	   0.01
keichii		   6	   0.01
markm		   6	   0.01
msmith		   6	   0.01
mw		   6	   0.01
olgeni		   6	   0.01
olli		   6	   0.01
ram		   6	   0.01
sef		   6	   0.01
syrinx		   6	   0.01
whu		   6	   0.01
yuripv		   6	   0.01
bwidawsk	   5	   0.01
eric		   5	   0.01
ghelmer		   5	   0.01
greid		   5	   0.01
hmp		   5	   0.01
jlemon		   5	   0.01
mckay		   5	   0.01
mizhka		   5	   0.01
mnag		   5	   0.01
nsayer		   5	   0.01
peadar		   5	   0.01
rdivacky	   5	   0.01
robak		   5	   0.01
seanc		   5	   0.01
bruno		   4	   0.01
cel		   4	   0.01
dannyboy	   4	   0.01
grembo		   4	   0.01
imura		   4	   0.01
jceel		   4	   0.01
jgh		   4	   0.01
jinmei		   4	   0.01
knu		   4	   0.01
lwhsu		   4	   0.01
matthew		   4	   0.01
mjoras		   4	   0.01
nectar		   4	   0.01
olivier		   4	   0.01
piso		   4	   0.01
rsm		   4	   0.01
skra		   4	   0.01
takawata	   4	   0.01
ticso		   4	   0.01
tom		   4	   0.01
wpaul		   4	   0.01
assar		   3	   0.01
benjsc		   3	   0.01
bmilekic	   3	   0.01
chinsan		   3	   0.01
dmlb		   3	   0.01
emoore		   3	   0.01
groudier	   3	   0.01
jedgar		   3	   0.01
lioux		   3	   0.01
mini		   3	   0.01
phil		   3	   0.01
rakuco		   3	   0.01
rees		   3	   0.01
robert		   3	   0.01
ade		   2	   0.00
ale		   2	   0.00
amorita		   2	   0.00
babkin		   2	   0.00
billf		   2	   0.00
bland		   2	   0.00
brix		   2	   0.00
cg		   2	   0.00
chris		   2	   0.00
crees		   2	   0.00
dbaker		   2	   0.00
dd		   2	   0.00
gleb		   2	   0.00
jb		   2	   0.00
jmcneill	   2	   0.00
lme		   2	   0.00
luoqi		   2	   0.00
motoyuki	   2	   0.00
nork		   2	   0.00
osa		   2	   0.00
snb		   2	   0.00
sos		   2	   0.00
svn		   2	   0.00
tabthorpe	   2	   0.00
tmunro		   2	   0.00
zml		   2	   0.00
adamw		   1	   0.00
alex		   1	   0.00
anish		   1	   0.00
art		   1	   0.00
beat		   1	   0.00
ben		   1	   0.00
chm		   1	   0.00
dan		   1	   0.00
danny		   1	   0.00
davidn		   1	   0.00
dbaio		   1	   0.00
dru		   1	   0.00
edavis		   1	   0.00
gber		   1	   0.00
hsu		   1	   0.00
jasone		   1	   0.00
jim		   1	   0.00
jmb		   1	   0.00
jmz		   1	   0.00
johalun		   1	   0.00
kato		   1	   0.00
lawrance	   1	   0.00
lifanov		   1	   0.00
matk		   1	   0.00
mhorne		   1	   0.00
miwi		   1	   0.00
mpp		   1	   0.00
mwlucas		   1	   0.00
novel		   1	   0.00
pgj		   1	   0.00
pst		   1	   0.00
rene		   1	   0.00
riggs		   1	   0.00
rushani		   1	   0.00
sjg		   1	   0.00
skreuzer	   1	   0.00
tackerman	   1	   0.00
tanimura	   1	   0.00
thj		   1	   0.00
tomsoft		   1	   0.00
twinterg	   1	   0.00
ue		   1	   0.00
versus		   1	   0.00
vsevolod	   1	   0.00
xride		   1	   0.00
```

-- Maxim Sobolev <sobomax@FreeBSD.org>

