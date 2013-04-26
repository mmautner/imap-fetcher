#!/usr/bin/env python

import sqlite3

from database import DB

QRY = """\
SELECT
    count(*)
FROM emails e
JOIN emails_by_sender ebs on e.id = ebs.email_id
JOIN senders s on s.id = ebs.sender_id
"""

QRY2 = """\
SELECT
    count(*)
FROM emails e
JOIN emails_by_recipient ebr on e.id = ebr.email_id
JOIN recipients r on r.id = ebr.recipient_id
"""

def main(db):
    c = db.cursor()
    c.execute(QRY)
    print c.fetchall()[0][0]
    c.execute(QRY2)
    print c.fetchall()[0][0]

if __name__=="__main__":
    db = sqlite3.connect(DB)
    main(db)
