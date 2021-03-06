"""
Part of the high-level python bindings for Kopano

Copyright 2018 - Kopano and its licensors (see LICENSE file for details)
"""

from MAPI.Tags import (
    PR_ADDRTYPE_W, PR_DISPLAY_NAME_W, PR_EMAIL_ADDRESS_W, PR_ENTRYID,
    PR_SEARCH_KEY, PR_RECIPIENT_TRACKSTATUS, PR_RECIPIENT_TRACKSTATUS_TIME,
    PR_RECIPIENT_TYPE,
)

from .address import Address
from .compat import repr as _repr

class Attendee(object):
    """Attendee class"""

    def __init__(self, server, mapirow):
        self.server = server
        self.mapirow = mapirow
        self.row = dict([(x.proptag, x) for x in mapirow])

    @property
    def address(self):
        args = [self.row[p].value if p in self.row else None for p in
                (PR_ADDRTYPE_W, PR_DISPLAY_NAME_W, PR_EMAIL_ADDRESS_W, PR_ENTRYID, PR_SEARCH_KEY)]

        return Address(self.server, *args, props=self.mapirow)

    @property
    def response(self):
        prop = self.row.get(PR_RECIPIENT_TRACKSTATUS)
        if prop:
            return {
                0: None,
                1: 'organizer',
                2: 'tentatively_accepted',
                3: 'accepted',
                4: 'declined',
                5: 'no_response',
            }.get(prop.value)

    @property
    def response_time(self):
        prop = self.row.get(PR_RECIPIENT_TRACKSTATUS_TIME)
        if prop:
            return prop.value

    @property
    def type_(self):
        # TODO is it just webapp which uses this?
        # (as there are explicit meeting properties for this)
        prop = self.row.get(PR_RECIPIENT_TYPE)
        if prop:
            return {
                1: 'required',
                2: 'optional',
                3: 'resource',
            }.get(prop.value)

    def __unicode__(self):
        return u'Attendee()'

    def __repr__(self):
        return _repr(self)
