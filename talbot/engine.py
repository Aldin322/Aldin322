"""Chess engine inspired by Mikhail Tal's attacking style."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import chess


MATE_VALUE = 100_000


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 950,
    chess.KING: 0,
}


# Piece-square tables adapted from the Sunfish engine and tuned for activity.
PAWN_TABLE = [
     0,   5,   5, -10, -10,   5,   5,   0,
    10,  10,  10,   0,   0,  10,  10,  10,
     5,   5,  10,  20,  20,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,   5,  10,  25,  25,  10,   5,   5,
    10,  10,  20,  30,  30,  20,  10,  10,
    50,  50,  50,  50,  50,  50,  50,  50,
     0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_TABLE = [
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   0,   0,   0,   0,   0,   0,
     0,   0,   0,   0,   0,   0,   0,   0,
     5,   5,   5,   5,   5,   5,   5,   5,
    10,  10,  10,  10,  10,  10,  10,  10,
    15,  15,  15,  15,  15,  15,  15,  15,
    20,  20,  20,  20,  20,  20,  20,  20,
     0,   0,   0,   0,   0,   0,   0,   0,
]

QUEEN_TABLE = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]

KING_MID_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20,
]

KING_END_TABLE = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}


@dataclass
class TTEntry:
    depth: int
    value: int
    flag: str
    move: Optional[chess.Move]


@dataclass
class SearchState:
    start_time: float
    time_limit: float
    nodes: int = 0
    stop: bool = False
    transposition_table: Dict[str, TTEntry] = None
    killer_moves: Dict[int, List[chess.Move]] = None

    def __post_init__(self) -> None:
        if self.transposition_table is None:
            self.transposition_table = {}
        if self.killer_moves is None:
            self.killer_moves = {}

    def time_up(self) -> bool:
        if self.stop:
            return True
        if self.time_limit <= 0:
            return False
        if time.time() - self.start_time >= self.time_limit:
            self.stop = True
        return self.stop


class TalBotEngine:
    """Attacking chess engine with a sacrificial bias."""

    def __init__(
        self,
        max_depth: int = 4,
        time_limit: float = 2.5,
        sacrifice_bias: float = 12.0,
        attack_weight: float = 6.0,
        mobility_weight: float = 2.0,
    ) -> None:
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.sacrifice_bias = sacrifice_bias
        self.attack_weight = attack_weight
        self.mobility_weight = mobility_weight
        self.history_heuristic: Dict[Tuple[int, int], int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def choose_move(
        self,
        board: chess.Board,
        time_limit: Optional[float] = None,
        max_depth: Optional[int] = None,
    ) -> chess.Move:
        """Return the Tal-style move for the current board."""
        limit = self.time_limit if time_limit is None else time_limit
        depth_limit = self.max_depth if max_depth is None else max_depth

        state = SearchState(start_time=time.time(), time_limit=limit)
        best_move: Optional[chess.Move] = None
        best_value = -math.inf
        aspiration_window = 50

        for depth in range(1, depth_limit + 1):
            if state.time_up():
                break

            alpha = -MATE_VALUE
            beta = MATE_VALUE
            if best_value not in (-math.inf, math.inf):
                alpha = max(alpha, int(best_value) - aspiration_window)
                beta = min(beta, int(best_value) + aspiration_window)

            value, move = self._search_root(board, depth, alpha, beta, state)

            if state.time_up():
                break

            if move is not None:
                best_move = move
                best_value = value

            # Tighten aspiration window after successful iteration
            aspiration_window = max(15, aspiration_window // 2)

        if best_move is None:
            # Fallback to first legal move
            try:
                return next(board.legal_moves)
            except StopIteration:
                raise ValueError("No legal moves available")
        return best_move

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _search_root(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        state: SearchState,
    ) -> Tuple[int, Optional[chess.Move]]:
        best_value = -MATE_VALUE
        best_move: Optional[chess.Move] = None

        moves = self._order_moves(board, depth=0, hash_move=None, state=state)
        if not moves:
            # No legal moves
            if board.is_checkmate():
                return (-MATE_VALUE + depth, None)
            return (0, None)

        for move in moves:
            if state.time_up():
                break
            board.push(move)
            value = -self._negamax(board, depth - 1, -beta, -alpha, state, ply=1)
            board.pop()

            if state.time_up():
                break

            if value > best_value:
                best_value = value
                best_move = move
            if best_value > alpha:
                alpha = best_value
            if alpha >= beta:
                break

        return best_value, best_move

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        state: SearchState,
        ply: int,
    ) -> int:
        if state.time_up():
            return 0

        key = board.fen()
        entry = state.transposition_table.get(key)
        if entry and entry.depth >= depth:
            if entry.flag == "exact":
                return entry.value
            if entry.flag == "lower" and entry.value > alpha:
                alpha = entry.value
            elif entry.flag == "upper" and entry.value < beta:
                beta = entry.value
            if alpha >= beta:
                return entry.value

        alpha_orig = alpha

        if depth == 0:
            return self._quiescence(board, alpha, beta, state, ply)

        if board.is_checkmate():
            return -MATE_VALUE + ply
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        state.nodes += 1

        hash_move = entry.move if entry else None
        moves = self._order_moves(board, depth=ply, hash_move=hash_move, state=state)
        if not moves:
            if board.is_checkmate():
                return -MATE_VALUE + ply
            return 0

        best_value = -MATE_VALUE
        best_move = None

        for move in moves:
            if state.time_up():
                break
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, state, ply + 1)
            board.pop()

            if state.time_up():
                break

            if score > best_value:
                best_value = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                if not board.is_capture(move):
                    self._store_killer(state, ply, move)
                self._update_history(move, depth)
                break

        if best_move is None:
            return self._evaluate(board)

        flag = "exact"
        if best_value <= alpha_orig:
            flag = "upper"
        elif best_value >= beta:
            flag = "lower"
        state.transposition_table[key] = TTEntry(depth=depth, value=best_value, flag=flag, move=best_move)
        return best_value

    def _quiescence(
        self,
        board: chess.Board,
        alpha: int,
        beta: int,
        state: SearchState,
        ply: int,
    ) -> int:
        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        for move in self._generate_captures(board):
            if state.time_up():
                break
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, state, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def _order_moves(
        self,
        board: chess.Board,
        depth: int,
        hash_move: Optional[chess.Move],
        state: SearchState,
    ) -> List[chess.Move]:
        moves = list(board.legal_moves)
        if not moves:
            return moves

        def move_score(move: chess.Move) -> int:
            if hash_move and move == hash_move:
                return 10_000
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                value = 0
                if victim:
                    value += 10 * PIECE_VALUES[victim.piece_type]
                if attacker:
                    value -= PIECE_VALUES[attacker.piece_type]
                return 5_000 + value
            killers = state.killer_moves.get(depth, [])
            if move in killers:
                return 2_000
            value = self.history_heuristic.get((move.from_square, move.to_square), 0)
            return value

        moves.sort(key=move_score, reverse=True)
        return moves

    def _generate_captures(self, board: chess.Board) -> Iterable[chess.Move]:
        captures = [move for move in board.legal_moves if board.is_capture(move) or move.promotion]
        captures.sort(key=lambda m: self._capture_score(board, m), reverse=True)
        return captures

    def _capture_score(self, board: chess.Board, move: chess.Move) -> int:
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        victim_value = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
        attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
        return 10 * victim_value - attacker_value

    def _store_killer(self, state: SearchState, ply: int, move: chess.Move) -> None:
        killers = state.killer_moves.setdefault(ply, [])
        if move in killers:
            return
        killers.insert(0, move)
        if len(killers) > 2:
            killers.pop()

    def _update_history(self, move: chess.Move, depth: int) -> None:
        key = (move.from_square, move.to_square)
        self.history_heuristic[key] = self.history_heuristic.get(key, 0) + depth * depth

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _evaluate(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -MATE_VALUE
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        material = self._material_score(board)
        pst = self._piece_square_score(board)
        mobility = self._mobility_score(board)
        attack_pressure_white = self._king_pressure(board, chess.WHITE)
        attack_pressure_black = self._king_pressure(board, chess.BLACK)
        attack_pressure = (attack_pressure_white - attack_pressure_black) * self.attack_weight
        sacrifice = self._sacrifice_score(
            board,
            material_white=self._material_total(board, chess.WHITE),
            material_black=self._material_total(board, chess.BLACK),
            attack_white=attack_pressure_white,
            attack_black=attack_pressure_black,
        )
        tempo = 10 if board.turn == chess.WHITE else -10

        score = material + pst + mobility + attack_pressure + sacrifice + tempo
        return score if board.turn == chess.WHITE else -score

    def _material_score(self, board: chess.Board) -> int:
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += value * (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK)))
        return score

    def _material_total(self, board: chess.Board, color: chess.Color) -> int:
        total = 0
        for piece_type, value in PIECE_VALUES.items():
            total += value * len(board.pieces(piece_type, color))
        return total

    def _piece_square_score(self, board: chess.Board) -> int:
        score = 0
        for piece_type, table in PIECE_SQUARE_TABLES.items():
            for square in board.pieces(piece_type, chess.WHITE):
                score += table[square]
            for square in board.pieces(piece_type, chess.BLACK):
                score -= table[chess.square_mirror(square)]

        # King phase-aware evaluation
        phase = self._game_phase(board)
        king_table = [
            int(phase * mid + (1 - phase) * end_)
            for mid, end_ in zip(KING_MID_TABLE, KING_END_TABLE)
        ]
        for square in board.pieces(chess.KING, chess.WHITE):
            score += king_table[square]
        for square in board.pieces(chess.KING, chess.BLACK):
            score -= king_table[chess.square_mirror(square)]
        return score

    def _mobility_score(self, board: chess.Board) -> int:
        turn = board.turn
        board.turn = chess.WHITE
        white_moves = sum(1 for _ in board.legal_moves)
        board.turn = chess.BLACK
        black_moves = sum(1 for _ in board.legal_moves)
        board.turn = turn
        return self.mobility_weight * (white_moves - black_moves)

    def _king_pressure(self, board: chess.Board, color: chess.Color) -> int:
        enemy = not color
        king_square = board.king(enemy)
        if king_square is None:
            return 0
        pressure = 0
        king_ring = chess.SquareSet(chess.BB_KING_ATTACKS[king_square] | chess.BB_SQUARES[king_square])
        for square in king_ring:
            attackers = board.attackers(color, square)
            pressure += len(attackers)
        # Encourage coordinated attacks with queen and minor pieces
        queen_attacks = len(board.pieces(chess.QUEEN, color))
        pressure += queen_attacks
        return pressure

    def _sacrifice_score(
        self,
        board: chess.Board,
        material_white: int,
        material_black: int,
        attack_white: int,
        attack_black: int,
    ) -> int:
        material_diff = material_white - material_black
        attack_diff = attack_white - attack_black
        # Reward dynamic imbalance that favours attacks.
        base = -self.sacrifice_bias * material_diff
        attack_factor = int(1.5 * attack_diff)
        if material_diff < 0:
            base += int(0.4 * (-material_diff) * (attack_white + 1))
        elif material_diff > 0:
            base -= int(0.3 * material_diff * (attack_black + 1))
        return base + attack_factor

    def _game_phase(self, board: chess.Board) -> float:
        phase_weights = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 1,
            chess.ROOK: 2,
            chess.QUEEN: 4,
        }
        total = sum(weight for weight in phase_weights.values()) * 2
        remaining = 0
        for piece_type, weight in phase_weights.items():
            remaining += weight * (
                len(board.pieces(piece_type, chess.WHITE)) + len(board.pieces(piece_type, chess.BLACK))
            )
        phase = remaining / total if total else 1.0
        return min(1.0, max(0.0, phase))
