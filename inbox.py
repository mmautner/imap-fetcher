#!/usr/bin/env python

"""
Make sure to create your own "secret.py" containing your gmail address and password
(modeled after "secret.py.example")

Surprisingly, this only takes about 30-60 mins for a 2GB email account.
"""

import imaplib
import email
import re
from math import ceil
import sqlite3

from dateutil import parser
import pytz

from secret import ADDRESS, PASSWD
from database import DB

DATE_FMT = '%Y-%m-%d %H:%M:%S'
LIST_RESPONSE_PATTERN = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
EMAIL_FIELDS = ('created_ts', 'subject', 'body', 'uid')

def save_email(db, emsg, flags=[]):
    c = db.cursor()

    c.execute("""\
    INSERT INTO emails (id, created_ts, subject, body, uid) 
    VALUES (?, ?, ?, ?, ?) """, [None] + [emsg.get(field) for field in EMAIL_FIELDS])
    db.commit()
    email_id = c.lastrowid

    c.execute("""\
    INSERT OR IGNORE INTO senders (id, sender_address, friendly_from)
    VALUES (?, ?, ?) """, (None, emsg['sender_address'], emsg['friendly_from']))
    db.commit()

    c.execute("""\
    INSERT OR IGNORE INTO emails_by_sender (email_id, sender_id)
    VALUES (?, ?) """, (email_id, c.lastrowid))
    db.commit()

    c.execute("""\
    INSERT OR IGNORE INTO recipients (id, recipient_address, friendly_to)
    VALUES (?, ?, ?)""", (None, emsg['recipient'][1], emsg['recipient'][0]))
    db.commit()

    c.execute("""\
    INSERT OR IGNORE INTO emails_by_recipient (email_id, recipient_id)
    VALUES (?, ?) """, (email_id, c.lastrowid))
    db.commit()
    
    for flag in flags:
        c.execute("INSERT INTO flags (id, flag, email_id) VALUES (?, ?, ?)", (None, flag, c.lastrowid))
        db.commit()

    return True

def get_first_text_payload(emsg, depth=0):
    body = ''
    if emsg.get_content_maintype() == 'multipart':
        for part in emsg.get_payload():
            body = get_first_text_payload(part, depth+1)
            content_type = part.get_content_type()
            if body != '':
                break
    else:
        content_type = emsg.get_content_type()
        if content_type == 'text/plain':
            body = emsg.get_payload()
    return body

def parse_email(emsg):
    new_email = {}
    new_email['friendly_from'], new_email['sender_address'] = email.utils.parseaddr(emsg['From'])
    new_email['recipient'] = email.utils.parseaddr(emsg['To'])
    try:
        received = emsg['Received']     # e.g. 'by 10.76.122.145 with HTTP; Thu, 22 Nov 2012 10:09:06 -0800 (PST)'
        w_tz_info = parser.parse(received[received.find(';')+2:])
        new_email['created_ts'] = w_tz_info.astimezone(pytz.utc).strftime(DATE_FMT)
    except:
        new_email['created_ts'] =  '0000-00-00 00:00:00'
    new_email['subject'] = emsg['Subject']
    new_email['body'] = get_first_text_payload(emsg)
    return new_email

def parse_msg(msg):
    e = parse_email(email.message_from_string(msg[1]))
    flags = imaplib.ParseFlags(msg[0])
    return e, flags

def get_emails_by_uid(conn, uids, data_fmt='(FLAGS BODY.PEEK[])'):
    _, msgs = conn.uid('fetch', ','.join((str(uid) for uid in uids)), data_fmt)
    emsgs = []
    for i, msg in enumerate(msgs):
        if i % 2 == 1: # WHAT THE ACTUAL FUCK
            continue
        emsgs.append(msg)
    return emsgs

def save_bulk_emails(conn, uids, chunk_size, db):
    saved = 0
    chunks = int(ceil(len(uids)/float(chunk_size)))

    for chunk_idx in xrange(chunks):
        idx = chunk_idx * chunk_size
        upper_bound = idx + chunk_size if idx + chunk_size < len(uids) else len(uids) - 1

        print 'pulling down block %d of %d, from %d to %d' % (chunk_idx, chunks, idx, upper_bound)
        msgs = get_emails_by_uid(conn, uids[idx:upper_bound])
        for i, msg in enumerate(msgs):
            emsg, flags = parse_msg(msg)
            emsg['uid'] = uids[idx+i]
            success = save_email(db, emsg, flags)
            saved += 1 if success is not None else 0

    return saved

def get_uids(conn):
    _, uids = conn.uid('search', 'all')
    return [int(uid) for uid in uids[0].split(' ')]

def save_mailbox(conn, db, bulk=False, chunk_size=100, limit=None):
    uids = get_uids(conn)
    uids = uids[::-1] # download starting from most recent
    if limit is not None and limit < len(uids):
        uids = uids[-limit:]
    print uids
    print '%d messages to download.' % len(uids)
    saved = save_bulk_emails(conn, uids, chunk_size, db)
    return saved

def get_folders(conn):
    _, folder_list = conn.list()
    folders = []
    for line in folder_list:
        flags, delimiter, mailbox_name = LIST_RESPONSE_PATTERN.match(line).groups()
        mailbox_name = mailbox_name.strip('"')
        folders.append(mailbox_name)
        print conn.status(mailbox_name, '(MESSAGES UNSEEN)')
    return folders


if __name__=='__main__':

    imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_conn.login(ADDRESS, PASSWD)
    db = sqlite3.connect(DB)

    #folders = get_folders(imap_conn)
    folders = ["[Gmail]/All Mail"]
    for f in folders:
        imap_conn.select(f)
        num_saved = save_mailbox(imap_conn, db, limit=100)
        print '%d emails saved to db from %s' % (num_saved, f)
    print 'done.'

