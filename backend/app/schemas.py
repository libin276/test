from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DirectionType = Literal['上行', '下行']


class ServerBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, max_length=100)
    tls: bool = False
    enabled: bool = True
    remark: str | None = Field(default=None, max_length=255)


class ServerCreate(ServerBase):
    pass


class ServerUpdate(ServerBase):
    pass


class ServerToggle(BaseModel):
    enabled: bool


class ServerRead(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    topic_count: int
    updated_at: datetime


class TopicBase(BaseModel):
    server_id: int
    topic: str = Field(min_length=1, max_length=255)
    qos: int = Field(default=0, ge=0, le=2)
    direction: DirectionType | None = None
    enabled: bool = True
    remark: str | None = Field(default=None, max_length=255)


class TopicCreate(TopicBase):
    pass


class TopicUpdate(TopicBase):
    pass


class TopicToggle(BaseModel):
    enabled: bool


class TopicRead(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_name: str
    updated_at: datetime


class MessageRead(BaseModel):
    id: int
    server_id: int
    server_name: str
    topic: str
    payload: str
    qos: int
    device_id: str | None
    direction: DirectionType
    raw: str | None
    timestamp: datetime


class MessageListResponse(BaseModel):
    items: list[MessageRead]
    total: int
    page: int
    size: int
    summary: dict[str, int]


class TrendPoint(BaseModel):
    label: str
    value: int


class RankItem(BaseModel):
    name: str
    count: int


class SettingsRead(BaseModel):
    retention_days: int
    cleanup_time: str
    export_before_cleanup: bool
    direction_rules: list[dict[str, str]]


class SettingsUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=365)
    cleanup_time: str
    export_before_cleanup: bool
