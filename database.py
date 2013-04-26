#!/usr/bin/env python

import sqlite3
import datetime

DB = 'emails.db'

TABLES = ('emails',
          'flags',
          'recipients',
          'senders',
          'emails_by_recipient',
          'emails_by_sender')

def drop_tables(db):
    c = db.cursor()
    for table in TABLES:
        try:
            c.execute("DROP TABLE %s" % table)
            db.commit()
        except:
            pass

def create_tables(db):
    c = db.cursor()
    c.execute("""\
    CREATE TABLE emails (
        id INTEGER PRIMARY KEY,
        created_ts DATETIME,
        subject VARCHAR(510),
        body TEXT,
        uid INTEGER
        )""")
    db.commit()
    created_ts = datetime.datetime.now()
    emails = [(created_ts, 'yo', 'nice meeting you today!', 0),
              (created_ts, 'hi', 'nice shoes!', 0)]
    c.executemany("""\
    INSERT INTO emails (created_ts, subject, body, uid) VALUES 
    (?, ?, ?, ?) """, emails)
    db.commit()

    c.execute("""\
    CREATE TABLE senders (
        id INTEGER PRIMARY KEY,
        sender_address VARCHAR(255),
        friendly_from VARCHAR(255)
    )""")
    db.commit()

    c.execute("""\
    CREATE TABLE recipients (
        id INTEGER PRIMARY KEY,
        recipient_address VARCHAR(255),
        friendly_to VARCHAR(255)
    )""")
    db.commit()

    c.execute("""\
    CREATE TABLE flags (
        id INTEGER PRIMARY KEY,
        flag VARCHAR(255),
        email_id INTEGER
    )""")
    db.commit()

    c.execute("""\
    CREATE TABLE emails_by_sender (
        email_id INTEGER,
        sender_id INTEGER,
        PRIMARY KEY (email_id, sender_id)
    )""")
    db.commit()

    c.execute("""\
    CREATE TABLE emails_by_recipient (
        email_id INTEGER,
        recipient_id INTEGER,
        PRIMARY KEY (email_id, recipient_id)
    )""")
    db.commit()

if __name__=="__main__":
    with sqlite3.connect(DB) as db:
        drop_tables(db)
        create_tables(db)
