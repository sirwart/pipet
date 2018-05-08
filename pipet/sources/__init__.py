from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.schema import MetaData
from sqlalchemy.types import BigInteger, Text, DateTime

from pipet.utils import PipetBase


SCHEMANAME = 'pipet'


@as_declarative(metadata=MetaData(schema=SCHEMANAME))
class Base(PipetBase):
    pass


class Identity(Base):
    id = Column(Text, primary_key=True)
    created = Column(DateTime)
    type = Column(Text, primary_key=True)
    source = Column(Text, primary_key=True)
    source_id = Column(Text, primary_key=True)
    data = Column(JSONB)


class Event(Base):
    uuid = Column(Text, primary_key=True)
    created = Column(DateTime)
    type = Column(Text)
    data = Column(JSONB)


class Page(Base):
    """
    No anonymous visitor should be able to visit more than once a second
    """
    created = Column(DateTime, primary_key=True)
    url = Column(Text, primary_key=True)
    anonymous_id = Column(Text, primary_key=True)
    referrer = Column(Text)
    ip_address = Column(Text)
    user_id = Column(Text)
    session_id = Column(Text)
    data = Column(Text)


class Group(Base):
    created = Column(DateTime)
    user_id = Column(Text, primary_key=True)
    group_id = Column(Text, primary_key=True)
    data = Column(JSONB)
