# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

import httplib
import urllib

WEBKOOK_URL = 'https://hooks.slack.com/services/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'
PAYLOAD = payload = {
    "text": "This is a line of text in a channel.\nAnd this is another line of text."
}

params = urllib.urlencode({'from': 'GBP', 'date': ''})
headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

conn = httplib.HTTPSConnection("hooks.slack.com")
conn.request("POST", "/services/T04BPS5RH/BFH6AUSDA/c3QaAzRMVaV0xLqlFpRhHnzF/", params, headers)
response = conn.getresponse()
print response.read()
