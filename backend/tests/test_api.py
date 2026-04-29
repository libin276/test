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
    assert ' ' in payload[0]['updated_at']


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


def test_live_server_name_can_be_updated(client):
    servers_response = client.get('/api/servers')
    assert servers_response.status_code == 200
    live_server = next(item for item in servers_response.json() if item['host'] == '139.9.100.63')
    original_name = live_server['name']
    updated_name = f'{original_name}-已修改'

    update_response = client.put(
        f"/api/servers/{live_server['id']}",
        json={
            'name': updated_name,
            'host': live_server['host'],
            'port': live_server['port'],
            'username': live_server['username'],
            'password': live_server['password'],
            'tls': live_server['tls'],
            'enabled': live_server['enabled'],
            'remark': live_server['remark'],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()['name'] == updated_name

    fetch_response = client.get('/api/servers')
    assert fetch_response.status_code == 200
    refreshed = next(item for item in fetch_response.json() if item['id'] == live_server['id'])
    assert refreshed['name'] == updated_name

    restore_response = client.put(
        f"/api/servers/{live_server['id']}",
        json={
            'name': original_name,
            'host': live_server['host'],
            'port': live_server['port'],
            'username': live_server['username'],
            'password': live_server['password'],
            'tls': live_server['tls'],
            'enabled': live_server['enabled'],
            'remark': live_server['remark'],
        },
    )
    assert restore_response.status_code == 200


def test_get_topics_with_filter(client):
    response = client.get('/api/topics', params={'direction': '上行'})
    assert response.status_code == 200
    payload = response.json()
    assert all(item['direction'] == '上行' for item in payload)


def test_messages_query_and_export(client):
    with SessionLocal() as db:
        server = db.query(Server).order_by(Server.id.asc()).first()
        server_id = server.id
        message = Message(
            server_id=server_id,
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

    direction_response = client.get('/api/messages', params={'direction': '下行', 'keyword': 'reboot'})
    assert direction_response.status_code == 200
    direction_payload = direction_response.json()
    assert all(item['direction'] == '下行' for item in direction_payload['items'])

    filter_response = client.get(
        '/api/messages',
        params={
            'keyword': 'reboot',
            'start': '2026-04-28T00:00:00+08:00',
            'end': '2026-04-30T00:00:00+08:00',
        },
    )
    assert filter_response.status_code == 200
    assert any('reboot' in item['payload'] for item in filter_response.json()['items'])

    export_response = client.get('/api/messages/export', params={'keyword': 'reboot'})
    assert export_response.status_code == 200
    assert export_response.headers['content-type'].startswith('text/csv')
    assert 'reboot' in export_response.text
    assert '+' in export_response.text

    cleanup_response = client.post(
        '/api/messages/cleanup',
        json={
            'before': '2999-01-01T00:00:00+08:00',
            'server_id': server_id,
        },
    )
    assert cleanup_response.status_code == 200
    assert cleanup_response.json()['deleted'] >= 1

    verify_response = client.get('/api/messages', params={'keyword': 'reboot'})
    assert verify_response.status_code == 200
    assert all('reboot' not in item['payload'] for item in verify_response.json()['items'])


def test_stats_endpoints(client):
    trend = client.get('/api/stat/message_trend')
    day_trend = client.get('/api/stat/message_trend', params={'granularity': 'day'})
    topic_rank = client.get('/api/stat/topic_rank')
    device_rank = client.get('/api/stat/device_rank')
    runtime = client.get('/api/runtime')
    assert trend.status_code == 200
    assert day_trend.status_code == 200
    assert topic_rank.status_code == 200
    assert device_rank.status_code == 200
    assert runtime.status_code == 200
    runtime_payload = runtime.json()
    assert 'servers' in runtime_payload
    assert 'throughput_per_second' in runtime_payload
    assert 'flush_count' in runtime_payload
    if runtime_payload.get('last_flush_at'):
        assert ' ' in runtime_payload['last_flush_at']
    for server in runtime_payload.get('servers', []):
        if server.get('connected_at'):
            assert ' ' in server['connected_at']
    assert all(':' in item['label'] for item in trend.json())
    assert all('-' in item['label'] for item in day_trend.json())


def test_detect_direction_for_edge_and_cloud_topics():
    assert detect_direction('/edge/uNQToB1YXcw/251211514/rtg') == '上行'
    assert detect_direction('/cloud/uNQToB1YXcw/251211514/cmd/set') == '下行'
