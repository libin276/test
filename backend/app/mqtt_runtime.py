import json
import logging
import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from paho.mqtt import client as mqtt_client
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import SessionLocal
from .models import Message, Server
from .seed import detect_direction, ensure_live_test_config

LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeMessage:
    server_id: int
    topic: str
    payload: str
    qos: int
    device_id: str | None
    direction: str
    raw: str
    timestamp: datetime


class BatchMessageWriter:
    def __init__(self, queue_size: int = 20000, batch_size: int = 200, flush_interval: float = 1.0):
        self.queue: queue.Queue[RuntimeMessage] = queue.Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.dropped_count = 0
        self.total_written = 0
        self.flush_count = 0
        self.last_flush_size = 0
        self.last_flush_at: datetime | None = None
        self.recent_flushes: deque[tuple[float, int]] = deque(maxlen=120)

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name='mqtt-batch-writer', daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def enqueue(self, message: RuntimeMessage) -> None:
        try:
            self.queue.put(message, timeout=0.2)
        except queue.Full:
            self.dropped_count += 1
            LOGGER.warning('MQTT 消息缓冲队列已满，丢弃消息。topic=%s dropped=%s', message.topic, self.dropped_count)

    def stats(self) -> dict[str, int]:
        now = time.monotonic()
        recent_window = [item for item in self.recent_flushes if now - item[0] <= 60]
        throughput = round(sum(size for _, size in recent_window) / 60, 2) if recent_window else 0
        return {
            'queue_size': self.queue.qsize(),
            'dropped_count': self.dropped_count,
            'batch_size': self.batch_size,
            'flush_interval_ms': int(self.flush_interval * 1000),
            'flush_count': self.flush_count,
            'last_flush_size': self.last_flush_size,
            'total_written': self.total_written,
            'throughput_per_second': throughput,
            'last_flush_at': self.last_flush_at.isoformat() if self.last_flush_at else None,
        }

    def _flush(self, messages: list[RuntimeMessage]) -> None:
        if not messages:
            return
        with SessionLocal() as db:
            db.add_all(
                [
                    Message(
                        server_id=item.server_id,
                        topic=item.topic,
                        payload=item.payload,
                        qos=item.qos,
                        device_id=item.device_id,
                        direction=item.direction,
                        raw=item.raw,
                        timestamp=item.timestamp,
                    )
                    for item in messages
                ]
            )
            db.commit()
            size = len(messages)
            self.total_written += size
            self.flush_count += 1
            self.last_flush_size = size
            self.last_flush_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.recent_flushes.append((time.monotonic(), size))

    def _run(self) -> None:
        batch: list[RuntimeMessage] = []
        last_flush = time.monotonic()
        while not self.stop_event.is_set() or not self.queue.empty():
            timeout = max(0.1, self.flush_interval - (time.monotonic() - last_flush))
            try:
                item = self.queue.get(timeout=timeout)
                batch.append(item)
                if len(batch) >= self.batch_size:
                    self._flush(batch)
                    batch.clear()
                    last_flush = time.monotonic()
            except queue.Empty:
                if batch and (time.monotonic() - last_flush >= self.flush_interval):
                    self._flush(batch)
                    batch.clear()
                    last_flush = time.monotonic()
        if batch:
            self._flush(batch)


class MQTTServerWorker:
    def __init__(
        self,
        server: Server,
        topics: list[tuple[str, int, str | None]],
        writer: BatchMessageWriter,
        status_callback: Callable[[int, str], None],
    ) -> None:
        self.server_id = server.id
        self.server_name = server.name
        self.host = server.host
        self.port = server.port
        self.username = server.username
        self.password = server.password
        self.tls = server.tls
        self.topics = topics
        self.writer = writer
        self.status_callback = status_callback
        self.client: mqtt_client.Client | None = None
        self.client_id = f'mqtt-manager-{server.id}-{uuid.uuid4().hex[:8]}'
        self.keepalive = 60
        self.status = '初始化中'
        self.reconnect_count = 0
        self.connected_at: datetime | None = None
        self.last_message_at: datetime | None = None
        self._topic_direction = {topic: direction for topic, _, direction in topics}

    @property
    def signature(self) -> tuple:
        return (
            self.host,
            self.port,
            self.username,
            self.password,
            self.tls,
            tuple(sorted(self.topics)),
        )

    def start(self) -> None:
        client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            clean_session=False,
        )
        if self.username:
            client.username_pw_set(self.username, self.password)
        if self.tls:
            client.tls_set()
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.enable_logger(LOGGER)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.connect_async(self.host, self.port, keepalive=self.keepalive)
        client.loop_start()
        self.client = client
        self._set_status('连接中')

    @staticmethod
    def _is_success_reason_code(reason_code) -> bool:
        if reason_code is None:
            return True
        try:
            return int(reason_code) == 0
        except (TypeError, ValueError):
            if hasattr(reason_code, 'is_failure'):
                return not bool(reason_code.is_failure)
            normalized = str(reason_code).lower()
            return 'success' in normalized or 'normal' in normalized

    def stop(self) -> None:
        if not self.client:
            return
        try:
            self.client.loop_stop()
            self.client.disconnect()
        finally:
            self.client = None
            self._set_status('未启用')

    def _set_status(self, status: str) -> None:
        self.status = status
        self.status_callback(self.server_id, status)

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties=None):
        if not self._is_success_reason_code(reason_code):
            LOGGER.warning('MQTT 连接失败 server=%s code=%s', self.server_name, reason_code)
            self.reconnect_count += 1
            self._set_status('重连中')
            return

        for topic, qos, _direction in self.topics:
            client.subscribe(topic, qos=qos)
        LOGGER.info('MQTT 已连接并完成订阅 server=%s topics=%s', self.server_name, [item[0] for item in self.topics])
        self.connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self._set_status('已连接')

    def _on_disconnect(self, _client, _userdata, *args):
        if len(args) >= 2:
            reason_code = args[1]
        elif len(args) == 1:
            reason_code = args[0]
        else:
            reason_code = 0

        if self._is_success_reason_code(reason_code):
            self._set_status('未启用')
            return
        self.reconnect_count += 1
        LOGGER.warning('MQTT 连接断开 server=%s code=%s，等待自动重连', self.server_name, reason_code)
        self._set_status('重连中')

    def _on_message(self, _client, _userdata, message):
        payload = message.payload.decode('utf-8', errors='replace')
        direction = self._resolve_direction(message.topic)
        device_id = self._extract_device_id(message.topic)
        runtime_message = RuntimeMessage(
            server_id=self.server_id,
            topic=message.topic,
            payload=payload,
            qos=message.qos,
            device_id=device_id,
            direction=direction,
            raw=payload,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.last_message_at = runtime_message.timestamp
        self.writer.enqueue(runtime_message)

    def snapshot(self) -> dict[str, object]:
        return {
            'server_id': self.server_id,
            'server_name': self.server_name,
            'host': self.host,
            'port': self.port,
            'status': self.status,
            'reconnect_count': self.reconnect_count,
            'topic_count': len(self.topics),
            'keepalive': self.keepalive,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
        }

    def _resolve_direction(self, topic: str) -> str:
        for pattern, direction in self._topic_direction.items():
            prefix = pattern.rstrip('#')
            if prefix and topic.startswith(prefix):
                return detect_direction(topic, direction)
        return detect_direction(topic)

    @staticmethod
    def _extract_device_id(topic: str) -> str | None:
        parts = [item for item in topic.split('/') if item]
        if len(parts) >= 3:
            return parts[2]
        return None


class MQTTRuntimeManager:
    def __init__(self) -> None:
        self.writer = BatchMessageWriter()
        self.lock = threading.Lock()
        self.workers: dict[int, MQTTServerWorker] = {}
        self.status_map: dict[int, str] = {}

    def start(self) -> None:
        self.writer.start()
        self.sync()

    def stop(self) -> None:
        with self.lock:
            for worker in self.workers.values():
                worker.stop()
            self.workers.clear()
        self.writer.stop()

    def sync(self) -> None:
        with SessionLocal() as db:
            ensure_live_test_config(db)
            servers = db.scalars(select(Server).options(selectinload(Server.topics))).unique().all()

        desired: dict[int, tuple[Server, list[tuple[str, int, str | None]]]] = {}
        for server in servers:
            enabled_topics = [(topic.topic, topic.qos, topic.direction) for topic in server.topics if topic.enabled]
            if not server.enabled:
                self.status_map[server.id] = '未启用'
                continue
            if not enabled_topics:
                self.status_map[server.id] = '未配置Topic'
                continue
            desired[server.id] = (server, enabled_topics)

        with self.lock:
            current_ids = set(self.workers.keys())
            desired_ids = set(desired.keys())

            for server_id in current_ids - desired_ids:
                self.workers[server_id].stop()
                del self.workers[server_id]

            for server_id, (server, topics) in desired.items():
                existing = self.workers.get(server_id)
                candidate = MQTTServerWorker(server, topics, self.writer, self._update_status)
                if existing and existing.signature == candidate.signature:
                    continue
                if existing:
                    existing.stop()
                candidate.start()
                self.workers[server_id] = candidate

    def get_status(self, server: Server) -> str:
        if not server.enabled:
            return '未启用'
        return self.status_map.get(server.id, '连接中')

    def runtime_stats(self) -> dict[str, object]:
        with SessionLocal() as db:
            servers = db.scalars(select(Server).options(selectinload(Server.topics))).unique().all()

        with self.lock:
            worker_snapshots = {server_id: worker.snapshot() for server_id, worker in self.workers.items()}

        server_status = []
        for server in servers:
            enabled_topic_count = sum(1 for topic in server.topics if topic.enabled)
            if server.id in worker_snapshots:
                item = worker_snapshots[server.id]
            else:
                item = {
                    'server_id': server.id,
                    'server_name': server.name,
                    'host': server.host,
                    'port': server.port,
                    'status': self.get_status(server),
                    'reconnect_count': 0,
                    'topic_count': enabled_topic_count,
                    'keepalive': 0,
                    'connected_at': None,
                    'last_message_at': None,
                }
            item['enabled'] = server.enabled
            item['configured_topic_count'] = len(server.topics)
            item['enabled_topic_count'] = enabled_topic_count
            server_status.append(item)

        return self.writer.stats() | {
            'worker_count': len(self.workers),
            'servers': server_status,
        }

    def _update_status(self, server_id: int, status: str) -> None:
        self.status_map[server_id] = status
