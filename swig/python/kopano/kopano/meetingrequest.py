"""
Part of the high-level python bindings for Kopano

Copyright 2017 - Kopano and its licensors (see LICENSE file for details)
"""

import datetime
import struct

from MAPI import (
    MAPI_UNICODE, MODRECIP_MODIFY, KEEP_OPEN_READWRITE, RELOP_EQ,
)

from MAPI.Tags import (
    PR_DISPLAY_NAME_W, PR_RECIPIENT_TRACKSTATUS, PR_MESSAGE_RECIPIENTS,
    PR_MESSAGE_CLASS,
    IID_IMAPITable, IID_IMessage,
)

from MAPI.Defs import (
    PpropFindProp
)

from MAPI.Struct import (
    SPropValue, SPropertyRestriction,
)

from .compat import repr as _repr, hex as _hex
from .errors import Error
from .restriction import Restriction

class MeetingRequest(object):
    def __init__(self, item):
        self.item = item

    @property
    def calendar_item(self):
        """ Global calendar item :class:`item <Item>` """

        goid = self.item.prop('meeting:35')

        restriction = Restriction(SPropertyRestriction(
            RELOP_EQ, goid.proptag, SPropValue(goid.proptag, goid.mapiobj.Value))
        )
        return self.item.store.calendar.items(restriction).next() # XXX store

    @property
    def basedate(self):
        """ Exception date """

        blob = self.item.prop('meeting:3').value
        y, m, d = struct.unpack_from('>HBB', blob, 16)
        if (y, m, d) != (0, 0, 0):
            return datetime.datetime(y, m, d)

    @property
    def update_counter(self):
        """ Update counter """

        return self.item.prop('appointment:33281').value

    @property
    def track_status(self):
        """ Track status """

        return {
            'IPM.Schedule.Meeting.Resp.Pos': 3, # XXX hard-coded
            'IPM.Schedule.Meeting.Resp.Tent': 2,
            'IPM.Schedule.Meeting.Resp.Neg': 4,
        }.get(self.item.message_class)

    @property
    def is_request(self):
        return self.item.message_class == 'IPM.Schedule.Meeting.Request'

    @property
    def is_response(self):
        return self.item.message_class.startswith('IPM.Schedule.Meeting.Resp.')

    @property
    def is_cancellation(self):
        return self.item.message_class == 'IPM.Schedule.Meeting.Canceled'

    def accept(self, tentative=False, response=True):
        """ Accept meeting request

        :param tentative: accept tentatively?
        :param response: send response message?
        """

        if tentative:
            self._accept('IPM.Schedule.Meeting.Resp.Tent', response=response)
        else:
            self._accept('IPM.Schedule.Meeting.Resp.Pos', response=response)

    def decline(self, response=True):
        """ Decline meeting request

        :param response: send response message?
        """
        self._accept('IPM.Schedule.Meeting.Resp.Neg', response=response)

    def _accept(self, message_class, response=True):
        if not self.is_request:
            raise Error('item is not a meeting request')

        cal_item = self.calendar_item
        calendar = self.item.store.calendar # XXX

        if cal_item:
            if self.update_counter <= cal_item.meetingrequest.update_counter:
                raise Error('trying to accept out-of-date meeting request')
            calendar.delete(cal_item)

        cal_item = self.item.copy(self.item.store.calendar)
        cal_item.message_class = 'IPM.Appointment'

        if response:
            response = self.item.copy(self.item.store.outbox)
            response.subject = 'Accepted: ' + self.item.subject
            response.message_class = message_class
            response.to = self.item.server.user(email=self.item.from_.email) # XXX
            response.from_ = self.item.store.user # XXX slow?
            response.send()

    def process_cancellation(self): # XXX very similar to process_response, _accept?
        """ Process meeting request cancellation """

        if not self.is_cancellation:
            raise Error('item is not a meeting request cancellation')

        cal_item = self.calendar_item
        basedate = self.basedate
        calendar = self.item.store.calendar # XXX

        # modify calendar item or embedded message (in case of exception)
        attach = None
        if basedate:
            for message in cal_item.embedded_items(): # XXX no cal_item?
                if message.prop('appointment:33320').value.date() == basedate.date(): # XXX date
                    attach = message._attobj
                    break
            # XXX not found: create exception
        else:
            message = cal_item

        # update properties
        self.item.mapiobj.CopyTo([], [], 0, None, IID_IMessage, message.mapiobj, 0)
        message.mapiobj.SetProps([SPropValue(PR_MESSAGE_CLASS, 'IPM.Appointment')])

        # save all the things
        message.mapiobj.SaveChanges(KEEP_OPEN_READWRITE)
        if attach:
            attach.SaveChanges(KEEP_OPEN_READWRITE)
            cal_item.mapiobj.SaveChanges(KEEP_OPEN_READWRITE)

    def process_response(self):
        """ Process meeting request response """

        if not self.is_response:
            raise Error('item is not a meeting request response')

        cal_item = self.calendar_item
        basedate = self.basedate

        # modify calendar item or embedded message (in case of exception)
        attach = None
        if basedate:
            for message in cal_item.embedded_items(): # XXX no cal_item?
                if message.prop('appointment:33320').value.date() == basedate.date(): # XXX date
                    attach = message._attobj # XXX
                    break
        else:
            message = cal_item

        # update recipient track status # XXX partially to recurrence.py
        table = message.mapiobj.OpenProperty(PR_MESSAGE_RECIPIENTS, IID_IMAPITable, MAPI_UNICODE, 0)
        rows = table.QueryRows(-1, 0)
        for row in rows:
            disp = PpropFindProp(row, PR_DISPLAY_NAME_W)
            if disp.Value == self.item.from_.name: # XXX resolving
                row.append(SPropValue(PR_RECIPIENT_TRACKSTATUS, self.track_status)) # XXX append

        message.mapiobj.ModifyRecipients(MODRECIP_MODIFY, rows)

        # save all the things
        message.mapiobj.SaveChanges(KEEP_OPEN_READWRITE)
        if attach:
            attach.SaveChanges(KEEP_OPEN_READWRITE)
            cal_item.mapiobj.SaveChanges(KEEP_OPEN_READWRITE)

    def __unicode__(self):
        return u'MeetingRequest()'

    def __repr__(self):
        return _repr(self)