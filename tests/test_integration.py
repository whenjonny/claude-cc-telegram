import asyncio
import json
import os
import tempfile
import pytest


@pytest.mark.asyncio
async def test_socket_roundtrip(tmp_path):
    """Test that socket server receives and responds to a notification payload."""
    sock_path = tempfile.mktemp(suffix=".sock", dir="/tmp")

    received = []

    async def handler(reader, writer):
        data = await reader.read(65536)
        payload = json.loads(data.decode())
        received.append(payload)
        writer.write(b'{"ok":true}')
        await writer.drain()
        writer.close()

    server = await asyncio.start_unix_server(handler, path=sock_path)

    reader, writer = await asyncio.open_unix_connection(sock_path)
    payload = {
        "action": "send_notification",
        "session_id": "test",
        "text": "hello",
        "buttons": [],
    }
    writer.write(json.dumps(payload).encode())
    await writer.drain()
    response = await reader.read(4096)
    writer.close()

    assert json.loads(response) == {"ok": True}
    assert len(received) == 1
    assert received[0]["session_id"] == "test"

    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_socket_ping(tmp_path):
    """Test ping action on socket."""
    sock_path = tempfile.mktemp(suffix=".sock", dir="/tmp")

    async def handler(reader, writer):
        data = await reader.read(65536)
        payload = json.loads(data.decode())
        if payload.get("action") == "ping":
            writer.write(b'{"ok":true}')
        await writer.drain()
        writer.close()

    server = await asyncio.start_unix_server(handler, path=sock_path)

    reader, writer = await asyncio.open_unix_connection(sock_path)
    writer.write(json.dumps({"action": "ping"}).encode())
    await writer.drain()
    response = await reader.read(4096)
    writer.close()

    assert json.loads(response) == {"ok": True}

    server.close()
    await server.wait_closed()
