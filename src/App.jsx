// src/App.jsx
import { useEffect, useRef, useState } from "react";
import * as mpHands from "@mediapipe/hands";
import { Camera } from "@mediapipe/camera_utils";

export default function App() {
  const localVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const pcRef = useRef(null);
  const channelRef = useRef(null);
  const [label, setLabel] = useState("-");
  const [running, setRunning] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(true);

  useEffect(() => {
    return () => cleanup();
  }, []);

  const cleanup = () => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    const v = localVideoRef.current;
    if (v && v.srcObject) {
      v.srcObject.getTracks().forEach((t) => t.stop());
      v.srcObject = null;
    }
  };

  const start = async () => {
    if (running) return;

    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    localVideoRef.current.srcObject = stream;

    // 🔹 Setup Mediapipe Hands
    const hands = new mpHands.Hands({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
    });
    hands.setOptions({
      maxNumHands: 1,
      modelComplexity: 1,
      minDetectionConfidence: 0.7,
      minTrackingConfidence: 0.7,
    });

    hands.onResults((results) => {
  const canvas = canvasRef.current;
  const ctx = canvas?.getContext("2d");
  if (!canvas || !ctx) return;

  canvas.width = localVideoRef.current.videoWidth;
  canvas.height = localVideoRef.current.videoHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

  if (results.multiHandLandmarks) {
    results.multiHandLandmarks.forEach((landmarks) => {
      for (let lm of landmarks) {
        ctx.beginPath();
        ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 5, 0, 2 * Math.PI);
        ctx.fillStyle = "red";
        ctx.fill();
      }
    });
  }
});

    // Connect Mediapipe camera
    const camera = new Camera(localVideoRef.current, {
      onFrame: async () => {
        await hands.send({ image: localVideoRef.current });
      },
      width: 640,
      height: 480,
    });
    camera.start();

    const pc = new RTCPeerConnection();
    pcRef.current = pc;

    const dc = pc.createDataChannel("gestures");
    channelRef.current = dc;
   dc.onmessage = (e) => {
  try {
    const { label, confidence } = JSON.parse(e.data);
    setLabel(`${label} (${(confidence * 100).toFixed(1)}%)`);
  } catch {
    setLabel(String(e.data));
  }
};


    stream.getTracks().forEach((track) => pc.addTrack(track, stream));

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const resp = await fetch("http://localhost:8080/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
    });
    const answer = await resp.json();
    await pc.setRemoteDescription(answer);

    setRunning(true);
    setCameraEnabled(true);
  };

  const stop = () => {
    setRunning(false);
    cleanup();
    setLabel("-");
    setCameraEnabled(false);
  };

  const toggleCamera = () => {
    const videoTrack = localVideoRef.current?.srcObject?.getVideoTracks()[0];
    if (videoTrack) {
      videoTrack.enabled = !videoTrack.enabled;
      setCameraEnabled(videoTrack.enabled);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", fontFamily: "system-ui" }}>
      <div style={{ width: 900, maxWidth: "95vw" }}>
        <h1>Gesture Detection Using Python + Hand Landmarks</h1>
        <p>Your camera streams to Python, but we also draw landmarks locally in React.</p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 16 }}>
          <div style={{ position: "relative" }}>
            <video
              ref={localVideoRef}
              autoPlay
              playsInline
              muted
              style={{ width: "100%", borderRadius: 12, border: "1px solid #ddd", background: "#000" }}
            />
            <canvas
              ref={canvasRef}
              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
            />
          </div>
          <div style={{ padding: 16, border: "1px solid #eee", borderRadius: 12 }}>
            <div style={{ fontSize: 14, opacity: 0.7, marginBottom: 6 }}>Detected gesture</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 16 }}>{label}</div>

            {!running ? (
              <button onClick={start} style={btnStyle}>Start</button>
            ) : (
              <>
                <button onClick={stop} style={{ ...btnStyle, background: "#e11d48", marginBottom: 8 }}>Stop</button>
                <button onClick={toggleCamera} style={{ ...btnStyle, background: cameraEnabled ? "#facc15" : "#10b981" }}>
                  {cameraEnabled ? "Disable Camera" : "Enable Camera"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const btnStyle = {
  background: "#2563eb",
  color: "white",
  border: "none",
  padding: "10px 16px",
  borderRadius: 10,
  cursor: "pointer",
  fontWeight: 600,
};

