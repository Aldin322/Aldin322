from pathlib import Path
import sys

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from talbot import TalBotEngine


def test_engine_returns_legal_move() -> None:
    engine = TalBotEngine(max_depth=3, time_limit=0.0)
    board = chess.Board()
    move = engine.choose_move(board, max_depth=2, time_limit=0.0)
    assert move in board.legal_moves


def test_engine_finds_mate_in_one() -> None:
    engine = TalBotEngine(max_depth=5, time_limit=0.0)
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
    move = engine.choose_move(board, max_depth=3, time_limit=0.0)
    assert move == chess.Move.from_uci("h5f7")
