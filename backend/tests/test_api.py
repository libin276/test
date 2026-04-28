from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Message, Server
from app.seed import detect_direction


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_servers(client):
    response = client.get('/api/servers')
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert 'topic_count' in payload[0]


def test_create_and_toggle_server(client):
    create_response = client.post(
        '/api/servers',
        json={
            'name': '测试服务器',
            'host': '127.0.0.1',
            'port': 1883,
            'username': 'tester',
            'password': 'secret',
            'tls': False,
            'enabled': True,
            'remark': 'pytest',
        },
    )
    assert create_response.status_code == 201
    server_id = create_response.json()['id']

    toggle_response = client.patch(f'/api/servers/{server_id}/enable', json={'enabled': False})
    assert toggle_response.status_code == 200
    assert toggle_response.json()['enabled'] is False

    delete_response = client.delete(f'/api/servers/{server_id}')
    assert delete_response.status_code == 204


def test_get_topics_with_filter(client):
    response = client.get('/api/topics', params={'direction': '上行'})
    assert response.status_code == 200
    payload = response.json()
    assert all(item['direction'] == '上行' for item in payload)


def test_messages_query_and_export(client):
    with SessionLocal() as db:
        server = db.query(Server).order_by(Server.id.asc()).first()
        message = Message(
            server_id=server.id,
            topic='/pytest/runtime/reboot',
            payload='{"cmd":"reboot","source":"pytest"}',
            qos=1,
            device_id='pytest-device',
            direction='下行',
            raw='{"cmd":"reboot","source":"pytest"}',
            timestamp=datetime.utcnow(),
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        message_id = message.id

    response = client.get('/api/messages', params={'keyword': 'reboot', 'page': 1, 'size': 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] >= 1
    assert any('reboot' in item['payload'] for item in payload['items'])

    export_response = client.get('/api/messages/export', params={'keyword': 'reboot'})
    assert export_response.status_code == 200
    assert export_response.headers['content-type'].startswith('text/csv')
    assert 'reboot' in export_response.text

    with SessionLocal() as db:
        message = db.get(Message, message_id)
        if message is not None:
            db.delete(message)
            db.commit()


def test_stats_endpoints(client):
    trend = client.get('/api/stat/message_trend')
    topic_rank = client.get('/api/stat/topic_rank')
    device_rank = client.get('/api/stat/device_rank')
    runtime = client.get('/api/runtime')
    assert trend.status_code == 200
    assert topic_rank.status_code == 200
    assert device_rank.status_code == 200
    assert runtime.status_code == 200
    runtime_payload = runtime.json()
    assert 'servers' in runtime_payload
    assert 'throughput_per_second' in runtime_payload
    assert 'flush_count' in runtime_payload


def test_detect_direction_for_edge_and_cloud_topics():
    assert detect_direction('/edge/uNQToB1YXcw/251211514/rtg') == '上行'
    assert detect_direction('/cloud/uNQToB1YXcw/251211514/cmd/set') == '下行'
