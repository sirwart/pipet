from flask_sqlalchemy import camel_to_snake_case
from sqlalchemy import Column
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.types import Boolean, Text, Integer, DateTime

from app import db

SCHEMANAME = 'stripe'
TABLES = {}

@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=TABLES)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)


class Account(Base):
    id = Column(Integer, primary_key=True)
    api_key = Column(Text)


class BalanceTransaction(Base):
    __tablename__ = 'balance_transactions'

    id = Column(Text, primary_key=True)
    amount = Column(Integer)
    available_on = Column(DateTime)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    fee = Column(Integer)
    net = Column(Integer)
    status = Column(Text)
    type = Column(Text)
    source_id = Column(Text)
    # automatic_transfer_id = Column(Integer, ForeignKey('transfers.id'))


class BalanceTransactionFeeDetail(Base):
    __tablename__ = 'balance_transaction_fee_details'

    balance_transaction_id = Column(Text, ForeignKey('balance_transactions.id'), primary_key=True)
    amount = Column(Integer)
    application = Column(Text)
    currency = Column(Text)
    description = Column(Text)
    type = Column(Text)


class Charge(Base):
    __tablename__ = 'charges'
    
    id = Column(Text, primary_key=True)
    amount = Column(Integer)
    amount_refunded = Column(Integer)
    application_fee_id = Column(Text)
    balance_transaction_id = Column(Text, ForeignKey('balance_transactions.id'))
    captured = Column(Boolean)
    created = Column(DateTime)
