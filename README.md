# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.



# React_Gesture_Detector_

This project streams your camera to a Python server which detects hand gestures and sends back the gesture label in real-time. The frontend is built with React, and the backend can be implemented using Python + WebRTC.

---

## Features

- One-way video streaming from browser to server
- Real-time gesture detection
- Shows detected gesture label in the UI
- Start/Stop camera streaming
- Enable/Disable camera without stopping the connection
---

## Prerequisites

- Node.js (v18+ recommended)
- npm or yarn
- Python 3.8+
- Web browser with camera support
- Backend Python server with WebRTC support

---

## Setup Frontend (React)

```bash
# Clone the repository
git clone https://github.com/Bagavathisingh/React_Gesture_Detector_.git
cd React_Gesture_Detector_

# Install dependencies
npm install
# or
yarn install

# Start the frontend
npm start
# or
yarn start
```

## SetUp Backend (Python)

```bash

cd gestureController

# after Changing The Directory

python server.py

```
