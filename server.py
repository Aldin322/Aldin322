"""FastAPI server exposing the Tal-inspired chess bot."""
from __future__ import annotations

import errno
import os
import socket
import uuid
from contextlib import closing
from typing import Dict, List, Optional

import chess
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from talbot import TalBotEngine


PROMOTION_FROM_SYMBOL = {
    "q": chess.QUEEN,
    "r": chess.ROOK,
    "b": chess.BISHOP,
    "n": chess.KNIGHT,
}
PROMOTION_TO_SYMBOL = {value: key for key, value in PROMOTION_FROM_SYMBOL.items()}


class MoveRequest(BaseModel):
    game_id: str
    uci: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    promotion: Optional[str] = None

    def resolve(self, board: chess.Board) -> chess.Move:
        """Convert the request payload into a :class:`~chess.Move`."""

        if self.uci:
            return chess.Move.from_uci(self.uci.lower())

        if not self.source or not self.target:
            raise ValueError("Move request must include either a UCI string or source/target squares")

        try:
            from_square = chess.parse_square(self.source.lower())
            to_square = chess.parse_square(self.target.lower())
        except ValueError as exc:
            raise ValueError("Invalid square coordinates") from exc

        promotion_piece: Optional[int] = None
        if self.promotion:
            promo_key = self.promotion.lower()
            promotion_piece = PROMOTION_FROM_SYMBOL.get(promo_key)
            if promotion_piece is None:
                raise ValueError("Invalid promotion piece")

        move = chess.Move(from_square, to_square, promotion=promotion_piece)
        if promotion_piece and move.promotion is None:
            # The promotion specification is inconsistent with the move geometry.
            raise ValueError("Promotion piece is not valid for the supplied move")
        return move


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
                "source": source,
                "to": target,
                "uci": move.uci(),
                "promotion": PROMOTION_TO_SYMBOL.get(move.promotion),
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

tal_engine = TalBotEngine(
    max_depth=12,
    time_limit=12.0,
    sacrifice_bias=9.0,
    attack_weight=8.5,
    king_safety_weight=6.5,
    mobility_weight=3.2,
    center_weight=2.4,
    tropism_weight=2.6,
    threat_weight=3.1,
)
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
        chess_move = move.resolve(board)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


def _is_port_available(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                return False
            raise
    return True


def _choose_port(host: str, preferred_port: int, attempts: int = 20) -> int:
    port = preferred_port
    for _ in range(attempts):
        if _is_port_available(host, port):
            return port
        port += 1
    raise RuntimeError(
        f"Unable to find an open port in range {preferred_port}-{port - 1}."
    )


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    reload_enabled = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}
    base_port = int(os.getenv("PORT", "8000"))
    try:
        port = _choose_port(host, base_port)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    if port != base_port:
        print(f"Port {base_port} unavailable; using {port} instead.")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info",
    )


if __name__ == "__main__":
    main()
