# import asyncio
# import json
# import cv2
# import numpy as np
# from aiohttp import web
# from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
# from aiortc.contrib.media import MediaBlackhole
# from av import VideoFrame
# from ultralytics import YOLO
# import mediapipe as mp
# import time

# yolo_model = YOLO('C:/Users/bugzx/OneDrive/Desktop/v0dev_codes/YOLOv10n_gestures.pt')

# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils
# hands = mp_hands.Hands(
#     static_image_mode=False,
#     max_num_hands=1,
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5
# )

# def get_landmark_ratios(landmarks):
#     coords = np.array([(lm.x, lm.y) for lm in landmarks.landmark])
#     wrist = coords[0]
#     coords -= wrist
#     max_dist = np.max(np.linalg.norm(coords, axis=1))
#     coords /= max_dist if max_dist != 0 else 1
#     return coords.flatten()

# CAP = cv2.VideoCapture(0)
# CAP_LOCK = asyncio.Lock()

# class GestureVideoTrack(VideoStreamTrack):
#     """ A VideoStreamTrack that captures frames from the local camera,
#         runs YOLO + MediaPipe overlays, and yields processed frames.
#     """
#     def __init__(self, fps=20):
#         super().__init__()
#         self.fps = fps
#         self._start = time.time()

#     async def recv(self):
#         pts, time_base = await self.next_timestamp()

#         async with CAP_LOCK:
#             ret, frame = CAP.read()
#         if not ret:
#             h, w = 480, 640
#             frame = np.zeros((h, w, 3), dtype=np.uint8)

#         results = yolo_model(frame)

#         for r in results:
#             if not hasattr(r, 'boxes') or r.boxes is None:
#                 continue
#             for box in r.boxes:
#                 x1, y1, x2, y2 = map(int, box.xyxy[0])
#                 x1, y1 = max(0, x1), max(0, y1)
#                 x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

#                 if x2 <= x1 or y2 <= y1:
#                     continue

#                 cropped_hand = frame[y1:y2, x1:x2]
#                 if cropped_hand.size == 0:
#                     continue

#                 rgb_hand = cv2.cvtColor(cropped_hand, cv2.COLOR_BGR2RGB)
#                 res = hands.process(rgb_hand)

#                 if res.multi_hand_landmarks:
#                     for hand_landmarks in res.multi_hand_landmarks:
#                         mp_drawing.draw_landmarks(
#                             cropped_hand,
#                             hand_landmarks,
#                             mp_hands.HAND_CONNECTIONS
#                         )
#                         cv2.putText(frame, "Hand Detected", (x1, min(y2 - 5, y1 + 20)),
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

#                 cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

#         av_frame = VideoFrame.from_ndarray(frame, format="bgr24")
#         av_frame.pts = pts
#         av_frame.time_base = time_base
#         return av_frame

# PCS = set()

# async def offer(request):
#     params = await request.json()
#     offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

#     pc = RTCPeerConnection()
#     PCS.add(pc)
#     media_blackhole = MediaBlackhole()

#     @pc.on("connectionstatechange")
#     async def on_connectionstatechange():
#         print("Connection state:", pc.connectionState)
#         if pc.connectionState in ["failed", "closed"]:
#             await pc.close()
#             PCS.discard(pc)

#     gesture_track = GestureVideoTrack()
#     pc.addTrack(gesture_track)

#     @pc.on("track")
#     async def on_track(track):
#         print("Received track", track.kind)
#         if track.kind in ["audio", "video"]:
#             await media_blackhole.addTrack(track)

#     await pc.setRemoteDescription(offer)
#     answer = await pc.createAnswer()
#     await pc.setLocalDescription(answer)

#     return web.json_response(
#         {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
#     )

# async def on_shutdown(app):
#     coros = [pc.close() for pc in list(PCS)]
#     await asyncio.gather(*coros)
#     CAP.release()

# # --- CORS middleware ---
# @web.middleware
# async def cors_middleware(request, handler):
#     if request.method == "OPTIONS":
#         resp = web.Response(status=200)
#     else:
#         resp = await handler(request)
#     resp.headers["Access-Control-Allow-Origin"] = "*"
#     resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
#     resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
#     return resp

# if __name__ == "__main__":
#     app = web.Application(middlewares=[cors_middleware])
#     app.router.add_post("/offer", offer)
#     app.on_shutdown.append(on_shutdown)
#     web.run_app(app, port=8080)









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
        # Preflight response
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
