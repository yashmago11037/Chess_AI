import chess

# NOTE: Weights here are NOT fully fine tuned - minimal testing
# These represent the traditonal centipawn values of the pieces in chess
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,  # Older models used to use 300 for both Knights/Bishops
    chess.BISHOP: 330,  # but 320/330 split between these is now the common approach
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,  # King does not have an associated centipawn value
}

# Pawn PST
pawn_table = [
    0,   0,   0,   0,   0,   0,   0,   0,
    5,  10,  10, -25, -25,  10,  10,   5,
    5,  -5, -10,   0,   0, -10,  -5,   5,
    0,   0,   0,  32,  35,   0,   0,   0,
    5,   5,  10,  27,  27,  10,   5,   5,
    10, 10,  20,  30,  30,  20,  10,  10,
    50, 50,  50,  50,  50,  50,  50,  50,
    0,   0,   0,   0,   0,   0,   0,   0
]

# Knight PST
knight_table = [
    -50, -35, -30, -30, -30, -30, -35, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
]

# Bishop PST
bishop_table = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
]

# Rook PST
rook_table = [
     0,   0,   0,   5,   5,   0,   0,   0,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     5,  10,  10,  10,  10,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0
]

# Queen PST
queen_table = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
      0,   0,   5,   5,   5,   5,   0,  -5,
     -5,   0,   5,   5,   5,   5,   0,  -5,
    -10,   0,   5,   5,   5,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
]

# King PST
king_table = [
     20,  30,  10,   0,   0,  10,  30,  20,
     20,  20,   0,   0,   0,   0,  20,  20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30
]

# Combine into one dict
piece_square_tables = {
    chess.PAWN: pawn_table,
    chess.KNIGHT: knight_table,
    chess.BISHOP: bishop_table,
    chess.ROOK: rook_table,
    chess.QUEEN: queen_table,
    chess.KING: king_table
}


def evaluate_material(board: chess.Board) -> int:
    """
    Fast, robust material evaluation that works across python-chess versions.
    Uses SquareSet.count() when available; falls back to int(...).bit_count().
    """
    score = 0
    for piece_type, value in piece_values.items():
        # White count
        try:
            w_count = board.pieces(piece_type, chess.WHITE).count()
        except Exception:
            # older/newer variations might need casting to int
            w_count = int(board.pieces(piece_type, chess.WHITE)).bit_count()

        # Black count
        try:
            b_count = board.pieces(piece_type, chess.BLACK).count()
        except Exception:
            b_count = int(board.pieces(piece_type, chess.BLACK)).bit_count()

        score += value * (w_count - b_count)

    return score


def evaluate_piece_square_tables(board: chess.Board) -> int:
    score = 0

    # piece_map() gives: {square: Piece}
    for square, piece in board.piece_map().items():
        pst = piece_square_tables[piece.piece_type]

        if piece.color == chess.WHITE:
            score += pst[square]
        else:
            score -= pst[chess.square_mirror(square)]

    return score


def evaluate_pawn_structure(board: chess.Board) -> int:
    score = 0

    # Fast bitboard getters
    white_pawns = int(board.pieces(chess.PAWN, chess.WHITE))
    black_pawns = int(board.pieces(chess.PAWN, chess.BLACK))

    # File masks (1 bit in each square of a file)
    FILE_MASKS = [int(chess.BB_FILES[i]) for i in range(8)]

    # --- Doubled and isolated pawns ---
    for color, pawns, sign in [
        (chess.WHITE, white_pawns, +1),
        (chess.BLACK, black_pawns, -1),
    ]:
        for file_i in range(8):
            file_mask = FILE_MASKS[file_i]
            pawns_on_file = pawns & file_mask

            if pawns_on_file == 0:
                continue

            count = pawns_on_file.bit_count()

            # Doubled pawns
            if count > 1:
                score += sign * (count - 1) * (-20)

            # Isolated pawns
            left = FILE_MASKS[file_i - 1] if file_i > 0 else 0
            right = FILE_MASKS[file_i + 1] if file_i < 7 else 0
            neighbors = pawns & (left | right)

            if neighbors == 0:
                score += sign * (-15)

    # --- Passed pawns ---
    # Precomputed masks for passed pawn checks:
    for color, pawns, sign, forward_shift, enemy_pawns in [
        (chess.WHITE, white_pawns, +1, 8, black_pawns),
        (chess.BLACK, black_pawns, -1, -8, white_pawns),
    ]:

        temp = pawns
        while temp:
            sq = (temp & -temp).bit_length() - 1  # index of LSB
            temp &= temp - 1

            file = sq % 8

            # Pawns in same file or adjacent files in front of this pawn (enemy)
            mask = 0

            # Build mask manually — cost is tiny (runs once per pawn)
            for f in (file - 1, file, file + 1):
                if 0 <= f < 8:
                    for rank in range(8):
                        target_sq = rank * 8 + f
                        if (color == chess.WHITE and target_sq > sq) or \
                           (color == chess.BLACK and target_sq < sq):
                            mask |= 1 << target_sq

            if enemy_pawns & mask == 0:
                score += sign * 30  # passed pawn bonus

    return score

def evaluate_bishop_pair(board: chess.Board) -> int:
    score = 0

    # White bishop count
    w_bishops = int(board.pieces(chess.BISHOP, chess.WHITE)).bit_count()
    if w_bishops >= 2:
        score += 50

    # Black bishop count
    b_bishops = int(board.pieces(chess.BISHOP, chess.BLACK)).bit_count()
    if b_bishops >= 2:
        score -= 50

    return score

def evaluate_rook_files(board: chess.Board) -> int:
    score = 0

    # Precompute pawn bitboards
    white_pawns = int(board.pieces(chess.PAWN, chess.WHITE))
    black_pawns = int(board.pieces(chess.PAWN, chess.BLACK))

    # File bit masks (BB_FILES is already prepared by python-chess)
    FILE_MASKS = [int(chess.BB_FILES[f]) for f in range(8)]

    for color in [chess.WHITE, chess.BLACK]:
        # Rooks for this side as bitboard
        rooks = int(board.pieces(chess.ROOK, color))

        # Pawn bitboards for logic
        friendly_pawns = white_pawns if color == chess.WHITE else black_pawns
        enemy_pawns = black_pawns if color == chess.WHITE else white_pawns

        temp = rooks
        while temp:
            r_sq = (temp & -temp).bit_length() - 1  # pop LSB
            temp &= temp - 1

            f = r_sq % 8
            file_mask = FILE_MASKS[f]

            friendly_count = (friendly_pawns & file_mask).bit_count()
            enemy_count = (enemy_pawns & file_mask).bit_count()

            # Open file: no pawns at all
            if friendly_count == 0 and enemy_count == 0:
                score += 25 if color == chess.WHITE else -25

            # Half-open: no friendly pawns, at least one enemy pawn
            elif friendly_count == 0 and enemy_count > 0:
                score += 15 if color == chess.WHITE else -15

    return score

def evaluate_knight_outposts(board: chess.Board) -> int:
    score = 0

    for color in [chess.WHITE, chess.BLACK]:
        knights = board.pieces(chess.KNIGHT, color)
        enemy_pawns = board.pieces(chess.PAWN, not color)
        friendly_pawns = board.pieces(chess.PAWN, color)

        for n_sq in knights:
            f = chess.square_file(n_sq)
            r = chess.square_rank(n_sq)

            # 1. Knight must be in enemy territory
            if color == chess.WHITE and r < 4:
                continue
            if color == chess.BLACK and r > 3:
                continue

            # 2. Knight must NOT be attacked by enemy pawn
            attacked = False
            direction = 1 if color == chess.WHITE else -1
            target_rank = r - direction  # enemy pawn must be on this rank

            for ep in enemy_pawns:
                if chess.square_rank(ep) == target_rank:
                    if abs(chess.square_file(ep) - f) == 1:
                        attacked = True
                        break

            if attacked:
                continue

            # 3. Knight must be SUPPORTED by a friendly pawn
            supported = False
            support_rank = r + direction  # friendly pawn must be here

            for fp in friendly_pawns:
                if chess.square_rank(fp) == support_rank:
                    if abs(chess.square_file(fp) - f) == 1:
                        supported = True
                        break

            if not supported:
                continue

            # 4. Award bonus
            score += 20 if color == chess.WHITE else -20

    return score

# Are we in the opening, middlegame, or endgame?

def game_phase(board: chess.Board) -> float:
    # Returns a phase factor between 0 and 1 based on remaining non-pawn material.
    # 1.0 = opening, 0.0 = endgame.

    # Non-pawn pieces considered: Knight, Bishop, Rook, Queen
    max_phase_material = 2 * 320 + 2 * 330 + 2 * 500 + 2 * 900  # total for all non-pawn pieces
    current_material = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        current_material += piece_values[piece_type] * (
                    len(board.pieces(piece_type, chess.WHITE)) + len(board.pieces(piece_type, chess.BLACK)))

    phase = current_material / max_phase_material
    return max(0.0, min(1.0, phase))  # Range between (0,1)


# Likely needed for minimax
# def phase(board: chess.Board) -> float:
#    return game_phase(board)


def evaluate_king(board: chess.Board) -> int:
    game_phase_value = game_phase(board)  # 1.0 = opening, 0.0 = endgame
    total_score = 0

    for color in [chess.WHITE, chess.BLACK]:

        # -------------------------
        # Extract king position
        # -------------------------
        king_square = next(iter(board.pieces(chess.KING, color)))
        king_file = chess.square_file(king_square)
        king_rank = chess.square_rank(king_square)

        # -------------------------
        # Middle Game King Safety
        # -------------------------
        king_safety_score = 0

        # King’s home rank (white = 0, black = 7)
        home_rank = 0 if color == chess.WHITE else 7

        # We only count pawn shields when the king is near home
        king_is_near_home = (
            king_rank == home_rank or
            (color == chess.WHITE and king_rank == 1) or
            (color == chess.BLACK and king_rank == 6)
        )

        if king_is_near_home:
            pawn_forward_direction = 1 if color == chess.WHITE else -1

            # Check the three squares directly in front of the king
            for file_offset in [-1, 0, 1]:
                pawn_file = king_file + file_offset
                pawn_rank = king_rank + pawn_forward_direction

                # on board?
                if 0 <= pawn_file <= 7 and 0 <= pawn_rank <= 7:
                    shield_square = chess.square(pawn_file, pawn_rank)
                    piece = board.piece_at(shield_square)

                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        king_safety_score += 12  # pawn shield bonus

        # -------------------------
        # Enemy Proximity Penalty
        # -------------------------
        # Only applied in the middlegame (when king should be safe)
        if game_phase_value > 0.35:
            for square, piece in board.piece_map().items():
                if piece.color != color:
                    enemy_file = chess.square_file(square)
                    enemy_rank = chess.square_rank(square)

                    manhattan_distance = abs(king_file - enemy_file) + abs(king_rank - enemy_rank)

                    if manhattan_distance <= 2:
                        king_safety_score -= 3  # small danger penalty

        # -------------------------
        # Endgame: King Activity
        # -------------------------
        # Distance from center (3.5,3.5)
        center_distance = abs(king_file - 3.5) + abs(king_rank - 3.5)
        king_activity_score = -center_distance * 8  # closer to center = better

        # -------------------------
        # Blend based on game phase
        # -------------------------
        king_total = (
            game_phase_value * king_safety_score +
            (1 - game_phase_value) * king_activity_score
        )

        # Add from correct perspective
        if color == chess.WHITE:
            total_score += king_total
        else:
            total_score -= king_total

    return total_score


def evaluate_mobility(board: chess.Board) -> int:
    # ----------------------------
    # Precompute static sets once
    # ----------------------------
    CENTRAL_SQUARES = frozenset((
        chess.C3, chess.D3, chess.E3, chess.F3,
        chess.C4, chess.D4, chess.E4, chess.F4,
        chess.C5, chess.D5, chess.E5, chess.F5,
        chess.C6, chess.D6, chess.E6, chess.F6
    ))

    MAIN_CENTER = frozenset((chess.E4, chess.D4, chess.E5, chess.D5))

    # ----------------------------
    # Precompute once per call
    # ----------------------------
    opening_phase = 1.0 if board.fullmove_number <= 6 else 0.0
    pieces = board.piece_map()
    moves = list(board.legal_moves)

    # Localize variables for speed
    central_squares = CENTRAL_SQUARES
    main_center = MAIN_CENTER
    op_phase = opening_phase

    white_score = 0
    black_score = 0

    # ----------------------------
    # Fast local references
    # ----------------------------
    PAWN = chess.PAWN
    KNIGHT = chess.KNIGHT
    BISHOP = chess.BISHOP
    ROOK = chess.ROOK
    QUEEN = chess.QUEEN
    KING = chess.KING
    WHITE = chess.WHITE

    for mv in moves:
        frm = mv.from_square
        piece = pieces.get(frm)
        if piece is None:
            continue

        ptype = piece.piece_type
        color_is_white = piece.color  # bool

        to_sq = mv.to_square

        # -------------
        # Piece scoring
        # -------------
        if ptype == PAWN:
            pts = 5
            if to_sq in main_center:
                pts += 25 * op_phase
            if to_sq in central_squares:
                pts += 10

        elif ptype == KNIGHT:
            pts = 4 - 6 * op_phase

        elif ptype == BISHOP:
            pts = 6

        elif ptype == ROOK:
            pts = 4 + (2 if op_phase == 0 else 0)

        elif ptype == QUEEN:
            pts = 2 + (6 if op_phase == 0 else 0)

        elif ptype == KING:
            pts = 1

        else:
            continue

        # -------------
        # Accumulate
        # -------------
        if color_is_white:
            white_score += pts
        else:
            black_score += pts

    return white_score - black_score

def evaluate_center_control(board: chess.Board) -> int:
    score = 0

    # Modern 16-square center
    center_squares = {
        chess.C3, chess.D3, chess.E3, chess.F3,
        chess.C4, chess.D4, chess.E4, chess.F4,
        chess.C5, chess.D5, chess.E5, chess.F5,
        chess.C6, chess.D6, chess.E6, chess.F6,
    }

    # Weight settings (centipawns)
    occupation_values = {
        chess.PAWN: 30,
        chess.KNIGHT: 20,
        chess.BISHOP: 20,
        chess.ROOK: 10,
        chess.QUEEN: 10,
        chess.KING: 0
    }

    control_values = {
        chess.PAWN: 15,
        chess.KNIGHT: 12,
        chess.BISHOP: 10,
        chess.ROOK: 6,
        chess.QUEEN: 4,
        chess.KING: 0
    }

    for sq in center_squares:
        # 1. Occupation bonus
        piece = board.piece_at(sq)
        if piece:
            value = occupation_values.get(piece.piece_type, 0)
            score += value if piece.color == chess.WHITE else -value

        # 2. Control bonus
        attackers_white = board.attackers(chess.WHITE, sq)
        attackers_black = board.attackers(chess.BLACK, sq)

        for attacker in attackers_white:
            p = board.piece_at(attacker)
            score += control_values.get(p.piece_type, 0)

        for attacker in attackers_black:
            p = board.piece_at(attacker)
            score -= control_values.get(p.piece_type, 0)

    return score



# Final calculation function, summation of each score * weight
def evaluate(board: chess.Board) -> int:
    # Game Phase
    phase_value = game_phase(board)

    # weights (not tested, used off of personal experience and intuition)
    w_material = 1.0
    w_pst = (0.3 + 0.7 * phase_value)
    w_pawn_structure = 0.4
    w_bishop_pair = 0.2
    w_knight_outposts = 0.3
    w_rook_files = 0.2
    w_king_safety = 0.6
    w_mobility = 0.3
    w_center = 0.38

    score = 0
    score += w_material * evaluate_material(board)  # material is static
    score += w_pst * evaluate_piece_square_tables(board)  # scale by phase
    score += w_pawn_structure * evaluate_pawn_structure(board)  # static enough
    score += w_bishop_pair * evaluate_bishop_pair(board)  # usually static
  # score += w_knight_outposts * evaluate_knight_outposts(board) - REMOVED, low elo gains and adds time complexity (can uncomment out later maybe)
    score += w_rook_files * evaluate_rook_files(board)  # static enough
    score += w_king_safety * evaluate_king(board)  # king safety changes entirely in endgame
    score += w_mobility * evaluate_mobility(board)  # mobility matters more in middlegame
    score += w_center * evaluate_center_control(board)  # At start, focus on moving pawns to the middle

    # Small tempo bonus
    if board.turn == chess.WHITE:
        score += 10
    else:
        score -= 10

    return int(score)

