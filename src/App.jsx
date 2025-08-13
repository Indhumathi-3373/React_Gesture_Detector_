// src/App.jsx
import { useEffect, useRef, useState } from "react";

export default function App() {
  const localVideoRef = useRef(null);
  const pcRef = useRef(null);
  const channelRef = useRef(null);
  const [label, setLabel] = useState("-");
  const [running, setRunning] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(true);

  useEffect(() => {
    return () => {
      cleanup();
    };
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

    // 1) Get local camera
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    localVideoRef.current.srcObject = stream;

    // 2) Create RTCPeerConnection
    const pc = new RTCPeerConnection();
    pcRef.current = pc;

    // 3) Create a data channel the server can use to send labels
    const dc = pc.createDataChannel("gestures");
    channelRef.current = dc;
    dc.onopen = () => console.log("DataChannel open");
    dc.onmessage = (e) => {
      try {
        const { label, confidence } = JSON.parse(e.data);
        setLabel(`${label} (${(confidence * 100).toFixed(1)}%)`);
      } catch {
        setLabel(String(e.data));
      }
    };

    // 4) Add local tracks (video only)
    stream.getTracks().forEach((track) => pc.addTrack(track, stream));

    // 5) Offer/Answer with server
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
        <h1 style={{ margin: 0 }}>Gesture Detection Using Python</h1>
        <p style={{ marginTop: 8, opacity: 0.8 }}>
          Your camera streams to Python. The server sends back the detected gesture label.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 16, alignItems: "start" }}>
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            style={{ width: "100%", borderRadius: 12, border: "1px solid #ddd", background: "#000" }}
          />
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
