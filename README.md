- 👋 Hi, I’m @Aldin322
- 👀 I’m interested in python, javascript, c++
- 🌱 I’m currently learning some python modules along with javascript, and a bit c++
- 💞️ I’m looking to collaborate on python opencv, socket, requests projects, if you are learning and want to make a project, feel free to contact me
- 📫 You can reach me via discord: Aldin#6666

<!---
Aldin322/Aldin322 is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->

## TalBot – Tal-inspired chess engine

This repository now includes **TalBot**, a sacrificial chess engine with a lightweight web interface
for playing against it online.

### Features

- Python chess engine biased toward initiative, king attacks, and selectively sound sacrifices.
- Alpha-beta search with deep pruning, killer/history heuristics, tapered evaluation, and new pawn/rook/king heuristics to keep
  play around the 2400 level.
- PyTorch-backed neural evaluator that fuses tactical pressure, king safety, and initiative features into a Tal-style score.
- Center control, threat-tracking, and king-tropism evaluation layers that reward only well-supported sacrificial attacks and
  punish speculative material gifts.
- FastAPI-powered web server exposing REST endpoints and a responsive front-end with Unicode
  pieces, move log, and a board overlay that locks interaction while the engine is thinking.
- Coordinate-aware move API that accepts either UCI strings or square-based payloads, protecting the server from malformed client submissions.

### Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional: install PyTorch to enable the accelerated neural evaluator
# pip install torch
python server.py
```

The helper script will honour optional environment variables such as `PORT`, `HOST`, and `RELOAD`.
If the requested port is busy, TalBot will automatically scan for the next available port and log the
chosen value, preventing the "Address already in use" crash seen when reloading uvicorn manually.

Then open the reported address (default `http://localhost:8000`) to challenge TalBot as White. Moves are
submitted automatically by clicking source and destination squares; the engine responds immediately as Black.

### Testing

Run the automated checks once dependencies are installed:

```bash
pytest
```

The suite exercises the HTTP API end-to-end and verifies the engine finds forced tactical wins such as the classic
Qxf7# mate in one, giving confidence that TalBot responds with legal, decisive play.
