from datetime import datetime
import os

from flask import url_for
from requests.exceptions import HTTPError
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import MetaData
from sqlalchemy.types import BigInteger, Boolean, Text, Integer, DateTime

from pipet.utils import PipetBase


SCHEMANAME = 'zendesk'
CLASS_REGISTRY = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=CLASS_REGISTRY)
class Base(PipetBase):
    id = Column(BigInteger, primary_key=True)

    @classmethod
    def parse(cls, data):
        d = {}
        for field, column in cls.__table__._columns.items():
            # metadata is not a valid column name
            value = data.get('meta' if field == 'metadata' else field, None)
            if not value:
                continue
            elif isinstance(column.type, DateTime):
                # We assume GMT
                d[field] = datetime.strptime(value[:19], '%Y-%m-%dT%H:%M:%S')
            else:
                d[field] = value
        return d

    @classmethod
    def process_response(cls, response):
        raise NotImplemented

    @classmethod
    def sync(cls, account):
        """
        Return:
            statements (list): list of insert insertments
            cursor (str): cursor for sync
            has_more (bool): continue sync'ing
        """
        statements = []
        cursor = account.cursors.get(cls.__tablename__, '0')

        resp = account.get(cls.endpoint.format(cursor=cursor))

        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 429:
                return statements, cursor, False
            raise HTTPError

        statements += cls.process_response(resp)
        cursor = resp.json()['end_time']
        return statements, cursor, resp.json()['count'] == 1000


class UserIdentity(Base):
    url = Column(Text)
    user_id = Column(BigInteger)
    type = Column(Text)
    value = Column(Text)
    verified = Column(Boolean)
    primary = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    undelivered_count = Column(BigInteger)
    deliverable_sate = Column(Text)

    @classmethod
    def sync(cls, account):
        # synced from User.sync
        return [], None, False


class User(Base):
    email = Column(Text)
    name = Column(Text)
    active = Column(Boolean)
    alias = Column(Text)
    chat_only = Column(Boolean)
    created_at = Column(DateTime)
    custom_role_id = Column(BigInteger)
    role_type = Column(BigInteger)
    details = Column(Text)
    external_id = Column(Text)
    last_login_at = Column(DateTime)
    locale = Column(Text)
    locale_id = Column(BigInteger)
    moderator = Column(Boolean)
    notes = Column(Text)
    only_private_comments = Column(Boolean)
    organization_id = Column(BigInteger)
    default_group_id = Column(BigInteger)
    phone = Column(Text)
    shared_phone_number = Column(Boolean)
    # photo
    restricted_agent = Column(Boolean)
    role = Column(Text)
    shared = Column(Boolean)
    shared_agent = Column(Boolean)
    signature = Column(Text)
    suspended = Column(Boolean)
    tags = Column(ARRAY(Text, dimensions=1))
    ticket_restriction = Column(Text)
    time_zone = Column(Text)
    two_factor_auth_enabled = Column(Boolean)
    updated_at = Column(DateTime)
    verified = Column(Boolean)
    url = Column(Text)
    user_fields = Column(JSONB)
    verified = Column(Boolean)

    endpoint = '/api/v2/incremental/users.json?start_time={cursor}&include=identities'

    @classmethod
    def process_response(cls, response):
        statements = []
        for data in response.json().get('users', []):
            statements.append(cls.upsert(cls.parse(data)))

        for identity_data in response.json().get('identities', []):
            statements.append(UserIdentity.upsert(
                UserIdentity.parse(identity_data)))

        return statements


class Group(Base):
    endpoint = 'groups'

    created_at = Column(DateTime)
    deleted = Column(Boolean)
    name = Column(Text)
    updated_at = Column(DateTime)
    url = Column(Text)

    endpoint = '/api/v2/groups.json'

    @classmethod
    def process_response(cls, response):
        statements = []
        for data in response.json().get('groups', []):
            statements.append(cls.upsert(cls.parse(data)))
        return statements

    @classmethod
    def sync(cls, account):
        """
        Returns:
            (list): statements to execute
            (str): cursor
            (bool): whether to call again immediately
        """
        return [], None, False


class Organization(Base):
    external_id = Column(Text)
    name = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    domain_names = Column(ARRAY(Text, dimensions=1))
    details = Column(Text)
    notes = Column(Text)
    group_id = Column(BigInteger)
    shared_tickets = Column(Boolean)
    shared_comments = Column(Boolean)
    tags = Column(ARRAY(Text, dimensions=1))
    organization_fields = Column(JSONB)

    endpoint = '/api/v2/incremental/organizations.json?start_time={cursor}'

    @classmethod
    def process_response(cls, response):
        statements = []
        for data in response.json().get('organizations', []):
            statements.append(cls.upsert(cls.parse(data)))

        return statements


# class TicketAudit(Base):
#     ticket_id = Column(BigInteger)
#     meta = Column(JSONB, name='metadata')
#     via = Column(JSONB)
#     created_at = Column(DateTime)
#     author_id = Column(BigInteger)
#     events = Column(JSONB)

#     endpoint = '/api/v2/incremental/ticket_events.json?start_time={cursor}&include=comment_events'

#     @classmethod
#     def process_response(cls, response):
#         statements = []
#         for data in response.json()['ticket_events']:
#             data['events'] = data['child_events']
#             statements.append(cls.upsert(cls.parse(data)))

#         return statements


class Ticket(Base):
    """Can be deleted by admins"""
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    external_id = Column(Text)
    type = Column(Text)
    subject = Column(Text)
    description = Column(Text)
    priority = Column(Text)
    status = Column(Text)
    recipient = Column(Text)
    requester_id = Column(BigInteger)
    submitter_id = Column(BigInteger)
    group_id = Column(BigInteger)
    collaborator_ids = Column(ARRAY(BigInteger, dimensions=1))
    has_incidents = Column(Boolean)
    due_at = Column(DateTime)
    tags = Column(ARRAY(Text, dimensions=1))
    via = Column(JSONB)
    followup_ids = Column(ARRAY(BigInteger, dimensions=1))

    # forum_topic_id = Column(BigInteger)
    # satisfaction_rating = Column(JSONB)
    # sharing_agreement_ids = Column(ARRAY(BigInteger, dimensions=1))
    # custom_fields
    # ticket_form_id
    # branch_id
    # allow_channelback
    # is_public

    endpoint = '/api/v2/incremental/tickets.json?start_time={cursor}&include=groups'

    @classmethod
    def process_response(cls, response):
        statements = []
        for data in response.json().get('tickets', []):
            statements.append(cls.upsert(cls.parse(data)))

        for data in response.json().get('groups', []):
            statements.append(Group.upsert(Group.parse(data)))

        return statements
