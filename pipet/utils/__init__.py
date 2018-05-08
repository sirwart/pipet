from flask_sqlalchemy import camel_to_snake_case
from inflection import tableize
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declared_attr

from sqlalchemy.types import BigInteger


class PipetBase():
    @declared_attr
    def __tablename__(cls):
        return tableize(cls.__name__)

    @classmethod
    def upsert(cls, data):
        """
        Args:
            cls (Group):
            data (dict): JSON
        Return:
            tuple: (object, created)
        """
        return insert(cls.__table__).values(**data).on_conflict_do_update(index_elements=[cls.id], set_=data)

    def __hash__(self):
        return hash(self.id)
