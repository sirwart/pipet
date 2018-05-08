from datetime import datetime
import uuid

from flask import url_for
from flask_login import UserMixin
from sqlalchemy import Column, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.types import Integer

from pipet import app, db
from pipet.sources import Base, SCHEMANAME


class User(db.Model, UserMixin):
    email = db.Column(db.Text, unique=True)
    name = db.Column(db.Text)
    role = db.Column(db.Text, default='owner')
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    verified = db.Column(db.Boolean, default=False)
    validation_hash = db.Column(db.Text)
    validation_hash_added = db.Column(db.DateTime)

    organization = db.relationship(
        'Organization', lazy='select', backref=db.backref('users'))

    def __init__(self, email, organization):
        self.email = email
        self.organization = organization

    def refresh_validation_hash(self):
        self.validation_hash = uuid.uuid4().hex
        self.validation_hash_added = datetime.now()

    def send_confirmation_email(self):
        if app.debug:
            print(url_for('login_with_validation',
                          validation_hash=self.validation_hash, _external=True))

        else:
            msg = EmailMessage()
            msg.set_content('Click here to confirm your email address: {}'.format(url_for(
                'login_with_validation', validation_hash=self.validation_hash, _external=True)))
            msg['Subject'] = 'Login to Pipet'
            msg['From'] = 'support@%s' % app.config['SERVER_NAME']
            msg['To'] = self.email
            s = smtplib.SMTP(os.environ['SMTP_SERVER'])
            s.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            s.send_message(msg)
            s.quit()


class Organization(db.Model):
    name = db.Column(db.Text, unique=True, nullable=False)
    database_credentials = db.Column(db.Text)
    api_key = db.Column(UUID(as_uuid=True), unique=True,
                        nullable=False, default=uuid.uuid4)

    def create_session(self):
        engine = create_engine(self.database_credentials, use_batch_mode=True)
        session_factory = sessionmaker(bind=engine)
        return scoped_session(session_factory)()

    def create_all(self, session):
        session.bind.execute(
            DDL('CREATE SCHEMA IF NOT EXISTS {schema}'.format(schema=SCHEMANAME)))
        Base.metadata.create_all(session.bind)
        self.initialized = True

    def drop_all(self, session):
        Base.metadata.drop_all(session.bind)
        session.bind.execute(
            DDL('DROP SCHEMA IF EXISTS {schema}'.format(schema=SCHEMANAME)))
        self.initialized = False
