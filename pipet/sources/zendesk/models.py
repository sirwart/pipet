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

from pipet import session
from pipet.models import Workspace

SCHEMANAME = 'zendesk'
ZENDESK_MODELS = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=ZENDESK_MODELS)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

    id = Column(BigInteger, primary_key=True)

    @classmethod
    def create_or_update(cls, data, account):
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
        inst.account = account
        return inst.load_json(data), True

    def __hash__(self):
        return hash(self.id)

    def load_json(self, data):
        for field, value in data.items():
            if field in self.__table__._columns.keys():
                if isinstance(self.__table__._columns.get(field).type, DateTime) and value:
                    setattr(self, field, datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))
                elif isinstance(self.__table__._columns.get(field).type, ARRAY):
                    setattr(self, field, sorted(value))
                elif isinstance(self.__table__._columns.get(field).type, BigInteger) and \
                    (self.__table__._columns.get(field).foreign_keys or field == 'id'):
                    setattr(self, field, value)
                else:
                    setattr(self, field, value)
        return self


class Account(Base):
    id = Column(Integer, primary_key=True)
    subdomain = Column(Text)
    admin_email = Column(Text)
    api_key = Column(Text)
    trigger_id = Column(Text)
    target_id = Column(Text)
    workspace_id = Column(Integer, ForeignKey(Workspace.id), unique=True)

    workspace = relationship(Workspace, backref=backref('zendesk_account', lazy='dynamic'))

    def __init__(self, subdomain, admin_email, api_key, workspace_id):
        self.subdomain = subdomain
        self.admin_email = admin_email
        self.api_key = api_key
        self.workspace_id = workspace_id

    @property
    def api_base_url(self):
        return 'https://{subdomain}.zendesk.com/api/v2'.format(subdomain=self.subdomain)

    @property
    def auth(self):
        return (self.admin_email + '/token', self.api_key)

    @property
    def target_exists(self):
        resp = requests.get(self.api_base_url + '/targets/{id}.json'.format(id=self.target_id))
        if resp.status_code == 200:
            return True
        return False

    @property
    def trigger_exists(self):
        resp = requests.get(self.api_base_url + '/triggers/{id}.json'.format(id=self.target_id))
        if resp.status_code == 200:
            return True
        return False

    def create_target(self):
        if self.target_id:
            return False

        target_payload = {'target': {
            'title': 'Pipet',
            'type': 'http_target',
            'active': True,
            'target_url': 'https://' + os.environ.get('PIPET_DOMAIN') + url_for('zendesk.hook'),
            'username': self.subdomain,
            'password': self.api_key,
            'method': 'post',
            'content_type': 'application/json',}}
        resp = requests.post(self.api_base_url + '/targets.json',
            auth=self.auth, json=target_payload)
        assert resp.status_code == 201
        self.target_id = resp.json()['target']['id']
        return True

    def create_trigger(self):
        if self.trigger_id:
            return False

        trigger_payload = {'trigger': {
            'actions': [{
                'field': 'notification_target',
                'value': [str(self.target_id), '{"id": {{ticket.id}}}']
            }],
            'active': True,
            'conditions': {
                'all': [],
                'any': [
                    {'field': 'update_type', 'operator': 'is', 'value': 'Create'},
                    {'field': 'update_type', 'operator': 'is', 'value': 'Change'}
                ]
            },
            'description': None,
            'title': 'Pipet Trigger',
        }}

        resp = requests.post(self.api_base_url + '/triggers.json',
            auth=self.auth, json=trigger_payload)
        self.trigger_id = resp.json()['trigger']['id']
        return True

    def destroy_target(self):
        requests.delete(self.api_base_url + '/targets/{id}.json'.format(id=self.target_id),
            auth=self.auth)
        self.target_id = None

    def destroy_trigger(self):
        requests.delete(self.api_base_url + '/triggers/{id}.json'.format(id=self.trigger_id),
            auth=self.auth)
        self.trigger_id = None


class TicketComment(Base):
    """Cannot be deleted (unless ticket is deleted)"""
    type = Column(Text)
    body = Column(Text)
    public = Column(Boolean)
    created_at = Column(DateTime)
    author_id = Column(BigInteger, ForeignKey('user.id', deferrable=True, initially='DEFERRED'))
    via = Column(JSONB)
    meta = Column(JSONB, name='metadata')
    ticket_id = Column(BigInteger, ForeignKey('ticket.id', deferrable=True, initially='DEFERRED'))

    # attachments

    ticket = relationship('Ticket', backref=backref('comments', lazy='dynamic'))
    author = relationship('User', backref=backref('comments', lazy='dynamic'))


class User(Base):
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

    account_id = Column(Integer, ForeignKey('account.id', deferrable=True, initially='DEFERRED'))
    account = relationship(Account, backref=backref('users', lazy='dynamic'))

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

    def fetch(self):
        return requests.get(self.account.api_base_url + '/users/{id}.json'.format(id=self.id),
            auth=self.account.auth)


class Group(Base):
    created_at = Column(DateTime)
    deleted = Column(Boolean)
    name = Column(Text)
    updated_at = Column(DateTime)
    url = Column(Text)

    account_id = Column(Integer, ForeignKey('account.id', deferrable=True, initially='DEFERRED'))
    account = relationship(Account, backref=backref('groups', lazy='dynamic'))

    def fetch(self):
        return requests.get(self.account.api_base_url + '/groups/{id}.json'.format(id=self.id),
            auth=self.account.auth)


class Organization(Base):
    external_id = Column(Text)
    name = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    domain_names = Column(ARRAY(Text, dimensions=1))
    details = Column(Text)
    notes = Column(Text)
    group_id = Column(BigInteger, ForeignKey('group.id', deferrable=True, initially='DEFERRED'))
    shared_tickets = Column(Boolean)
    shared_comments = Column(Boolean)
    tags = Column(ARRAY(Text, dimensions=1))
    organization_fields = Column(JSONB)

    account_id = Column(Integer, ForeignKey('account.id', deferrable=True, initially='DEFERRED'))
    account = relationship(Account, backref=backref('organizations', lazy='dynamic'))

    def fetch(self):
        return requests.get(self.account.api_base_url + '/organizations/{id}.json'.format(id=self.id),
            auth=self.account.auth)


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
    requester_id = Column(BigInteger, ForeignKey('user.id', deferrable=True, initially='DEFERRED'))
    submitter_id = Column(BigInteger, ForeignKey('user.id', deferrable=True, initially='DEFERRED'))
    group_id = Column(BigInteger, ForeignKey('group.id', deferrable=True, initially='DEFERRED'))
    collaborator_ids = Column(ARRAY(BigInteger, dimensions=1))
    has_incidents = Column(Boolean)
    due_at = Column(DateTime)
    tags = Column(ARRAY(Text, dimensions=1))
    via = Column(JSONB)
    followup_ids = Column(ARRAY(BigInteger, dimensions=1))

    account_id = Column(Integer, ForeignKey('account.id', deferrable=True, initially='DEFERRED'))
    account = relationship(Account, backref=backref('tickets', lazy='dynamic'))

    # forum_topic_id = Column(BigInteger, ForeignKey('')), deferrable=True, initially='DEFERRED'
    # satisfaction_rating = Column(JSONB)
    # sharing_agreement_ids = Column(ARRAY(BigInteger, dimensions=1))
    # custom_fields
    # ticket_form_id
    # branch_id
    # allow_channelback
    # is_public

    def fetch(self):
        return requests.get(self.account.api_base_url + '/tickets/{id}.json'.format(id=self.id),
            auth=self.account.auth)

    def update(self, extended_json):
        """Updates from API"""
        inst_list = [self]

        for user_data in extended_json['users']:
            user, _ = User.create_or_update(user_data, self.account)
            inst_list.append(user)

        for group_data in extended_json['groups']:
            group, _ = Group.create_or_update(group_data, self.account)
            inst_list.append(group)

        return inst_list

    def update_comments(self, comments_json):
        comments = []
        for comment_json in comments_json:
            if not session.query(User).get(comment_json['author_id']):
                user = User()
                user.id = comment_json['author_id']
                user.account = self.account
                user_resp = user.fetch()
                user.load_json(user_resp.json())
                comments.append(user)

            comment, _ = TicketComment.create_or_update(comment_json, self.account)
            comment.ticket_id = self.id
            comments.append(comment)

        return comments
