#!/usr/bin/env python3
"""Arranca el servidor Triunfo MVP.

Uso:
    python run.py
    python run.py --port 8001
    python run.py --reload     (modo desarrollo)
"""
import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Triunfo MVP Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"\n  Triunfo MVP arrancando en http://localhost:{args.port}")
    print(f"  UI:   http://localhost:{args.port}/app")
    print(f"  Docs: http://localhost:{args.port}/docs\n")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
