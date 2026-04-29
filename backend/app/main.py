import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Message, Server, Topic
from .mqtt_runtime import MQTTRuntimeManager
from .schemas import (
    MessageCleanupRequest,
    MessageCleanupResponse,
    MessageListResponse,
    MessageRead,
    RankItem,
    ServerCreate,
    ServerRead,
    ServerToggle,
    ServerUpdate,
    SettingsRead,
    SettingsUpdate,
    TopicCreate,
    TopicRead,
    TopicToggle,
    TopicUpdate,
    TrendPoint,
)
from .seed import detect_direction, ensure_live_test_config, seed_data

settings_state = {
    'retention_days': 30,
    'cleanup_time': '03:00:00',
    'export_before_cleanup': True,
}

CHINA_TZ = timezone(timedelta(hours=8))

mqtt_runtime = MQTTRuntimeManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_data(db)
        ensure_live_test_config(db)
    mqtt_runtime.start()
    yield
    mqtt_runtime.stop()


app = FastAPI(title='MQTT订阅管理器 API', version='0.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def format_server_status(server: Server) -> str:
    return mqtt_runtime.get_status(server)


def server_to_read(server: Server) -> ServerRead:
    return ServerRead(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        username=server.username,
        password=server.password,
        tls=server.tls,
        enabled=server.enabled,
        remark=server.remark,
        status=format_server_status(server),
        topic_count=len(server.topics),
        updated_at=to_china_time_string(server.updated_at),
    )


def topic_to_read(topic: Topic) -> TopicRead:
    return TopicRead(
        id=topic.id,
        server_id=topic.server_id,
        server_name=topic.server.name,
        topic=topic.topic,
        qos=topic.qos,
        direction=topic.direction,
        enabled=topic.enabled,
        remark=topic.remark,
        updated_at=to_china_time_string(topic.updated_at),
    )


def message_to_read(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        server_id=message.server_id,
        server_name=message.server.name,
        topic=message.topic,
        payload=message.payload,
        qos=message.qos,
        device_id=message.device_id,
        direction=message.direction,
        raw=message.raw,
        timestamp=to_china_time_string(message.timestamp),
    )


def normalize_client_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def to_china_time(value: datetime | str) -> datetime:
    if isinstance(value, str):
        normalized = value.replace('Z', '+00:00')
        value = datetime.fromisoformat(normalized)
    if value.tzinfo is not None:
        return value.astimezone(CHINA_TZ)
    return value.replace(tzinfo=timezone.utc).astimezone(CHINA_TZ)


def to_china_time_string(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    return to_china_time(value).strftime('%Y-%m-%d %H:%M:%S')


def get_server_or_404(db: Session, server_id: int) -> Server:
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail='服务器不存在')
    return server


def get_topic_or_404(db: Session, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail='Topic 不存在')
    return topic


@app.get('/api/health')
def health_check():
    return {'status': 'ok'}


@app.get('/api/runtime')
def runtime_overview():
    runtime = mqtt_runtime.runtime_stats()
    runtime['last_flush_at'] = to_china_time_string(runtime.get('last_flush_at'))

    for server in runtime.get('servers', []):
        server['connected_at'] = to_china_time_string(server.get('connected_at'))
        server['last_message_at'] = to_china_time_string(server.get('last_message_at'))

    return runtime


@app.get('/api/servers', response_model=list[ServerRead])
def list_servers(
    keyword: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Server).order_by(Server.id.asc())
    if keyword:
        stmt = stmt.where(or_(Server.name.contains(keyword), Server.host.contains(keyword)))
    servers = db.scalars(stmt).unique().all()
    if status:
        servers = [item for item in servers if format_server_status(item) == status]
    return [server_to_read(server) for server in servers]


@app.post('/api/servers', response_model=ServerRead, status_code=201)
def create_server(payload: ServerCreate, db: Session = Depends(get_db)):
    server = Server(**payload.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    mqtt_runtime.sync()
    return server_to_read(server)


@app.put('/api/servers/{server_id}', response_model=ServerRead)
def update_server(server_id: int, payload: ServerUpdate, db: Session = Depends(get_db)):
    server = get_server_or_404(db, server_id)
    for field, value in payload.model_dump().items():
        setattr(server, field, value)
    db.commit()
    db.refresh(server)
    mqtt_runtime.sync()
    return server_to_read(server)


@app.patch('/api/servers/{server_id}/enable', response_model=ServerRead)
def toggle_server(server_id: int, payload: ServerToggle, db: Session = Depends(get_db)):
    server = get_server_or_404(db, server_id)
    server.enabled = payload.enabled
    db.commit()
    db.refresh(server)
    mqtt_runtime.sync()
    return server_to_read(server)


@app.delete('/api/servers/{server_id}', status_code=204)
def delete_server(server_id: int, db: Session = Depends(get_db)):
    server = get_server_or_404(db, server_id)
    db.delete(server)
    db.commit()
    mqtt_runtime.sync()
    return Response(status_code=204)


@app.get('/api/topics', response_model=list[TopicRead])
def list_topics(
    server_id: int | None = None,
    keyword: str | None = None,
    direction: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Topic).order_by(Topic.id.asc())
    if server_id is not None:
        stmt = stmt.where(Topic.server_id == server_id)
    if keyword:
        stmt = stmt.where(Topic.topic.contains(keyword))
    if direction:
        stmt = stmt.where(Topic.direction == direction)
    if enabled is not None:
        stmt = stmt.where(Topic.enabled == enabled)
    topics = db.scalars(stmt).unique().all()
    return [topic_to_read(topic) for topic in topics]


@app.post('/api/topics', response_model=TopicRead, status_code=201)
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)):
    get_server_or_404(db, payload.server_id)
    direction = payload.direction or detect_direction(payload.topic)
    topic = Topic(**payload.model_dump(exclude={'direction'}), direction=direction)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    mqtt_runtime.sync()
    return topic_to_read(topic)


@app.put('/api/topics/{topic_id}', response_model=TopicRead)
def update_topic(topic_id: int, payload: TopicUpdate, db: Session = Depends(get_db)):
    get_server_or_404(db, payload.server_id)
    topic = get_topic_or_404(db, topic_id)
    data = payload.model_dump()
    data['direction'] = data['direction'] or detect_direction(data['topic'])
    for field, value in data.items():
        setattr(topic, field, value)
    db.commit()
    db.refresh(topic)
    mqtt_runtime.sync()
    return topic_to_read(topic)


@app.patch('/api/topics/{topic_id}/enable', response_model=TopicRead)
def toggle_topic(topic_id: int, payload: TopicToggle, db: Session = Depends(get_db)):
    topic = get_topic_or_404(db, topic_id)
    topic.enabled = payload.enabled
    db.commit()
    db.refresh(topic)
    mqtt_runtime.sync()
    return topic_to_read(topic)


@app.delete('/api/topics/{topic_id}', status_code=204)
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = get_topic_or_404(db, topic_id)
    db.delete(topic)
    db.commit()
    mqtt_runtime.sync()
    return Response(status_code=204)


def build_message_stmt(
    server_id: int | None,
    topics: list[str] | None,
    keyword: str | None,
    direction: str | None,
    start: datetime | None,
    end: datetime | None,
):
    stmt = select(Message).order_by(Message.timestamp.desc())
    if server_id is not None:
        stmt = stmt.where(Message.server_id == server_id)
    if topics:
        stmt = stmt.where(Message.topic.in_(topics))
    if keyword:
        stmt = stmt.where(or_(Message.topic.contains(keyword), Message.payload.contains(keyword), Message.device_id.contains(keyword)))
    if direction:
        stmt = stmt.where(Message.direction == direction)
    if start is not None:
        stmt = stmt.where(Message.timestamp >= normalize_client_datetime(start))
    if end is not None:
        stmt = stmt.where(Message.timestamp <= normalize_client_datetime(end))
    return stmt


@app.get('/api/messages', response_model=MessageListResponse)
def list_messages(
    server_id: int | None = None,
    topics: list[str] = Query(default=[]),
    keyword: str | None = None,
    direction: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = build_message_stmt(server_id, topics or None, keyword, direction, start, end)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * size).limit(size)).unique().all()

    summary_stmt = build_message_stmt(server_id, topics or None, keyword, direction, start, end)
    summary_items = db.scalars(summary_stmt).unique().all()
    summary = {
        'total': len(summary_items),
        'uplink': sum(1 for item in summary_items if item.direction == '上行'),
        'downlink': sum(1 for item in summary_items if item.direction == '下行'),
    }
    return MessageListResponse(
        items=[message_to_read(item) for item in items],
        total=total,
        page=page,
        size=size,
        summary=summary,
    )


@app.get('/api/messages/export')
def export_messages(
    server_id: int | None = None,
    topics: list[str] = Query(default=[]),
    keyword: str | None = None,
    direction: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    stmt = build_message_stmt(server_id, topics or None, keyword, direction, start, end)
    items = db.scalars(stmt).unique().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['时间戳', '服务器', 'Topic', '方向', 'QoS', '设备ID', '消息内容'])
    for item in items:
        writer.writerow([
            to_china_time(item.timestamp).isoformat(sep=' ', timespec='seconds'),
            item.server.name,
            item.topic,
            item.direction,
            item.qos,
            item.device_id or '',
            item.payload,
        ])
    content = buffer.getvalue()
    filename = f"mqtt_logs_{datetime.now(CHINA_TZ).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@app.post('/api/messages/cleanup', response_model=MessageCleanupResponse)
def cleanup_messages(payload: MessageCleanupRequest, db: Session = Depends(get_db)):
    before = normalize_client_datetime(payload.before)
    stmt = select(Message).where(Message.timestamp < before)
    if payload.server_id is not None:
        stmt = stmt.where(Message.server_id == payload.server_id)

    items = db.scalars(stmt).all()
    deleted = len(items)
    for item in items:
        db.delete(item)
    db.commit()
    return MessageCleanupResponse(deleted=deleted)


@app.get('/api/stat/message_trend', response_model=list[TrendPoint])
def message_trend(granularity: str = Query(default='hour', pattern='^(hour|day)$'), db: Session = Depends(get_db)):
    items = db.scalars(select(Message.timestamp).order_by(Message.timestamp.asc())).all()
    bucket_map: dict[str, int] = {}
    for item in items:
        china_time = to_china_time(item)
        label = china_time.strftime('%H:00') if granularity == 'hour' else china_time.strftime('%Y-%m-%d')
        bucket_map[label] = bucket_map.get(label, 0) + 1
    return [TrendPoint(label=label, value=value) for label, value in sorted(bucket_map.items())]


@app.get('/api/stat/topic_rank', response_model=list[RankItem])
def topic_rank(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Message.topic, func.count(Message.id))
        .group_by(Message.topic)
        .order_by(func.count(Message.id).desc())
        .limit(10)
    ).all()
    return [RankItem(name=row[0], count=row[1]) for row in rows]


@app.get('/api/stat/device_rank', response_model=list[RankItem])
def device_rank(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Message.device_id, func.count(Message.id))
        .where(Message.device_id.is_not(None))
        .group_by(Message.device_id)
        .order_by(func.count(Message.id).desc())
        .limit(10)
    ).all()
    return [RankItem(name=row[0], count=row[1]) for row in rows]


@app.get('/api/settings', response_model=SettingsRead)
def get_settings():
    return SettingsRead(
        retention_days=settings_state['retention_days'],
        cleanup_time=settings_state['cleanup_time'],
        export_before_cleanup=settings_state['export_before_cleanup'],
        direction_rules=[
            {'key': '/up, /data, /report', 'type': '上行', 'desc': '设备或网关主动上报'},
            {'key': '/down, /cmd, /set', 'type': '下行', 'desc': '云平台下发控制和配置'},
        ],
    )


@app.put('/api/settings', response_model=SettingsRead)
def update_settings(payload: SettingsUpdate):
    settings_state.update(payload.model_dump())
    return get_settings()
