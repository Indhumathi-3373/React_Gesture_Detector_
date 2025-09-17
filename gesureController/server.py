# server.py
import asyncio
import json
import time
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame
from ultralytics import YOLO
# Load YOLOv10n model (Make sure path is correct!)
yolo_model = YOLO("C:/Users/INDHUMATHI C/Documents/GitHub/transign/React_Gesture_Detector_/gesureController/YOLOv10n_gestures.pt")
PCS = set()
# ------------------ CORS Middleware ------------------
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(status=204)
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response
# ------------------ Frame Processing ------------------
async def consume_and_detect(track, send_label):
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
            if best_label and (now - last_sent) > 0.1:
                payload = json.dumps({"label": best_label, "confidence": best_conf})
                print("Sending to frontend:", payload)
                await send_label(payload)
                last_sent = now
    except asyncio.CancelledError:
        print("Detection task cancelled")
        pass
# ------------------ WebRTC Offer Handler ------------------
async def offer(request: web.Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    PCS.add(pc)
    print("Created new PeerConnection")
    label_channel = {"send": None}
    video_track = {"track": None}
    detect_task = {"task": None}
    @pc.on("connectionstatechange")
    async def on_connection_state_change():
        print("Connection state is", pc.connectionState)
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            PCS.discard(pc)
            if detect_task["task"]:
                detect_task["task"].cancel()
    blackhole = MediaBlackhole()
    @pc.on("datachannel")
    def on_datachannel(channel):
        print("DataChannel created:", channel.label)
        if channel.label == "gestures":
            async def send_label(text):
                if channel.readyState == "open":
                    channel.send(text)
                blackhole = MediaBlackhole()
            # Start detection if video already received
            if video_track["track"]:
                 detect_task["task"] = asyncio.create_task(
                    consume_and_detect(video_track["track"], send_label)
                )
    @pc.on("track")
    def on_track(track):
        print("Track received:", track.kind)
        if track.kind == "video":
            video_track["track"] = track
            async def send_label(payload):
                if label_channel["send"] is not None:
                    await pc.setRemoteDescription(offer)
                else:
                    print("⚠️ Tried to send label but data channel not ready.")
            # Start detection only if data channel is ready
            if label_channel["send"] is not None:
                 detect_task["task"] = asyncio.create_task(
                    consume_and_detect(track, send_label)
                )
            @track.on("ended")
            async def on_ended():
                print("Track ended.")
                if detect_task["task"]:
                    detect_task["task"].cancel()
        else:
            blackhole.addTrack(track)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )
# ------------------ Web App ------------------
def make_app():
    app = web.Application(middlewares=[cors_middleware])
    async def handle_options(request):
     return web.Response(status=204)
    app.router.add_post("/offer", offer)
    async def on_shutdown(app):
        coros = [pc.close() for pc in PCS]
        await asyncio.gather(*coros)
        PCS.clear()
    app.on_shutdown.append(on_shutdown)
    return app
# ------------------ Server Startup ------------------
if __name__ == "__main__":
    web.run_app(make_app(), port=8080)
