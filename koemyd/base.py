# vi:ts=4:sw=4:syn=python

import uuid

class Base(object):
    def __init__(self): pass

class UUIDObject(Base):
    def __init__(self): self.__uuid = uuid.uuid4()

    @property
    def uuid(self): return self.__uuid.hex[:4]
