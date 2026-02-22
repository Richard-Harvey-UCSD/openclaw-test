"""OBS WebSocket integration via obs-websocket-plugin v5."""

import asyncio
import json
import hashlib
import base64
import uuid
from typing import Optional
import websockets


class OBSController:
    def __init__(self, url: str = "ws://localhost:4455", password: str = ""):
        self.url = url
        self.password = password
        self._ws = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self._ws is not None

    async def connect(self):
        try:
            self._ws = await websockets.connect(self.url)
            hello = json.loads(await self._ws.recv())
            if hello.get("op") != 0:
                raise ConnectionError("Unexpected OBS hello")

            auth = hello["d"].get("authentication")
            if auth and self.password:
                secret = base64.b64encode(
                    hashlib.sha256(
                        (self.password + auth["salt"]).encode()
                    ).digest()
                ).decode()
                auth_string = base64.b64encode(
                    hashlib.sha256(
                        (secret + auth["challenge"]).encode()
                    ).digest()
                ).decode()
                await self._send(1, {"rpcVersion": 1, "authentication": auth_string})
            else:
                await self._send(1, {"rpcVersion": 1})

            resp = json.loads(await self._ws.recv())
            if resp.get("op") == 2:
                self._connected = True
            else:
                raise ConnectionError("OBS auth failed")
        except Exception as e:
            self._connected = False
            self._ws = None
            raise

    async def disconnect(self):
        if self._ws:
            await self._ws.close()
        self._ws = None
        self._connected = False

    async def _send(self, op: int, data: dict):
        if self._ws:
            await self._ws.send(json.dumps({"op": op, "d": data}))

    async def _request(self, request_type: str, data: Optional[dict] = None) -> dict:
        if not self.connected:
            raise ConnectionError("Not connected to OBS")
        req_id = str(uuid.uuid4())
        payload = {"requestType": request_type, "requestId": req_id}
        if data:
            payload["requestData"] = data
        await self._send(6, payload)
        while True:
            raw = await self._ws.recv()
            msg = json.loads(raw)
            if msg.get("op") == 7 and msg["d"].get("requestId") == req_id:
                return msg["d"].get("responseData", {})

    async def switch_scene(self, scene_name: str):
        await self._request("SetCurrentProgramScene", {"sceneName": scene_name})

    async def get_scenes(self) -> list[str]:
        resp = await self._request("GetSceneList")
        return [s["sceneName"] for s in resp.get("scenes", [])]

    async def toggle_source(self, scene: str, source: str, visible: Optional[bool] = None):
        items = await self._request("GetSceneItemList", {"sceneName": scene})
        for item in items.get("sceneItems", []):
            if item["sourceName"] == source:
                item_id = item["sceneItemId"]
                if visible is None:
                    current = item.get("sceneItemEnabled", True)
                    visible = not current
                await self._request("SetSceneItemEnabled", {
                    "sceneName": scene,
                    "sceneItemId": item_id,
                    "sceneItemEnabled": visible,
                })
                return

    async def set_source_filter_visibility(self, source: str, filter_name: str, enabled: bool):
        await self._request("SetSourceFilterEnabled", {
            "sourceName": source,
            "filterName": filter_name,
            "filterEnabled": enabled,
        })
