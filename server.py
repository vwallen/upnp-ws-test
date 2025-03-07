#!/usr/bin/env python

import logging
import miniupnpc
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

connections = {}

async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    for connection in connections.values():
        await ws.send_text(f"{connection.client.host}:{connection.client.port} connected")

    connections[ws.client.port] = ws
    for connection in connections.values():
        await connection.send_text(f"{ws.client.host}:{ws.client.port} connected")

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        del connections[ws.client.port]
        for connection in connections.values():
            await connection.send_text(f"{ws.client.host}:{ws.client.port} disconnected")

routes=[
    WebSocketRoute('/ws', websocket_endpoint),
    Mount('/', app=StaticFiles(directory='static', html=True), name="static"),
]

app = Starlette(routes=routes)

if __name__ == '__main__':

    port_local = 9000
    port_external = port_local

    u = miniupnpc.UPnP(discoverdelay=200)
    u.discover()
    u.selectigd()

    port_available = u.getspecificportmapping(port_external, 'TCP') is None
    while not port_available and port_external < 65536:
        port_external += 1
        port_available = u.getspecificportmapping(port_external, 'TCP') is None

    mapped = u.addportmapping(port_external, 'TCP', u.lanaddr, port_local, f'UPnP test mapping: {u.externalipaddress()}:{port_external}', '')
    logger.info(f"Added port mapping {u.getspecificportmapping(port_external, 'TCP')}")

    try:
        config = uvicorn.Config(app, host='0.0.0.0', port=port_local)
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt as err:
        pass
    finally:
        logger.info(f"Deleting port mapping {u.getspecificportmapping(port_external, 'TCP')}")
        u.deleteportmapping(port_external, 'TCP')
