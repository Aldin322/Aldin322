"""TalBot: a fresh sacrificial chess engine built from scratch."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import chess


MATE_SCORE = 1_000_000
MATE_THRESHOLD = MATE_SCORE - 1_000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 325,
    chess.BISHOP: 330,
    chess.ROOK: 520,
    chess.QUEEN: 1_000,
    chess.KING: 0,
}


# Piece-square tables tuned for central control and king aggression.
PAWN_TABLE = [
      0,   5,  10,  20,  20,  10,   5,   0,
     10,  20,  25,  35,  35,  25,  20,  10,
      5,  15,  20,  30,  30,  20,  15,   5,
      0,   5,  15,  25,  25,  15,   5,   0,
      0,   0,   5,  20,  20,   5,   0,   0,
     -5,  -5,   5,  10,  10,   5,  -5,  -5,
    -10, -10, -10, -20, -20, -10, -10, -10,
      0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_TABLE = [
    -50, -40, -25, -20, -20, -25, -40, -50,
    -35, -15,   0,   5,   5,   0, -15, -35,
    -25,   5,  20,  25,  25,  20,   5, -25,
    -15,  10,  25,  30,  30,  25,  10, -15,
    -15,   5,  20,  30,  30,  20,   5, -15,
    -25,   0,  15,  20,  20,  15,   0, -25,
    -40, -20,  -5,   0,   0,  -5, -20, -40,
    -55, -35, -30, -30, -30, -30, -35, -55,
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,  10,  15,  15,  10,   5, -10,
     -5,  10,  15,  20,  20,  15,  10,  -5,
     -5,  10,  20,  25,  25,  20,  10,  -5,
     -5,  10,  20,  25,  25,  20,  10,  -5,
    -10,   5,  10,  15,  15,  10,   5, -10,
    -15, -10,  -5,   0,   0,  -5, -10, -15,
    -20, -15, -15, -15, -15, -15, -15, -20,
]

ROOK_TABLE = [
      0,   0,   5,  10,  10,   5,   0,   0,
      0,   0,  10,  15,  15,  10,   0,   0,
      0,   0,  10,  15,  15,  10,   0,   0,
      5,  10,  15,  20,  20,  15,  10,   5,
      5,  10,  15,  20,  20,  15,  10,   5,
     10,  10,  15,  20,  20,  15,  10,  10,
     10,  10,  15,  20,  20,  15,  10,  10,
      0,   0,   5,  10,  10,   5,   0,   0,
]

QUEEN_TABLE = [
    -15, -10, -10,  -5,  -5, -10, -10, -15,
    -10,  -5,   0,   0,   0,   0,  -5, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,   0,
      0,   0,   5,   5,   5,   5,   0,   0,
     -5,   0,   5,   5,   5,   5,   0,  -5,
    -10,  -5,   0,   0,   0,   0,  -5, -10,
    -15, -10, -10,  -5,  -5, -10, -10, -15,
]

KING_MIDDLEGAME = [
    -40, -30, -30, -40, -40, -30, -30, -40,
    -30, -20, -20, -30, -30, -20, -20, -30,
    -20, -10, -10, -20, -20, -10, -10, -20,
    -20,  -5,   0,  -5,  -5,   0,  -5, -20,
    -10,   0,  10,  20,  20,  10,   0, -10,
     -5,   5,  15,  25,  25,  15,   5,  -5,
     20,  25,  30,  35,  35,  30,  25,  20,
     20,  30,  30,  40,  40,  30,  30,  20,
]

KING_ENDGAME = [
    -30, -20, -20, -20, -20, -20, -20, -30,
    -20, -10,   0,   0,   0,   0, -10, -20,
    -20,   0,  10,  15,  15,  10,   0, -20,
    -20,   0,  15,  25,  25,  15,   0, -20,
    -20,   0,  15,  25,  25,  15,   0, -20,
    -20,   0,  10,  15,  15,  10,   0, -20,
    -20, -10,   0,   0,   0,   0, -10, -20,
    -30, -20, -20, -20, -20, -20, -20, -30,
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}

PASSED_PAWN_BONUS = [0, 18, 35, 60, 95, 150, 230, 0]
ISOLATED_PAWN_PENALTY = 18
DOUBLED_PAWN_PENALTY = 14
ROOK_OPEN_FILE_BONUS = 28
ROOK_SEMI_OPEN_FILE_BONUS = 14
BISHOP_PAIR_BONUS = 35
CENTER_SQUARES = [chess.D4, chess.E4, chess.D5, chess.E5]
EXTENDED_CENTER = [
    chess.C3,
    chess.C4,
    chess.C5,
    chess.C6,
    chess.D3,
    chess.D4,
    chess.D5,
    chess.D6,
    chess.E3,
    chess.E4,
    chess.E5,
    chess.E6,
    chess.F3,
    chess.F4,
    chess.F5,
    chess.F6,
]
TROPISM_PIECES = {chess.QUEEN: 14, chess.ROOK: 10, chess.BISHOP: 9, chess.KNIGHT: 8}


@dataclass
class TTEntry:
    depth: int
    value: int
    flag: str
    move: Optional[chess.Move]
    ply: int


@dataclass
class SearchState:
    start_time: float
    time_limit: float
    transposition: Dict[int, TTEntry] = field(default_factory=dict)
    killers: Dict[int, List[chess.Move]] = field(default_factory=dict)
    history: Dict[Tuple[int, int], int] = field(default_factory=dict)
    nodes: int = 0
    stop: bool = False

    def time_exceeded(self) -> bool:
        if self.stop:
            return True
        if self.time_limit <= 0:
            return False
        if time.time() - self.start_time >= self.time_limit:
            self.stop = True
        return self.stop


class TalBotEngine:
    """A new Tal-inspired chess engine favouring sound sacrifices."""

    def __init__(
        self,
        max_depth: int = 9,
        time_limit: float = 6.0,
        sacrifice_bias: float = 12.0,
        attack_weight: float = 7.0,
        king_safety_weight: float = 6.0,
        mobility_weight: float = 3.0,
        center_weight: float = 2.0,
        tropism_weight: float = 2.0,
        threat_weight: float = 2.5,
    ) -> None:
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.sacrifice_bias = sacrifice_bias
        self.attack_weight = attack_weight
        self.king_safety_weight = king_safety_weight
        self.mobility_weight = mobility_weight
        self.center_weight = center_weight
        self.tropism_weight = tropism_weight
        self.threat_weight = threat_weight

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def choose_move(
        self,
        board: chess.Board,
        time_limit: Optional[float] = None,
        max_depth: Optional[int] = None,
    ) -> chess.Move:
        """Return the best move according to the TalBot engine."""

        limit = self.time_limit if time_limit is None else time_limit
        depth_cap = self.max_depth if max_depth is None else max_depth
        state = SearchState(start_time=time.time(), time_limit=limit)

        best_move: Optional[chess.Move] = None
        best_value = -math.inf
        aspiration = 50

        for depth in range(1, depth_cap + 1):
            if state.time_exceeded():
                break

            alpha = -MATE_SCORE
            beta = MATE_SCORE
            window = aspiration
            if best_value not in (-math.inf, math.inf):
                alpha = max(alpha, int(best_value) - window)
                beta = min(beta, int(best_value) + window)

            while True:
                value, move = self._search_root(board, depth, alpha, beta, state, best_move)

                if state.time_exceeded():
                    break

                if value <= alpha and alpha > -MATE_SCORE:
                    alpha = max(-MATE_SCORE, alpha - max(50, window * 2))
                    continue
                if value >= beta and beta < MATE_SCORE:
                    beta = min(MATE_SCORE, beta + max(50, window * 2))
                    continue
                break

            if state.time_exceeded():
                break

            if move is not None:
                best_move = move
                best_value = value

            aspiration = max(25, aspiration // 2)

        if best_move is None:
            try:
                return next(board.legal_moves)
            except StopIteration as exc:  # pragma: no cover
                raise ValueError("No legal moves available") from exc
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
        pv_hint: Optional[chess.Move],
    ) -> Tuple[int, Optional[chess.Move]]:
        best_value = -MATE_SCORE
        best_move: Optional[chess.Move] = None

        key = self._hash(board)
        tt_entry = state.transposition.get(key)
        hash_move = pv_hint or (tt_entry.move if tt_entry else None)
        moves = self._order_moves(board, 0, hash_move, state)

        if not moves:
            if board.is_checkmate():
                return -MATE_SCORE + depth, None
            return 0, None

        for move in moves:
            if state.time_exceeded():
                break
            board.push(move)
            value = -self._pv_search(board, depth - 1, -beta, -alpha, state, 1)
            board.pop()

            if state.time_exceeded():
                break

            if value > best_value:
                best_value = value
                best_move = move
            if best_value > alpha:
                alpha = best_value
            if alpha >= beta:
                break

        if best_move is not None:
            state.transposition[key] = TTEntry(depth, best_value, "exact", best_move, 0)
        return best_value, best_move

    def _pv_search(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        state: SearchState,
        ply: int,
    ) -> int:
        if state.time_exceeded():
            return 0

        key = self._hash(board)
        entry = state.transposition.get(key)
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
        in_check = board.is_check()
        if in_check:
            depth += 1

        if depth <= 0:
            return self._quiescence(board, alpha, beta, state, ply)

        if board.is_checkmate():
            return -MATE_SCORE + ply
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        state.nodes += 1

        # Null move pruning
        if depth >= 3 and not in_check and self._can_null_move(board):
            board.push(chess.Move.null())
            null_score = -self._pv_search(board, depth - 1 - 2, -beta, -beta + 1, state, ply + 1)
            board.pop()
            if null_score >= beta:
                return beta

        tt_move = entry.move if entry else None
        moves = self._order_moves(board, ply, tt_move, state)
        if not moves:
            if in_check:
                return -MATE_SCORE + ply
            return self._evaluate(board)

        best_value = -MATE_SCORE
        best_move: Optional[chess.Move] = None

        for index, move in enumerate(moves):
            if state.time_exceeded():
                break

            is_capture = board.is_capture(move)

            board.push(move)

            gives_check = board.is_check()

            reduction = 0
            if (
                depth >= 3
                and index >= 3
                and not is_capture
                and not gives_check
                and move.promotion is None
            ):
                reduction = 1 + (1 if index > 6 else 0)

            new_depth = depth - 1
            if gives_check and depth > 1:
                new_depth += 1
            if new_depth < 0:
                new_depth = 0

            if (
                new_depth <= 2
                and not is_capture
                and not gives_check
                and move.promotion is None
                and not in_check
            ):
                static_eval = self._evaluate(board)
                futility_margin = 150 + 100 * new_depth
                if static_eval + futility_margin <= alpha:
                    board.pop()
                    continue

            if index == 0:
                score = -self._pv_search(board, new_depth, -beta, -alpha, state, ply + 1)
            else:
                score = -self._pv_search(board, max(0, new_depth - reduction), -alpha - 1, -alpha, state, ply + 1)
                if score > alpha:
                    score = -self._pv_search(board, new_depth, -beta, -alpha, state, ply + 1)

            board.pop()

            if state.time_exceeded():
                break

            if score > best_value:
                best_value = score
                best_move = move
            if score > alpha:
                alpha = score
                if not is_capture:
                    self._update_history(move, depth, state)
            if alpha >= beta:
                if not is_capture:
                    self._store_killer(move, ply, state)
                    self._update_history(move, depth, state)
                break

        if best_move is None:
            return self._evaluate(board)

        flag = "exact"
        if best_value <= alpha_orig:
            flag = "upper"
        elif best_value >= beta:
            flag = "lower"

        state.transposition[key] = TTEntry(depth, best_value, flag, best_move, ply)
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
        if stand_pat > alpha:
            alpha = stand_pat

        captures = list(self._generate_tactical_moves(board))
        for move in captures:
            if state.time_exceeded():
                break
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, state, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # ------------------------------------------------------------------
    # Move ordering and helpers
    # ------------------------------------------------------------------
    def _order_moves(
        self,
        board: chess.Board,
        ply: int,
        hash_move: Optional[chess.Move],
        state: SearchState,
    ) -> List[chess.Move]:
        killers = state.killers.get(ply, [])

        moves = list(board.legal_moves)

        def move_score(move: chess.Move, order_index: int) -> int:
            if move == hash_move:
                return 1_000_000
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                victim_val = 0 if victim is None else PIECE_VALUES.get(victim.piece_type, 0)
                attacker_val = 0 if attacker is None else PIECE_VALUES.get(attacker.piece_type, 0)
                return 600_000 + 100 * victim_val - attacker_val - 15 * order_index
            if move in killers:
                return 450_000 - killers.index(move) * 1_000
            history_score = state.history.get((move.from_square, move.to_square), 0)
            if move.promotion:
                history_score += 10_000
            if self._gives_check(board, move):
                history_score += 5_000
            return history_score

        scored: List[Tuple[int, chess.Move]] = []
        for idx, mv in enumerate(moves):
            scored.append((move_score(mv, idx), mv))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [mv for _, mv in scored]

    def _generate_tactical_moves(self, board: chess.Board) -> Iterable[chess.Move]:
        moves = list(board.legal_moves)
        for move in moves:
            gives_check = self._gives_check(board, move)
            if board.is_capture(move) or gives_check or move.promotion is not None:
                if self._see_ge(board, move, 0):
                    yield move

    def _see_ge(self, board: chess.Board, move: chess.Move, threshold: int) -> bool:
        see = getattr(board, "see", None)
        if callable(see):
            return see(move, threshold=threshold)
        # Fallback: optimistic MVV-LVA estimate.
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        victim_val = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
        attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
        return victim_val - attacker_val >= threshold

    def _gives_check(self, board: chess.Board, move: chess.Move) -> bool:
        pushed = False
        try:
            board.push(move)
            pushed = True
            return board.is_check()
        except Exception:
            analysis = board.copy(stack=False)
            try:
                analysis.push(move)
            except Exception:
                return False
            return analysis.is_check()
        finally:
            if pushed:
                board.pop()

    def _store_killer(self, move: chess.Move, ply: int, state: SearchState) -> None:
        killers = state.killers.setdefault(ply, [])
        if move in killers:
            return
        killers.insert(0, move)
        if len(killers) > 2:
            killers.pop()

    def _update_history(self, move: chess.Move, depth: int, state: SearchState) -> None:
        key = (move.from_square, move.to_square)
        bonus = depth * depth
        state.history[key] = state.history.get(key, 0) + bonus

    def _can_null_move(self, board: chess.Board) -> bool:
        if board.turn == chess.WHITE:
            material = sum(PIECE_VALUES[p.piece_type] for p in board.piece_map().values() if p.color == chess.WHITE)
        else:
            material = sum(PIECE_VALUES[p.piece_type] for p in board.piece_map().values() if p.color == chess.BLACK)
        return material - PIECE_VALUES[chess.PAWN] > 0

    def _hash(self, board: chess.Board) -> int:
        for attr in ("zobrist_hash", "transposition_key", "_transposition_key"):
            method = getattr(board, attr, None)
            if callable(method):
                return method()
        return hash(board.fen())

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _evaluate(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -MATE_SCORE
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        material = self._material_balance(board)
        pst = self._piece_square(board)
        mobility = self._mobility(board) * self.mobility_weight
        king_safety_white, king_safety_black = self._king_safety(board)
        attack_white, attack_black = self._attack_pressure(board)
        pawn_structure = self._pawn_structure(board)
        rook_activity = self._rook_activity(board)
        bishop_pair = self._bishop_pair(board)
        center_control = self._center_control(board)
        threats = self._threat_map(board)
        tropism_white, tropism_black = self._king_tropism(board)
        sacrifice = self._sacrifice_bias_eval(
            board,
            material_white=self._material_total(board, chess.WHITE),
            material_black=self._material_total(board, chess.BLACK),
            attack_white=attack_white,
            attack_black=attack_black,
            king_white=king_safety_white,
            king_black=king_safety_black,
            threats=threats,
            center=center_control,
            tropism_white=tropism_white,
            tropism_black=tropism_black,
        )
        tempo = 12 if board.turn == chess.WHITE else -12

        score = (
            material
            + pst
            + mobility
            + (attack_white - attack_black) * self.attack_weight
            + (king_safety_white - king_safety_black) * self.king_safety_weight
            + center_control * self.center_weight
            + (tropism_white - tropism_black) * self.tropism_weight
            + threats * self.threat_weight
            + sacrifice
            + pawn_structure
            + rook_activity
            + bishop_pair
            + tempo
        )
        return score if board.turn == chess.WHITE else -score

    def _material_balance(self, board: chess.Board) -> int:
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += value * (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK)))
        return score

    def _material_total(self, board: chess.Board, color: chess.Color) -> int:
        total = 0
        for piece_type, value in PIECE_VALUES.items():
            total += value * len(board.pieces(piece_type, color))
        return total

    def _piece_square(self, board: chess.Board) -> int:
        score = 0
        for piece_type, table in PIECE_SQUARE_TABLES.items():
            for square in board.pieces(piece_type, chess.WHITE):
                score += table[square]
            for square in board.pieces(piece_type, chess.BLACK):
                score -= table[chess.square_mirror(square)]

        phase = self._phase(board)
        king_table = [
            int(phase * mid + (1 - phase) * end)
            for mid, end in zip(KING_MIDDLEGAME, KING_ENDGAME)
        ]
        for square in board.pieces(chess.KING, chess.WHITE):
            score += king_table[square]
        for square in board.pieces(chess.KING, chess.BLACK):
            score -= king_table[chess.square_mirror(square)]
        return score

    def _phase(self, board: chess.Board) -> float:
        phase_weights = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 1,
            chess.ROOK: 2,
            chess.QUEEN: 4,
            chess.KING: 0,
        }
        total = sum(phase_weights[p.piece_type] for p in board.piece_map().values())
        return min(1.0, total / 24.0)

    def _mobility(self, board: chess.Board) -> int:
        white_attacks = 0
        black_attacks = 0
        for square, piece in board.piece_map().items():
            attack_count = len(board.attacks(square))
            if piece.color == chess.WHITE:
                white_attacks += attack_count
            else:
                black_attacks += attack_count
        return white_attacks - black_attacks

    def _pawn_structure(self, board: chess.Board) -> int:
        score = 0
        white_files = [0] * 8
        black_files = [0] * 8
        for square in board.pieces(chess.PAWN, chess.WHITE):
            white_files[chess.square_file(square)] += 1
        for square in board.pieces(chess.PAWN, chess.BLACK):
            black_files[chess.square_file(square)] += 1

        def is_passed(square: int, color: chess.Color) -> bool:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            direction = 1 if color == chess.WHITE else -1
            enemy = chess.BLACK if color == chess.WHITE else chess.WHITE
            r = rank + direction
            while 0 <= r < 8:
                for df in (-1, 0, 1):
                    file_sq = file + df
                    if not 0 <= file_sq < 8:
                        continue
                    sq = chess.square(file_sq, r)
                    piece = board.piece_at(sq)
                    if piece and piece.color == enemy and piece.piece_type == chess.PAWN:
                        return False
                r += direction
            return True

        for square in board.pieces(chess.PAWN, chess.WHITE):
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            if white_files[file] > 1:
                score -= DOUBLED_PAWN_PENALTY
            neighbors = []
            if file > 0:
                neighbors.append(white_files[file - 1])
            if file < 7:
                neighbors.append(white_files[file + 1])
            if neighbors and all(count == 0 for count in neighbors):
                score -= ISOLATED_PAWN_PENALTY
            if is_passed(square, chess.WHITE):
                score += PASSED_PAWN_BONUS[rank]

        for square in board.pieces(chess.PAWN, chess.BLACK):
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            if black_files[file] > 1:
                score += DOUBLED_PAWN_PENALTY
            neighbors = []
            if file > 0:
                neighbors.append(black_files[file - 1])
            if file < 7:
                neighbors.append(black_files[file + 1])
            if neighbors and all(count == 0 for count in neighbors):
                score += ISOLATED_PAWN_PENALTY
            if is_passed(square, chess.BLACK):
                score -= PASSED_PAWN_BONUS[7 - rank]

        return score

    def _rook_activity(self, board: chess.Board) -> int:
        score = 0
        for color in (chess.WHITE, chess.BLACK):
            for square in board.pieces(chess.ROOK, color):
                file = chess.square_file(square)
                file_mask = chess.BB_FILES[file]
                friendly_pawns = board.pieces(chess.PAWN, color) & file_mask
                enemy_pawns = board.pieces(chess.PAWN, not color) & file_mask
                bonus = 0
                if not friendly_pawns and not enemy_pawns:
                    bonus = ROOK_OPEN_FILE_BONUS
                elif not friendly_pawns:
                    bonus = ROOK_SEMI_OPEN_FILE_BONUS
                score += bonus if color == chess.WHITE else -bonus
        return score

    def _bishop_pair(self, board: chess.Board) -> int:
        score = 0
        if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
            score += BISHOP_PAIR_BONUS
        if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
            score -= BISHOP_PAIR_BONUS
        return score

    def _center_control(self, board: chess.Board) -> int:
        score = 0
        for square in EXTENDED_CENTER:
            piece = board.piece_at(square)
            if piece is None:
                continue
            bonus = 12 if square in CENTER_SQUARES else 6
            if piece.color == chess.WHITE:
                score += bonus
            else:
                score -= bonus

        for square in CENTER_SQUARES:
            white_attackers = len(board.attackers(chess.WHITE, square))
            black_attackers = len(board.attackers(chess.BLACK, square))
            score += 4 * (white_attackers - black_attackers)
        return score

    def _king_tropism(self, board: chess.Board) -> Tuple[int, int]:
        def tropism(color: chess.Color) -> int:
            enemy_king = board.king(not color)
            if enemy_king is None:
                return 0
            enemy_file = chess.square_file(enemy_king)
            enemy_rank = chess.square_rank(enemy_king)
            pressure = 0
            for square in board.pieces(chess.PAWN, color):
                file_diff = abs(chess.square_file(square) - enemy_file)
                rank_diff = abs(chess.square_rank(square) - enemy_rank)
                if rank_diff < 3 and file_diff <= 1:
                    pressure += 2
            for square, piece in board.piece_map().items():
                if piece.color != color or piece.piece_type not in TROPISM_PIECES:
                    continue
                distance = abs(chess.square_file(square) - enemy_file) + abs(
                    chess.square_rank(square) - enemy_rank
                )
                pressure += max(0, TROPISM_PIECES[piece.piece_type] - 3 * distance)
            return pressure

        return tropism(chess.WHITE), tropism(chess.BLACK)

    def _threat_map(self, board: chess.Board) -> int:
        score = 0
        for square, piece in board.piece_map().items():
            enemy = not piece.color
            attackers = len(board.attackers(enemy, square))
            defenders = len(board.attackers(piece.color, square))
            value = PIECE_VALUES.get(piece.piece_type, 0)
            if attackers > defenders:
                swing = min(attackers - defenders, 2)
                penalty = (value * swing) // 4 + 6
                score += -penalty if piece.color == chess.WHITE else penalty

        for square in chess.SquareSet(board.occupied_co[chess.BLACK]):
            piece = board.piece_at(square)
            if piece is None:
                continue
            attackers = len(board.attackers(chess.WHITE, square))
            defenders = len(board.attackers(chess.BLACK, square))
            if attackers > defenders:
                gain = PIECE_VALUES.get(piece.piece_type, 0) // 6 + 8
                score += gain

        for square in chess.SquareSet(board.occupied_co[chess.WHITE]):
            piece = board.piece_at(square)
            if piece is None:
                continue
            attackers = len(board.attackers(chess.BLACK, square))
            defenders = len(board.attackers(chess.WHITE, square))
            if attackers > defenders:
                gain = PIECE_VALUES.get(piece.piece_type, 0) // 6 + 8
                score -= gain
        return score

    def _king_safety(self, board: chess.Board) -> Tuple[int, int]:
        def score(color: chess.Color) -> int:
            king_square = board.king(color)
            if king_square is None:
                return -MATE_THRESHOLD
            file = chess.square_file(king_square)
            rank = chess.square_rank(king_square)
            shelter = 0
            direction = 1 if color == chess.WHITE else -1
            for df in (-1, 0, 1):
                file_sq = file + df
                if not 0 <= file_sq < 8:
                    continue
                defended = False
                for step in range(1, 3):
                    rank_sq = rank + step * direction
                    if not 0 <= rank_sq < 8:
                        break
                    sq = chess.square(file_sq, rank_sq)
                    piece = board.piece_at(sq)
                    if piece and piece.color == color and piece.piece_type == chess.PAWN:
                        shelter += 12 // step
                        defended = True
                        break
                if not defended:
                    shelter -= 10

            attackers = len(board.attackers(not color, king_square))

            open_files = 0
            for df in (-1, 0, 1):
                file_sq = file + df
                if not 0 <= file_sq < 8:
                    continue
                clear = True
                file_range = range(rank + 1, 8) if color == chess.WHITE else range(0, rank)
                for r in file_range:
                    sq = chess.square(file_sq, r)
                    piece = board.piece_at(sq)
                    if piece:
                        clear = False
                        break
                if clear:
                    open_files += 1
            return shelter - 8 * attackers - 6 * open_files

        return score(chess.WHITE), score(chess.BLACK)

    def _attack_pressure(self, board: chess.Board) -> Tuple[int, int]:
        king_ring_offsets = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]

        def ring_squares(square: int) -> List[int]:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            result: List[int] = []
            for df, dr in king_ring_offsets:
                file_sq = file + df
                rank_sq = rank + dr
                if 0 <= file_sq < 8 and 0 <= rank_sq < 8:
                    result.append(chess.square(file_sq, rank_sq))
            return result

        def pressure(color: chess.Color) -> int:
            king_square = board.king(not color)
            if king_square is None:
                return 0
            attackers = 0
            heavy = 0
            opponent_squares = chess.SquareSet(board.occupied_co[not color])
            if color == chess.WHITE:
                forward_targets = chess.SquareSet(
                    chess.BB_RANK_4 | chess.BB_RANK_5 | chess.BB_RANK_6 | chess.BB_RANK_7
                )
            else:
                forward_targets = chess.SquareSet(
                    chess.BB_RANK_1 | chess.BB_RANK_2 | chess.BB_RANK_3 | chess.BB_RANK_4
                )
            for square, piece in board.piece_map().items():
                if piece.color != color:
                    continue
                attacks = chess.SquareSet(board.attacks(square))
                attack_count = len(attacks & opponent_squares)
                if piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP):
                    heavy += attack_count
                attackers += len(attacks & forward_targets)
            ring_control = sum(1 for sq in ring_squares(king_square) if board.is_attacked_by(color, sq))
            direct = len(board.attackers(color, king_square))
            return heavy * 4 + attackers * 2 + ring_control * 6 + direct * 8

        return pressure(chess.WHITE), pressure(chess.BLACK)

    def _sacrifice_bias_eval(
        self,
        board: chess.Board,
        *,
        material_white: int,
        material_black: int,
        attack_white: int,
        attack_black: int,
        king_white: int,
        king_black: int,
        threats: int,
        center: int,
        tropism_white: int,
        tropism_black: int,
    ) -> int:
        side = chess.WHITE if board.turn == chess.WHITE else chess.BLACK
        own_material = material_white if side == chess.WHITE else material_black
        opp_material = material_black if side == chess.WHITE else material_white
        material_deficit = own_material - opp_material

        if material_deficit >= 0:
            return 0

        attack_advantage = (attack_white - attack_black) if side == chess.WHITE else (attack_black - attack_white)
        king_pressure = (king_white - king_black) if side == chess.WHITE else (king_black - king_white)
        threat_balance = threats if side == chess.WHITE else -threats
        center_swing = center if side == chess.WHITE else -center
        tropism_delta = (tropism_white - tropism_black) if side == chess.WHITE else (tropism_black - tropism_white)

        combined = (
            0.6 * attack_advantage
            + 0.5 * king_pressure
            + 0.4 * threat_balance
            + 0.3 * tropism_delta
            + 0.2 * center_swing
        )

        guardrail = max(0, -material_deficit / 6)
        if combined <= guardrail:
            return material_deficit // 5

        bonus = self.sacrifice_bias * combined / 12 + tropism_delta * 0.4
        return int(bonus + material_deficit / 10)


__all__ = ["TalBotEngine"]
