/*
 * ---------------------------------------------------------------------------
 * "THE BEER-WARE LICENSE" (Revision 42, (c) Poul-Henning Kamp): Maxim
 * Sobolev <sobomax@FreeBSD.org> wrote this file. As long as you retain
 * this  notice you can  do whatever you  want with this stuff. If we meet
 * some day, and you think this stuff is worth it, you can buy me a beer in
 * return.
 *
 * Maxim Sobolev
 * ---------------------------------------------------------------------------
 *
 * $FreeBSD$
 *
 */

#include <err.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <regex.h>

#ifdef _HOME
#define MFCNS_ROOT	"/tmp/MFCns"
#else
#define MFCNS_ROOT	"/home/sobomax/MFCns"
#endif
#define MFCNS_TMP	MFCNS_ROOT "/tmp"
#define MFCNS_SPOOL	MFCNS_ROOT "/spool"

#define MID_PTRN	"^Message-Id: <([a-zA-Z0-9.]+@gitrepo\\.freebsd\\.org)>$"
#define BRNCH_PTRN	"^X-Git-Refname: refs/heads/([a-z0-9-]+)$"
#define SENDER_PTRN	"^Sender: (.*)$"
#define MFC_PTRN	"^  [ \t]*MFC[ \t]+([Aa]fter|[Ii]n):[ \t]*([0-9]+)[ \t]*(days?|weeks?|months?)?[ \t]*$"

int	safe_regcomp(regex_t *, const char *, int);
char	*get_matched_str(char *, regmatch_t [], int);

int
main()
{
    FILE *tempfile;
    int fd, currlvl, isbody;
    char *branch, *line, *mfc_per, *msgid, *outname, *sender, *tmp;
    char tmpname[] = MFCNS_TMP "/.MFCns.XXXXXX";
    regex_t brnch_rex, mfc_rex, mid_rex, sender_rex;
    regmatch_t matches[2];
    size_t lenr, lenw;

    /*{static int b=1; while (b);}*/
    fd = mkstemp(tmpname);
    if (fd < 0) {
	err(2, "%s", tmpname);
	/* Not Reached */
    }

    tempfile = fdopen(fd, "w");
    if (tempfile == NULL) {
	err(2, "%s", tmpname);
	/* Not Reached */
    }

    safe_regcomp(&brnch_rex, BRNCH_PTRN, REG_EXTENDED | REG_NEWLINE);
    safe_regcomp(&mfc_rex, MFC_PTRN, REG_EXTENDED | REG_NEWLINE);
    safe_regcomp(&mid_rex, MID_PTRN, REG_EXTENDED | REG_NEWLINE);
    safe_regcomp(&sender_rex, SENDER_PTRN, REG_EXTENDED | REG_NEWLINE);

    branch = NULL;
    msgid = NULL;
    sender = NULL;
    mfc_per = NULL;
    currlvl = 0;
    isbody = 0;
    while((line = fgetln(stdin, &lenr)) != NULL) {
	lenw = fwrite(line, 1, lenr, tempfile);
	if (lenw != lenr) {
	    warn("%s", tmpname);
	    unlink(tmpname);
	    exit(2);
	}

	if (line[lenr - 1] != '\n') {
	    tmp = alloca(++lenr);
	    line = memcpy(tmp, line, lenr - 1);
	}
	line[lenr - 1] = '\0';

	if ((isbody == 0) && (lenr == 1)) {
	    if (currlvl != 1)
		goto notmatched;
	    isbody = 1;
	}

	switch(currlvl) {
	case 0:
	    /* There is no defined header order, look for all three before progressing */
	    /* -peter */
	    if (msgid == NULL && regexec(&mid_rex, line, 2, matches, 0) == 0) {
		msgid = strdup(get_matched_str(line, matches, 1));
	    }
	    if (branch == NULL && regexec(&brnch_rex, line, 2, matches, 0) == 0) {
		branch = strdup(get_matched_str(line, matches, 1));
		if (strcasecmp(branch, "main") != 0)
		    goto notmatched;
	    }
	    if (sender == NULL && regexec(&sender_rex, line, 2, matches, 0) == 0) {
		sender = strdup(get_matched_str(line, matches, 1));
		if ((strcasecmp(sender, "owner-cvs-all@FreeBSD.ORG") != 0) &&
		    (strcasecmp(sender, "owner-cvs-committers@FreeBSD.org") != 0) &&
		    (strcasecmp(sender, "owner-src-committers@FreeBSD.org") != 0))
		    goto notmatched;
	    }
	    if (msgid != NULL && branch != NULL && sender != NULL) {
		currlvl++;
	    }
	    break;

	case 1:
	    if (regexec(&mfc_rex, line, 2, matches, 0) == 0) {
		mfc_per = strdup(get_matched_str(line, matches, 1));
		currlvl++;
	    }
	    break;

	default:
	    break;
	}
    }

    fclose(tempfile);

    if (currlvl < 1 || msgid == NULL || branch == NULL || mfc_per == NULL)
	goto notmatched;

    asprintf(&outname, "%s/%s", MFCNS_SPOOL, msgid);

    if (rename(tmpname, outname) != 0) {
	err(2, "rename %s to %s", tmpname, outname);
	/* Not Reached */
    }

    exit(0);

notmatched:
    unlink(tmpname);
    exit(1);
}

int
safe_regcomp(regex_t *preg, const char *pattern, int cflags)
{
    char errbuf[255];
    int rval;

    rval = regcomp(preg, pattern, cflags);
    if (rval != 0) {
	errbuf[0] = '\0';
	regerror(rval, preg, errbuf, sizeof(errbuf));
	errx(2, "can't compile regular expression: %s", errbuf);
	/* Not Reached */
    }

    return rval;
}

char *
get_matched_str(char *pattern, regmatch_t pmatch[], int matchn)
{
    size_t len;
    static char *rval = NULL;

    len = pmatch[matchn].rm_eo - pmatch[matchn].rm_so + 1;

    if (rval == NULL)
	rval = malloc(len);
    else
	rval = realloc(rval, len);

    strlcpy(rval, pattern + pmatch[matchn].rm_so, len);

    return rval;
}
