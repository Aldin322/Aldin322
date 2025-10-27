"""FastAPI server exposing the Tal-inspired chess bot."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

import chess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from talbot import TalBotEngine


class MoveRequest(BaseModel):
    game_id: str
    uci: str


class MoveRecord(BaseModel):
    move_number: int
    white: str
    black: Optional[str]


class GameState(BaseModel):
    game_id: str
    fen: str
    turn: str
    status: str
    legal_moves: Dict[str, list]
    history: List[MoveRecord]


def describe_status(board: chess.Board) -> str:
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_insufficient_material():
        return "draw (insufficient material)"
    if board.can_claim_threefold_repetition():
        return "draw (threefold repetition available)"
    if board.can_claim_fifty_moves():
        return "draw (fifty-move rule available)"
    if board.is_check():
        return "check"
    return "ongoing"


def move_history(board: chess.Board) -> List[MoveRecord]:
    scratch = chess.Board()
    san_moves: List[str] = []
    for mv in board.move_stack:
        san_moves.append(scratch.san(mv))
        scratch.push(mv)

    history: List[MoveRecord] = []
    for index in range(0, len(san_moves), 2):
        move_number = index // 2 + 1
        white_san = san_moves[index]
        black_san = san_moves[index + 1] if index + 1 < len(san_moves) else None
        history.append(MoveRecord(move_number=move_number, white=white_san, black=black_san))
    return history


def serialize_state(game_id: str, board: chess.Board) -> GameState:
    legal_moves: Dict[str, list] = {}
    if not board.is_game_over() and board.turn == chess.WHITE:
        for move in board.legal_moves:
            source = chess.square_name(move.from_square)
            target = chess.square_name(move.to_square)
            moves = legal_moves.setdefault(source, [])
            moves.append({
                "to": target,
                "uci": move.uci(),
                "promotion": move.promotion,
            })
    return GameState(
        game_id=game_id,
        fen=board.fen(),
        turn="white" if board.turn == chess.WHITE else "black",
        status=describe_status(board),
        legal_moves=legal_moves,
        history=move_history(board),
    )


app = FastAPI(title="TalBot Chess Server", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

tal_engine = TalBotEngine()
_games: Dict[str, chess.Board] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/new", response_model=GameState)
async def new_game() -> GameState:
    game_id = str(uuid.uuid4())
    board = chess.Board()
    _games[game_id] = board
    return serialize_state(game_id, board)


@app.get("/api/state/{game_id}", response_model=GameState)
async def get_state(game_id: str) -> GameState:
    board = _games.get(game_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return serialize_state(game_id, board)


@app.post("/api/move", response_model=GameState)
async def play_move(move: MoveRequest) -> GameState:
    board = _games.get(move.game_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Game not found")

    try:
        chess_move = chess.Move.from_uci(move.uci)
    except ValueError as exc:  # pragma: no cover - guard clause
        raise HTTPException(status_code=400, detail="Invalid move format") from exc

    if chess_move not in board.legal_moves:
        raise HTTPException(status_code=400, detail="Illegal move")

    board.push(chess_move)
    if board.is_game_over():
        return serialize_state(move.game_id, board)

    # Engine responds as Black
    if board.turn == chess.BLACK:
        engine_move = tal_engine.choose_move(board)
        board.push(engine_move)

    return serialize_state(move.game_id, board)
