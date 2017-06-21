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
from sqlalchemy.types import Boolean, Text, Integer, DateTime

from pipet import session
from pipet.models import Workspace

SCHEMANAME = 'zendesk'
ZENDESK_MODELS = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=ZENDESK_MODELS)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

    id = Column(Text, primary_key=True)

    @classmethod
    def get_or_create(cls, data):
        """
        Args:
            cls (Group):
            data (dict): JSON
        Return:
            tuple: (object, created)
        """
        inst = session.query(cls).get(str(data['id']))
        if inst:
            return inst.load_json(data), False

        inst = cls()
        return inst.load_json(data), True

    def __hash__(self):
        return hash(self.id)

    def load_json(self, data):
        for field, value in data.items():
            if field in self.__table__._columns.keys():
                if isinstance(self.__table__._columns.get(field).type, DateTime):
                    setattr(self, field,datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
                elif isinstance(self.__table__._columns.get(field).type, ARRAY):
                    setattr(self, field, sorted(value))
                elif isinstance(self.__table__._columns.get(field).type, Text) and \
                    (self.__table__._columns.get(field).foreign_keys or field == 'id'):
                    setattr(self, field, str(value))
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
    workspace_id = Column(Integer)

    # workspace = relationship('Workspace', backref=backref('zendesk_account', lazy='dynamic'))

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

    def create_target(self):
        target_payload = {'target': {
            'title': 'Pipet',
            'type': 'http_target',
            'active': True,
            'target_url': os.environ.get('PIPET_DOMAIN') + url_for('zendesk.hook'),
            'username': self.subdomain,
            'password': os.environ.get('FLASK_SECRET'),
            'method': 'post',
            'content_type': 'application/json',}}
        resp = requests.post(self.api_base_url + '/targets.json',
            auth=self.auth, json=target_payload)
        self.target_id = resp.json()['target']['id']

    def create_trigger(self):
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

    def destroy_target(self):
        requests.delete(self.api_base_url + '/targets/{id}.json'.format(id=self.target_id),
            auth=self.auth)
        self.target_id = None

    def destroy_trigger(self):
        requests.delete(self.api_base_url + '/triggers/{id}.json'.format(id=self.trigger_id),
            auth=self.auth)
        self.trigger_id = None

    def backfill(self, start_time=0):
        """Backfill Zendesk data when an account is created.
        Eventually, this should be a RQ task, but for not, just run from CLI"""
        user_results = []
        group_results = []
        ticket_results = []
        comment_results = []
        while True:
            resp = requests.get(self.api_base_url +
                '/incremental/tickets.json?include=users,groups&start_time={start_time}'.format(
                    start_time=start_time), auth=(self.auth))

            if resp.status_code != 200:
                print(resp.status_code)
                print(resp.content)
                break

            data = resp.json()
            if data['count'] == 0:
                break

            start_time = resp.json()['end_time']

            for user_json in data['users']:
                user, _ = User.get_or_create(user_json)
                user_results.append(user)

            for group_json in data['groups']:
                group, _ = Group.get_or_create(group_json)
                group_results.append(group)

            for ticket_json in data['tickets']:
                if ticket_json['status'] == 'deleted':
                    continue

                ticket, _ = Ticket.get_or_create(ticket_json)
                ticket_results.append(ticket)

                resp = requests.get(self.api_base_url + \
                    '/tickets/{id}/comments.json'.format(id=ticket.id),
                    auth=self.auth)
                
                assert resp.status_code == 200
                comment_results += ticket.update_comments(resp.json()['comments'])

        return user_results, group_results, ticket_results, comment_results


class TicketComment(Base):
    """Cannot be deleted (unless ticket is deleted)"""
    type = Column(Text)
    body = Column(Text)
    public = Column(Boolean)
    created_at = Column(DateTime)
    author_id = Column(Text, ForeignKey('user.id'))
    via = Column(JSONB)
    meta = Column(JSONB, name='metadata')
    ticket_id = Column(Text, ForeignKey('ticket.id'))

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

    # only_private_comments = Column(Boolean)
    # url = Column(Text)
    # two_factor_auth_enabled = Column(Boolean)
    # ticket_restriction = Column(Text)
    # suspended = Column(Boolean)
    # signature = Column(Text)
    # shared = Column(Boolean)
    # shared_agent = Column(Boolean)
    # restricted_agent
    # organization_id = Column(Integer)
    # default_group_id = Column(Integer)
    # custom_role_id = Column(Integer)
    # photo
    # user_fields


class Group(Base):
    created_at = Column(DateTime)
    deleted = Column(Boolean)
    name = Column(Text)
    updated_at = Column(DateTime)
    url = Column(Text)


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
    requester_id = Column(Text, ForeignKey('user.id'))
    submitter_id = Column(Text, ForeignKey('user.id'))
    group_id = Column(Text, ForeignKey('group.id'))
    collaborator_ids = Column(ARRAY(Text, dimensions=1))
    has_incidents = Column(Boolean)
    due_at = Column(DateTime)
    tags = Column(ARRAY(Text, dimensions=1))
    via = Column(JSONB)
    followup_ids = Column(ARRAY(Text, dimensions=1))

    # forum_topic_id = Column(Text, ForeignKey(''))
    # satisfaction_rating = Column(JSONB)
    # sharing_agreement_ids = Column(ARRAY(Text, dimensions=1))
    # custom_fields
    # ticket_form_id
    # branch_id
    # allow_channelback
    # is_public

    account_id = Column(Integer, ForeignKey('account.id'))
    account = relationship('Account', backref=backref('tickets', lazy='dynamic'))

    def update(self, extended_json):
        """Updates from API"""
        inst_list = [self]

        for user_data in extended_json['users']:
            user, _ = User.get_or_create(user_data)
            inst_list.append(user)

        for group_data in extended_json['groups']:
            group, _ = Group.get_or_create(group_data)
            inst_list.append(group)

        return inst_list

    def update_comments(self, comments_json):
        comments = []
        for comment_json in comments_json:
            comment, _ = TicketComment.get_or_create(comment_json)
            comments.append(comment)

        return comments
