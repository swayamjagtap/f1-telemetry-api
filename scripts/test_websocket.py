import asyncio
import json

import websockets


WS_URL = "ws://127.0.0.1:8000/ws/telemetry"

REQUEST = {
    "year": 2025,
    "event": "abu_dhabi",
    "session": "qualifying",
    "lap": 17,
    "drivers": ["VER", "LEC"],
    "frames": 20,
    "fps": 5,
}


async def main():
    async with websockets.connect(WS_URL) as websocket:
        await websocket.send(json.dumps(REQUEST))

        frame_count = 0

        while True:
            message = await websocket.recv()
            data = json.loads(message)

            print(json.dumps(data, indent=2))

            if data["type"] == "frame":
                frame_count += 1

                if frame_count >= 3:
                    print("\nReceived 3 frames successfully.")
                    break

            elif data["type"] == "error":
                print("\nWebSocket returned an error.")
                break


if __name__ == "__main__":
    asyncio.run(main())