
# server.py
import asyncio
import json
import time
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame
from ultralytics import YOLO

yolo_model = YOLO(r"C:/Users/bugzx/OneDrive/Desktop/v0dev_codes/YOLOv10n_gestures.pt")

PCS = set()

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp

async def consume_and_detect(track, send_label):
    """Read frames from incoming WebRTC video track, run YOLO, send best label."""
    last_sent = 0.0
    try:
        while True:
            frame: VideoFrame = await track.recv()
            img = frame.to_ndarray(format="bgr24")

            results = yolo_model(img, verbose=False)

            best_label = None
            best_conf = 0.0
            for r in results:
                if getattr(r, "boxes", None) is None:
                    continue
                names = r.names 
                for b in r.boxes:
                    conf = float(b.conf[0]) if b.conf is not None else 0.0
                    cls_id = int(b.cls[0]) if b.cls is not None else -1
                    if cls_id >= 0 and conf > best_conf:
                        best_conf = conf
                        best_label = names.get(cls_id, f"class_{cls_id}")

            now = time.time()
            if best_label is not None and (now - last_sent) > 0.1:
                payload = json.dumps({"label": best_label, "confidence": best_conf})
                await send_label(payload)
                last_sent = now
    except asyncio.CancelledError:
        pass

async def offer(request: web.Request):
    """
    POST /offer
    Body: { "sdp": "<offer sdp>", "type": "offer" }
    Returns: { "sdp": "<answer sdp>", "type": "answer" }
    """
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    PCS.add(pc)

    label_channel = {"send": None}

    @pc.on("connectionstatechange")
    async def on_state():
        print("PC state:", pc.connectionState)
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            PCS.discard(pc)

    blackhole = MediaBlackhole()

    @pc.on("datachannel")
    def on_datachannel(channel):
        print("DataChannel created by client:", channel.label)
        if channel.label == "gestures":
            async def send_label_async(text):

                channel.send(text)
            label_channel["send"] = send_label_async

    @pc.on("track")
    def on_track(track):
        print("Incoming track:", track.kind)
        if track.kind == "video":

            async def send_label(payload):
                if label_channel["send"] is not None:
                    await label_channel["send"](payload)

            task = asyncio.create_task(consume_and_detect(track, send_label))

            @track.on("ended")
            async def on_ended():
                task.cancel()
        else:
    
            blackhole.addTrack(track)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


def make_app():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_route("OPTIONS", "/offer", lambda _: web.Response(status=204))
    app.router.add_post("/offer", offer)

    async def on_shutdown(app):
        coros = [pc.close() for pc in list(PCS)]
        await asyncio.gather(*coros)

    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), port=8080)
