from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import camel_to_snake_case
from sqlalchemy import Column
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.types import Boolean, Text, Integer, DateTime
from werkzeug.security import generate_password_hash, check_password_hash

TABLES = {}

@as_declarative(class_registry=TABLES)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

class Workspace(UserMixin, Base):
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True)
    password_hash = Column(Text)

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
