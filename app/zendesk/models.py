from datetime import datetime
import os

from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from flask_sqlalchemy import camel_to_snake_case
from sqlalchemy import Column
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.types import Boolean, Text, Integer, DateTime

from app import db

SCHEMANAME = 'zendesk'
TABLES = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=TABLES)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

    def load_json(self, data):
        for field, value in data.items():
            if field in self.__table__._columns.keys():
                if isinstance(self.__table__._columns.get(field).type, DateTime):
                    setattr(self, field,datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
                elif isinstance(self.__table__._columns.get(field).type, ARRAY):
                    setattr(self, field, sorted(value))
                else:
                    setattr(self, field, value)


class Account(Base):
    id = Column(Integer, primary_key=True)
    subdomain = Column(Text)
    admin_email = Column(Text)
    api_key = Column(Text)
    trigger_id = Column(Integer)
    target_id = Column(Integer)

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


class TicketComment(Base):
    """Cannot be deleted (unless ticket is deleted)"""
    id = Column(Integer, primary_key=True)
    type = Column(Text)
    body = Column(Text)
    public = Column(Boolean)
    created_at = Column(DateTime)
    author_id = Column(Integer, ForeignKey('user.id'))
    via = Column(JSONB)
    meta = Column(JSONB, name='metadata')
    ticket_id = Column(Integer, ForeignKey('ticket.id'))

    # attachments

    ticket = relationship('Ticket', backref=backref('comments', lazy='dynamic'))
    author = relationship('User', backref=backref('comments', lazy='dynamic'))


class User(Base):
    id = Column(Integer, primary_key=True)
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
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    deleted = Column(Boolean)
    name = Column(Text)
    updated_at = Column(DateTime)
    url = Column(Text)


class Ticket(Base):
    """Can be deleted by admins"""
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    external_id = Column(Text)
    type = Column(Text)
    subject = Column(Text)
    description = Column(Text)
    priority = Column(Text)
    status = Column(Text)
    recipient = Column(Text)
    requester_id = Column(Integer, ForeignKey('user.id'))
    submitter_id = Column(Integer, ForeignKey('user.id'))
    group_id = Column(Integer, ForeignKey('group.id'))
    collaborator_ids = Column(ARRAY(Integer, dimensions=1))
    has_incidents = Column(Boolean)
    due_at = Column(DateTime)
    tags = Column(ARRAY(Text, dimensions=1))
    via = Column(JSONB)
    followup_ids = Column(ARRAY(Integer, dimensions=1))

    # forum_topic_id = Column(Integer, ForeignKey(''))
    # satisfaction_rating = Column(JSONB)
    # sharing_agreement_ids = Column(ARRAY(Integer, dimensions=1))
    # custom_fields
    # ticket_form_id
    # branch_id
    # allow_channelback
    # is_public

    account_id = Column(Integer, ForeignKey('account.id'))
    account = relationship('Account', backref=backref('tickets', lazy='dynamic'))

    def update(self):
        """Updates from API"""
        inst_list = [self]

        d = requests.get(self.account.api_base_url + \
            '/tickets/{id}.json?include=users,groups'.format(id=self.id),
            auth=self.account.auth).json()
        self.load_json(d['ticket'])

        if not User.query.filter(id=self.requester_id).first():
            requester = User()
            requester.load_json([x for x in d['users'] if x['id'] == self.requester_id][0])
            inst_list.append(requester)

        if not User.query.filter(id=self.submitter_id).first():
            submitter = User()
            submitter.load_json([x for x in d['users'] if x['id'] == self.submitter_id][0])
            inst_list.append(submitter)

        if not Group.query.filter(id=self.group_id).first():
            group = Group()
            group.load_json([x for x in d['groups'] if x['id'] == self.group_id][0])
            inst_list.append(group)

        return inst_list

    def update_comments(self):
        resp = requests.get(self.account.api_base_url + \
            '/tickets/{id}/comments.json'.format(id=self.id), auth=self.account.auth)

        comments = []
        for d in resp.json()['comments']:
            if TicketComment.query.filter_by(id=d['id']).first():
                pass

            comment = TicketComment()
            comment.load_json(d)
            comments.append(comment)

        return comments
