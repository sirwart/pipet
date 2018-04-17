from datetime import datetime
import requests
import os

from flask import url_for
from flask_sqlalchemy import camel_to_snake_case
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import Column
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.types import BigInteger, Boolean, Text, Integer, DateTime

SCHEMANAME = 'zendesk'
ZENDESK_MODELS = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=ZENDESK_MODELS)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

    id = Column(BigInteger, primary_key=True)

    @classmethod
    def create_or_update(cls, session, data, account):
        """
        Args:
            cls (Group):
            data (dict): JSON
        Return:
            tuple: (object, created)
        """
        inst = session.query(cls).get(data['id'])
        if inst:
            return inst.load_json(data), False

        inst = cls()
        return inst.load_json(data), True

    def __hash__(self):
        return hash(self.id)

    def fetch(self, account):
        return requests.get(account.base_url + '/{endpoint}/{id}.json'.format(endpoint=self.endpoint, id=self.id),
                            auth=account.auth)

    def load_json(self, data):
        for field, value in data.items():
            if field in self.__table__._columns.keys():
                if isinstance(self.__table__._columns.get(field).type, DateTime) and value:
                    setattr(self, field, datetime.strptime(
                        value, '%Y-%m-%dT%H:%M:%SZ'))
                elif isinstance(self.__table__._columns.get(field).type, ARRAY):
                    setattr(self, field, sorted(value))
                elif isinstance(self.__table__._columns.get(field).type, BigInteger) and \
                        (self.__table__._columns.get(field).foreign_keys or field == 'id'):
                    setattr(self, field, value)
                else:
                    setattr(self, field, value)
        return self


class TicketComment(Base):
    """Cannot be deleted (unless ticket is deleted)"""
    type = Column(Text)
    body = Column(Text)
    public = Column(Boolean)
    created_at = Column(DateTime)
    author_id = Column(BigInteger, ForeignKey(
        'user.id', deferrable=True, initially='DEFERRED'))
    via = Column(JSONB)
    meta = Column(JSONB, name='metadata')
    ticket_id = Column(BigInteger, ForeignKey(
        'ticket.id', deferrable=True, initially='DEFERRED'))

    # attachments

    ticket = relationship(
        'Ticket', backref=backref('comments', lazy='dynamic'))
    author = relationship('User', backref=backref('comments', lazy='dynamic'))


class User(Base):
    endpoint = 'users'

    email = Column(Text)
    name = Column(Text)
    active = Column(Boolean)
    alias = Column(Text)
    chat_only = Column(Boolean)
    created_at = Column(DateTime)
    details = Column(Text)
    external_id = Column(Text)
    last_login_at = Column(DateTime)
    locale = Column(Text)
    locale_id = Column(Integer)
    moderator = Column(Boolean)
    notes = Column(Text)
    phone = Column(Text)
    role = Column(Text)
    tags = Column(ARRAY(Text, dimensions=1))
    time_zone = Column(Text)
    updated_at = Column(DateTime)
    verified = Column(Boolean)

    # only_private_comments = Column(Boolean)
    # url = Column(Text)
    # two_factor_auth_enabled = Column(Boolean)
    # ticket_restriction = Column(Text)
    # suspended = Column(Boolean)
    # signature = Column(Text)
    # shared = Column(Boolean)
    # shared_agent = Column(Boolean)
    # restricted_agent
    # organization_id = Column(BigInteger)
    # default_group_id = Column(BigInteger)
    # custom_role_id = Column(Integer)
    # photo
    # user_fields


class Group(Base):
    endpoint = 'groups'

    created_at = Column(DateTime)
    deleted = Column(Boolean)
    name = Column(Text)
    updated_at = Column(DateTime)
    url = Column(Text)


class Organization(Base):
    endpoint = 'organizations'

    external_id = Column(Text)
    name = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    domain_names = Column(ARRAY(Text, dimensions=1))
    details = Column(Text)
    notes = Column(Text)
    group_id = Column(BigInteger, ForeignKey(
        'group.id', deferrable=True, initially='DEFERRED'))
    shared_tickets = Column(Boolean)
    shared_comments = Column(Boolean)
    tags = Column(ARRAY(Text, dimensions=1))
    organization_fields = Column(JSONB)


class Ticket(Base):
    endpoint = 'tickets'

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
    requester_id = Column(BigInteger, ForeignKey(
        'user.id', deferrable=True, initially='DEFERRED'))
    submitter_id = Column(BigInteger, ForeignKey(
        'user.id', deferrable=True, initially='DEFERRED'))
    group_id = Column(BigInteger, ForeignKey(
        'group.id', deferrable=True, initially='DEFERRED'))
    collaborator_ids = Column(ARRAY(BigInteger, dimensions=1))
    has_incidents = Column(Boolean)
    due_at = Column(DateTime)
    tags = Column(ARRAY(Text, dimensions=1))
    via = Column(JSONB)
    followup_ids = Column(ARRAY(BigInteger, dimensions=1))

    # forum_topic_id = Column(BigInteger, ForeignKey('')), deferrable=True, initially='DEFERRED'
    # satisfaction_rating = Column(JSONB)
    # sharing_agreement_ids = Column(ARRAY(BigInteger, dimensions=1))
    # custom_fields
    # ticket_form_id
    # branch_id
    # allow_channelback
    # is_public

    def update(self, session, extended_json, account):
        """Updates from API"""
        inst_list = [self]

        for user_data in extended_json['users']:
            user, _ = User.create_or_update(session, user_data, account)
            inst_list.append(user)

        for group_data in extended_json['groups']:
            group, _ = Group.create_or_update(
                session, group_data, account)
            inst_list.append(group)

        return inst_list

    def update_comments(self, session, comments_json, account):
        comments = []
        users = []
        for comment_json in comments_json:
            if not session.query(User).get(comment_json['author_id']) and comment_json['author_id'] not in [user.id for user in users]:
                user = User()
                user.id = comment_json['author_id']
                user_resp = user.fetch(account)
                user.load_json(user_resp.json())
                users.append(user)

            comment, _ = TicketComment.create_or_update(
                session, comment_json, account)
            comment.ticket_id = self.id
            comments.append(comment)

        return comments, users
