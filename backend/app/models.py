from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Server(Base):
    __tablename__ = 'mqtt_server'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(Text)
    password: Mapped[str | None] = mapped_column(Text)
    tls: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    topics: Mapped[list['Topic']] = relationship('Topic', back_populates='server', cascade='all, delete-orphan')
    messages: Mapped[list['Message']] = relationship('Message', back_populates='server', cascade='all, delete-orphan')


class Topic(Base):
    __tablename__ = 'mqtt_topic'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey('mqtt_server.id'), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    qos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    direction: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    server: Mapped['Server'] = relationship('Server', back_populates='topics')


class Message(Base):
    __tablename__ = 'mqtt_message'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey('mqtt_server.id'), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    qos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    device_id: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    raw: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    server: Mapped['Server'] = relationship('Server', back_populates='messages')
