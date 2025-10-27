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

- Python chess engine biased toward initiative, king attacks, and speculative sacrifices.
- Alpha-beta search with move ordering, killer moves, quiescence search, and tapered evaluation.
- FastAPI-powered web server exposing REST endpoints and a responsive front-end with Unicode
  pieces and move log.

### Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 to challenge TalBot as White. Moves are submitted automatically by
clicking source and destination squares; the engine responds immediately as Black.
