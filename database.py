import os
from sqlalchemy import (
        create_engine,
        Column,
        BigInteger,
        String,
        Integer)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config



def start() -> scoped_session:
    engine = create_engine(Config.DB_URI)
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


try:
    BASE = declarative_base()
    SESSION = start()

except AttributeError as e:
    raise e


class ChatData(BASE):
    __tablename__ = "chatdata"
    chat_id = Column(BigInteger, primary_key=True)
    vote_count = Column(Integer)
    delete_timeout = Column(Integer)
    locale = Column(String)

    def __init__(
            self,
            chat_id,
            vote_count,
            delete_timeout,
            locale):
        self.chat_id = chat_id
        self.vote_count = vote_count
        self.delete_timeout = delete_timeout
        self.locale = locale


ChatData.__table__.create(checkfirst=True)


def mod_or_make_chat(chat_id,
                     vote_count=None,
                     delete_timeout=None,
                     locale=None):
    try:
        chat = SESSION.query(ChatData).get(chat_id)
        if chat:
            if vote_count:
                chat.vote_count = vote_count
            if delete_timeout:
                chat.delete_timeout = delete_timeout
            if locale:
                chat.locale = locale
        else:
            chat = ChatData(chat_id, vote_count, delete_timeout, locale)
            SESSION.add(chat)
        SESSION.commit()
        SESSION.close()
        return 'success'
    except:
        return str(Exception)


def get_chat(chat_id):
    try:
        return SESSION.query(ChatData).get(chat_id)
    except:
        return None
    finally:
        SESSION.close()

