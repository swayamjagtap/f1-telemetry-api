import asyncio
import json

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from .datasets import (
    list_drivers,
    list_events,
    list_seasons,
    list_sessions,
)

from .telemetry import (
    DEFAULT_PLAYBACK_FPS,
    DEFAULT_PLAYBACK_FRAMES,
    build_playback_frames,
    load_driver_telemetry,
)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="F1 Telemetry API",
    description="Backend API for the F1 telemetry dashboard.",
    version="0.3.0",
)


# =========================================================
# CORS
# =========================================================
#
# These are the browser origins allowed to call the REST API.
#
# Production frontend:
#   https://swayamjagtap.github.io
#
# Local frontend testing:
#   http://localhost:5500
#   http://127.0.0.1:5500
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swayamjagtap.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT / HEALTH
# =========================================================

@app.get("/")
async def root():
    return {
        "name": "F1 Telemetry API",
        "status": "online",
        "version": "0.3.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


# =========================================================
# DATASET DISCOVERY
# =========================================================

@app.get("/api/seasons")
async def seasons():
    available_seasons = list_seasons()

    return {
        "seasons": available_seasons,
    }


@app.get("/api/events")
async def events(
    year: int = Query(
        ...,
        description="Season year",
    ),
):
    available_events = list_events(year)

    if not available_events:
        raise HTTPException(
            status_code=404,
            detail=f"No datasets found for season {year}.",
        )

    return {
        "year": year,
        "events": available_events,
    }


@app.get("/api/sessions")
async def sessions(
    year: int = Query(
        ...,
        description="Season year",
    ),
    event: str = Query(
        ...,
        description="Event directory ID",
    ),
):
    available_sessions = list_sessions(
        year=year,
        event=event,
    )

    if not available_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"No sessions found for {year}/{event}.",
        )

    return {
        "year": year,
        "event": event,
        "sessions": available_sessions,
    }


@app.get("/api/drivers")
async def drivers(
    year: int = Query(
        ...,
        description="Season year",
    ),
    event: str = Query(
        ...,
        description="Event directory ID",
    ),
    session: str = Query(
        ...,
        description="Session directory ID",
    ),
):
    available_drivers = list_drivers(
        year=year,
        event=event,
        session=session,
    )

    if not available_drivers:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No drivers found for "
                f"{year}/{event}/{session}."
            ),
        )

    return {
        "year": year,
        "event": event,
        "session": session,
        "drivers": available_drivers,
    }


# =========================================================
# REST TELEMETRY
# =========================================================

@app.get("/api/telemetry")
async def telemetry(
    year: int = Query(
        ...,
        description="Season year",
    ),
    event: str = Query(
        ...,
        description="Event directory ID",
    ),
    session: str = Query(
        ...,
        description="Session directory ID",
    ),
    driver: str = Query(
        ...,
        description="Driver abbreviation",
    ),
    lap: int | None = Query(
        None,
        description="Optional lap number",
    ),
):
    try:
        telemetry_data = load_driver_telemetry(
            year=year,
            event=event,
            session=session,
            driver=driver,
            lap=lap,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if telemetry_data.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No telemetry found for driver "
                f"{driver.upper()}."
            ),
        )

    records = telemetry_data.to_dict(
        orient="records"
    )

    return {
        "year": year,
        "event": event,
        "session": session,
        "driver": driver.upper(),
        "lap": lap,
        "count": len(records),
        "telemetry": records,
    }


# =========================================================
# WEBSOCKET TELEMETRY PLAYBACK
# =========================================================

@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        request = await websocket.receive_json()

        year = int(
            request.get("year", 2025)
        )

        event = str(
            request.get("event", "")
        ).strip().lower()

        session = str(
            request.get("session", "")
        ).strip().lower()

        lap = int(
            request.get("lap")
        )

        requested_drivers = request.get(
            "drivers"
        )

        if requested_drivers is None:
            requested_drivers = [
                driver["driver"]
                for driver in list_drivers(
                    year=year,
                    event=event,
                    session=session,
                )
            ]

        drivers = [
            str(driver).strip().upper()
            for driver in requested_drivers
            if str(driver).strip()
        ]

        frames = int(
            request.get(
                "frames",
                DEFAULT_PLAYBACK_FRAMES,
            )
        )

        fps = float(
            request.get(
                "fps",
                DEFAULT_PLAYBACK_FPS,
            )
        )

        # Keep client-supplied values reasonable.
        frames = max(
            2,
            min(frames, 2000),
        )

        fps = max(
            1.0,
            min(fps, 60.0),
        )

        playback = build_playback_frames(
            year=year,
            event=event,
            session=session,
            lap=lap,
            drivers=drivers,
            frames=frames,
        )

        if not playback:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": (
                            "No telemetry found "
                            "for the requested "
                            "drivers/lap."
                        ),
                    }
                )
            )

            await websocket.close()

            return

        # Determine which drivers actually made it
        # into the generated playback.
        playback_drivers = sorted(
            {
                frame_driver["driver"]
                for frame in playback
                for frame_driver in frame["drivers"]
            }
        )

        if not playback_drivers:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": (
                            "Playback was generated, "
                            "but contained no drivers."
                        ),
                    }
                )
            )

            await websocket.close()

            return

        # Tell the client what playback it actually received.
        await websocket.send_text(
            json.dumps(
                {
                    "type": "ready",
                    "year": year,
                    "event": event,
                    "session": session,
                    "lap": lap,
                    "drivers": playback_drivers,
                    "frames": len(playback),
                    "fps": fps,
                }
            )
        )

        # =================================================
        # STREAM FRAMES
        # =================================================

        delay = 1.0 / fps

        for frame in playback:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "frame",
                        **frame,
                    }
                )
            )

            await asyncio.sleep(delay)

        # =================================================
        # PLAYBACK COMPLETE
        # =================================================

        await websocket.send_text(
            json.dumps(
                {
                    "type": "complete",
                    "frames": len(playback),
                }
            )
        )

    except WebSocketDisconnect:
        return

    except Exception as exc:
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": str(exc),
                    }
                )
            )

            await websocket.close()

        except Exception:
            pass