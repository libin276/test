from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Message, Server, Topic


LIVE_TEST_SERVER = {
    'name': '华为云MQTT测试服务器',
    'host': '139.9.100.63',
    'port': 30883,
    'username': 's_bacnetchina',
    'password': 'X4eNgIXWoH633Lr6QBFi',
    'tls': False,
    'enabled': True,
    'remark': '自动注入的真实 MQTT 联调服务器',
}

LIVE_TEST_TOPICS = [
    {
        'topic': '/edge/uNQToB1YXcw/251211514/#',
        'qos': 1,
        'direction': '上行',
        'enabled': True,
        'remark': '真实 broker 上行订阅',
    },
    {
        'topic': '/cloud/uNQToB1YXcw/251211514/#',
        'qos': 1,
        'direction': '下行',
        'enabled': True,
        'remark': '真实 broker 下行订阅',
    },
]


def detect_direction(topic: str, manual_direction: str | None = None) -> str:
    if manual_direction in {'上行', '下行'}:
        return manual_direction

    normalized = topic.lower()
    uplink_keywords = ('/up', '/data', '/report', '/edge/')
    downlink_keywords = ('/down', '/cmd', '/set', '/cloud/')

    if any(keyword in normalized for keyword in uplink_keywords):
        return '上行'
    if any(keyword in normalized for keyword in downlink_keywords):
        return '下行'
    return '上行'


def ensure_live_test_config(db: Session) -> None:
    server = db.scalar(
        select(Server).where(
            Server.host == LIVE_TEST_SERVER['host'],
            Server.port == LIVE_TEST_SERVER['port'],
            Server.username == LIVE_TEST_SERVER['username'],
        )
    )

    if server is None:
        server = Server(**LIVE_TEST_SERVER)
        db.add(server)
        db.flush()
    else:
        for field, value in LIVE_TEST_SERVER.items():
            setattr(server, field, value)
        db.flush()

    existing_topics = {item.topic: item for item in server.topics}
    for topic_data in LIVE_TEST_TOPICS:
        existing = existing_topics.get(topic_data['topic'])
        if existing is None:
            db.add(Topic(server_id=server.id, **topic_data))
            continue
        for field, value in topic_data.items():
            setattr(existing, field, value)

    db.commit()


def seed_data(db: Session) -> None:
    existing = db.scalar(select(Server.id).limit(1))
    if existing is not None:
        return

    servers = [
        Server(name='深圳智云中心', host='mqtt.cloud.example.com', port=8883, username='ops_admin', password='******', tls=True, enabled=True, remark='生产环境云端集群'),
        Server(name='园区边缘网关', host='192.168.10.50', port=1883, username='gateway', password='******', tls=False, enabled=True, remark='现场排障临时接入'),
        Server(name='历史回放服务器', host='10.10.12.8', port=1883, username='replay_user', password='******', tls=False, enabled=False, remark='用于历史问题复盘'),
    ]
    db.add_all(servers)
    db.flush()

    topics = [
        Topic(server_id=servers[0].id, topic='/gateway/+/up/report', qos=1, direction='上行', enabled=True, remark='网关运行状态上报'),
        Topic(server_id=servers[0].id, topic='/gateway/+/down/cmd', qos=1, direction='下行', enabled=True, remark='云端控制指令'),
        Topic(server_id=servers[1].id, topic='/site/a/building/1/data', qos=0, direction='上行', enabled=True, remark='环境数据同步'),
        Topic(server_id=servers[1].id, topic='/site/a/building/1/set', qos=0, direction='下行', enabled=False, remark='远程参数设置'),
    ]
    db.add_all(topics)
    db.flush()

    base_time = datetime(2026, 4, 28, 9, 31, 0)
    messages = [
        Message(server_id=servers[0].id, topic='/gateway/gw-001/up/report', payload='{"temp":26.3,"humidity":61,"status":"online"}', qos=1, device_id='gw-001', direction=detect_direction('/gateway/gw-001/up/report'), raw='{"temp":26.3,"humidity":61,"status":"online"}', timestamp=base_time + timedelta(seconds=22)),
        Message(server_id=servers[0].id, topic='/gateway/gw-001/down/cmd', payload='{"cmd":"reboot","operator":"ops"}', qos=1, device_id='gw-001', direction=detect_direction('/gateway/gw-001/down/cmd'), raw='{"cmd":"reboot","operator":"ops"}', timestamp=base_time + timedelta(seconds=45)),
        Message(server_id=servers[1].id, topic='/site/a/building/1/data', payload='{"power":13.22,"voltage":221.5}', qos=0, device_id='meter-13', direction=detect_direction('/site/a/building/1/data'), raw='{"power":13.22,"voltage":221.5}', timestamp=base_time + timedelta(minutes=1, seconds=2)),
        Message(server_id=servers[1].id, topic='/site/a/building/1/set', payload='{"setpoint":24,"mode":"cooling"}', qos=0, device_id='ahu-02', direction=detect_direction('/site/a/building/1/set'), raw='{"setpoint":24,"mode":"cooling"}', timestamp=base_time + timedelta(minutes=1, seconds=30)),
    ]
    db.add_all(messages)
    db.commit()
