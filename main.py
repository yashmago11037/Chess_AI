# main.py
import pygame
import chess
import chess.engine
import csv
from pathlib import Path
import time
from minimax_bot import MinimaxBot
from evaluate import evaluate

TILE = 50
WIDTH = HEIGHT = TILE * 8

WHITE_RGB = (255, 255, 255)
BLACK_RGB = (0, 0, 0)
LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
HILITE_RGBA = (255, 255, 0, 90)

FONT_NAME = "segoeuisymbol"
FONT_SIZE = 36

# Stockfish: set this to your local Stockfish binary path to enable Stockfish play.
# Download from: https://stockfishchess.org/download/
# Leave as None to disable (Minimax will be used as fallback).
# Examples:
#   Windows: r"C:\path\to\stockfish.exe"
#   macOS:   "/usr/local/bin/stockfish"
#   Linux:   "/usr/games/stockfish"
STOCKFISH_PATH = None  # <-- Set your path here
STOCKFISH_LIMIT = chess.engine.Limit(time=0.1)  # or depth=12, nodes=...

# How long to display result screen (ms)
RESULT_DISPLAY_MS = 2500


def get_square_from_xy(x: int, y: int) -> chess.Square:
    """Convert screen (x,y) to chess.Square (0..63), with rank 7 at top row."""
    file_ = x // TILE
    rank_ = 7 - (y // TILE)
    return chess.square(file_, rank_)


class ChessGame:
    """
    Side strings:
      - "human": clicks
      - "minimax": our Python Minimax
      - "stockfish": external engine (if STOCKFISH_PATH is set)
    """
    def __init__(self, white_player="human", black_player="minimax", minimax_depth=5, flip_board=False):
        self.white_player = white_player
        self.black_player = black_player

        self.board = chess.Board()
        self.minimax = MinimaxBot(depth=minimax_depth, eval_fn=evaluate)
        self.flip_board = flip_board
        self.screen = None
        self.font = None
        self.running = True

        self.has_selected = False
        self.current_sqr = None
        self.highlighted_sqrs = []

        self.highlight_layer = None

        self.engine = None
        if self.white_player == "stockfish" or self.black_player == "stockfish":
            if STOCKFISH_PATH:
                try:
                    self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
                except Exception as e:
                    print(f"[WARN] Could not start Stockfish: {e}")
                    self.engine = None
            else:
                print("[INFO] STOCKFISH_PATH not set; Stockfish disabled for this run.")

        if self.engine:
            try:
                # example: set strength to ~1500 Elo
                self.engine.configure({"UCI_LimitStrength": True, "UCI_Elo": 1800})
            except Exception as e:
                print(f"[WARN] Could not configure Stockfish options: {e}")

    def draw_board(self):
        for r in range(8):
            for f in range(8):
                # flip rank index for color so a1 is dark
                color = DARK_SQ if (r + f) % 2 == 0 else LIGHT_SQ
                pygame.draw.rect(
                    self.screen,
                    color,
                    pygame.Rect(f * TILE, (7 - r) * TILE, TILE, TILE),
                )

    def draw_pieces_from_board(self):
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            color = WHITE_RGB if piece.color == chess.WHITE else BLACK_RGB
            r = chess.square_rank(sq)
            f = chess.square_file(sq)
            glyph = piece.unicode_symbol()
            text_surface = self.font.render(glyph, True, color)
            cx = TILE // 2 + TILE * f
            cy = TILE // 2 + TILE * (7 - r)
            rect = text_surface.get_rect(center=(cx, cy))
            self.screen.blit(text_surface, rect)

    def draw_highlights(self):
        self.highlight_layer.fill((0, 0, 0, 0))
        for sq in self.highlighted_sqrs:
            r = chess.square_rank(sq)
            f = chess.square_file(sq)
            pygame.draw.rect(
                self.highlight_layer,
                HILITE_RGBA,
                pygame.Rect(f * TILE, (7 - r) * TILE, TILE, TILE),
            )
        self.screen.blit(self.highlight_layer, (0, 0))

    def get_result_text(self) -> str:
        if self.board.is_checkmate():
            # side-to-move is checkmated
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"Checkmate — {winner} wins"
        # other draw types
        if self.board.is_stalemate():
            return "Draw — stalemate"
        outcome = self.board.outcome()
        if outcome and outcome.termination:
            if outcome.winner is None:
                return "Draw"
            return f"{'White' if outcome.winner else 'Black'} wins"
        return "Game over"

    def show_center_banner(self, text: str):
        """Render a centered banner text."""
        label = pygame.font.SysFont("arial", 28, bold=True).render(text, True, (30, 30, 30))
        rect = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        # semi-transparent backdrop
        backdrop = pygame.Surface((rect.width + 20, rect.height + 12), pygame.SRCALPHA)
        backdrop.fill((255, 255, 255, 210))
        brect = backdrop.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(backdrop, brect)
        self.screen.blit(label, rect)

    def choose_promotion(self, to_square: chess.Square, allowed_types: list[int]) -> int | None:
        """
        Modal mini-UI to choose promotion piece for the human.
        allowed_types is a list of piece types among {QUEEN, ROOK, BISHOP, KNIGHT}
        that are actually legal for the selected from→to.
        Returns the chosen piece type or None if canceled.
        """
        # Build dynamic choices from what's actually legal
        label_for = {
            chess.QUEEN:  "Q",
            chess.ROOK:   "R",
            chess.BISHOP: "B",
            chess.KNIGHT: "N",
        }
        priority = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        choices = [(pt, label_for[pt]) for pt in priority if pt in allowed_types]
        if not choices:
            return None

        f = chess.square_file(to_square)
        r = chess.square_rank(to_square)
        px = f * TILE
        py = (7 - r) * TILE
        item_w, item_h = 44, 44
        pad = 6
        popup_w = pad + len(choices) * (item_w + pad)
        popup_h = item_h + pad * 2

        popup_x = min(max(px - popup_w // 2 + TILE // 2, 4), WIDTH - popup_w - 4)
        popup_y = min(max(py - popup_h - 8, 4), HEIGHT - popup_h - 4)

        rects = []
        x = popup_x + pad
        for _ptype, _label in choices:
            rects.append(pygame.Rect(x, popup_y + pad, item_w, item_h))
            x += item_w + pad

        # Modal loop
        while True:
            # draw current board/background
            self.draw_board()
            self.draw_pieces_from_board()
            self.draw_highlights()

            # popup bg
            popup = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
            popup.fill((40, 40, 40, 220))
            self.screen.blit(popup, (popup_x, popup_y))

            # draw items
            font = pygame.font.SysFont("arial", 22, bold=True)
            for idx, (ptype, label) in enumerate(choices):
                rct = rects[idx]
                pygame.draw.rect(self.screen, (220, 220, 220), rct, border_radius=6)
                glyph = font.render(label, True, (20, 20, 20))
                self.screen.blit(glyph, glyph.get_rect(center=rct.center))

            pygame.display.flip()

            # handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return None
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return None  # cancel
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    for idx, rct in enumerate(rects):
                        if rct.collidepoint(mx, my):
                            return choices[idx][0]  # piece type
                    # click outside popup cancels
                    if not pygame.Rect(popup_x, popup_y, popup_w, popup_h).collidepoint(mx, my):
                        return None

    # ---------- interaction ----------
    def handle_human_click(self, event) -> bool:
        """Process a click; return True iff a legal move was pushed."""
        if event.type != pygame.MOUSEBUTTONDOWN:
            return False
        x, y = event.pos
        target_sqr = get_square_from_xy(x, y)

        if not self.has_selected:
            piece = self.board.piece_at(target_sqr)
            # only select your own piece
            if piece and piece.color == self.board.turn:
                self.current_sqr = target_sqr
                # legal targets from that square
                self.highlighted_sqrs = [m.to_square for m in self.board.legal_moves
                                         if m.from_square == target_sqr]
                self.has_selected = True
            else:
                self.current_sqr = None
                self.highlighted_sqrs = []
            return False

        # ---- Second click: attempt a move ----
        from_sq = self.current_sqr
        to_sq = target_sqr

        # Quick deselect: clicking the same square toggles off
        if to_sq == from_sq:
            self.has_selected = False
            self.current_sqr = None
            self.highlighted_sqrs = []
            return False

        legal_moves = list(self.board.legal_moves)

        # All legal promotions for exactly this from→to
        promotion_moves = [
            m for m in legal_moves
            if m.from_square == from_sq and m.to_square == to_sq and m.promotion
        ]

        move_to_push = None

        if promotion_moves:
            # Restrict UI to actually legal promotion piece types
            allowed_types = sorted({m.promotion for m in promotion_moves})
            chosen = self.choose_promotion(to_sq, allowed_types)
            if chosen is None:
                # canceled; keep selection so user can re-try
                return False

            candidate = chess.Move(from_sq, to_sq, promotion=chosen)
            if candidate in legal_moves:
                move_to_push = candidate
            else:
                move_to_push = promotion_moves[0]
        else:
            # Non-promotion path
            candidate = chess.Move(from_sq, to_sq)
            if candidate in legal_moves:
                move_to_push = candidate

        made_move = False
        if move_to_push is not None:
            self.board.push(move_to_push)
            made_move = True

        # reset selection
        self.has_selected = False
        self.current_sqr = None
        self.highlighted_sqrs = []
        return made_move

    # ---------- AI turns ----------
    def play_minimax_turn(self):
        mv = self.minimax.play(self.board)
        if mv:
            self.board.push(mv)

    def play_stockfish_turn(self):
        if not self.engine:
            self.play_minimax_turn()
            return
        try:
            result = self.engine.play(self.board, STOCKFISH_LIMIT)
            if result and result.move:
                self.board.push(result.move)
        except Exception as e:
            print(f"[WARN] Stockfish error: {e}")
            # graceful fallback
            #self.play_minimax_turn()

    # ---------- main loop ----------
    # In ChessGame
    def play(self, render: bool | None = None, block_on_gameover: bool | None = None):
        # Auto settings: show UI if a human is involved; block at end iff we are rendering
        if render is None:
            render = (self.white_player == "human" or self.black_player == "human")
        if block_on_gameover is None:
            block_on_gameover = render

        if render:
            pygame.init()
            pygame.display.set_caption("Chess — Human / Minimax / Stockfish")
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
            self.highlight_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            clock = pygame.time.Clock()
        else:
            clock = None  # headless

        # --- main loop unchanged, but guard all drawing/event code with `if render:` ---

        while self.running and not self.board.is_game_over():
            moved_this_frame = False

            if render:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    else:
                        if self.board.turn == chess.WHITE and self.white_player == "human":
                            moved_this_frame |= self.handle_human_click(event)
                        elif self.board.turn == chess.BLACK and self.black_player == "human":
                            moved_this_frame |= self.handle_human_click(event)

                self.draw_board()
                self.draw_pieces_from_board()
                self.draw_highlights()
                pygame.display.flip()

                if moved_this_frame:
                    clock.tick(60)
                    continue

            # AI turn(s)
            if self.running:
                if self.board.turn == chess.WHITE and self.white_player != "human":
                    if self.white_player == "minimax":
                        self.play_minimax_turn()
                    elif self.white_player == "stockfish":
                        self.play_stockfish_turn()
                elif self.board.turn == chess.BLACK and self.black_player != "human":
                    if self.black_player == "minimax":
                        self.play_minimax_turn()
                    elif self.black_player == "stockfish":
                        self.play_stockfish_turn()

            if render:
                self.draw_board()
                self.draw_pieces_from_board()
                self.draw_highlights()
                pygame.display.flip()
                clock.tick(60)

        # ----- Game over -----
        # Decide winner/label once
        outcome = self.board.outcome()
        if outcome and outcome.winner is not None:
            winner = "white" if outcome.winner else "black"
        elif self.board.is_checkmate():
            winner = "black" if self.board.turn == chess.WHITE else "white"
        else:
            winner = "draw"

        # Print to terminal every game
        print(f"[RESULT] Winner: {winner}  (white={self.white_player}, black={self.black_player})")

        # Show banner only when rendering
        if self.running and render:
            self.draw_board()
            self.draw_pieces_from_board()
            self.draw_highlights()
            self.show_center_banner(self.get_result_text())
            pygame.display.flip()

        # Append to CSV (same as you had)
        results_path = Path("results_log.csv")
        write_header = not results_path.exists()
        with results_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["game_id", "winner", "white_player", "black_player"])
            existing_lines = sum(1 for _ in open(results_path, "r", encoding="utf-8")) - (1 if write_header else 0)
            writer.writerow([existing_lines + 1, winner, self.white_player, self.black_player])

        # Keep window open at end only when interactive
        if block_on_gameover and render:
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        waiting = False
                pygame.time.Clock().tick(30)

        # Cleanup
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass
        if render:
            pygame.quit()


def run_batch(num_games=10):
    for i in range(1, num_games + 1):
        print(f"\n=== Starting game {i} ===")

        game = ChessGame(
            white_player="human",
            black_player="minimax",
            minimax_depth=5,
            flip_board=False,  # or True; see part 2
        )

        start_time = time.time()
        is_last = (i == num_games)
        game.play(render=True, block_on_gameover=is_last)
        end_time = time.time()

        print(f"Game {i} finished in {end_time - start_time:.2f}s\n")

        # For non-last games we close the window immediately; for last,
        # play() already blocks until user closes, so this is harmless.
        if game.engine:
            try: game.engine.quit()
            except Exception: pass

        pygame.quit()
        if not is_last:
            time.sleep(1)




def main():
    # Configure players: "human", "minimax", or "stockfish"
    # Adjust minimax_depth to control bot strength (higher = stronger but slower)
    game = ChessGame(white_player="human", black_player="minimax", minimax_depth=5)
    game.play()

    # To run automated bot-vs-bot games, use run_batch() instead:
    # run_batch(num_games=10)

if __name__ == "__main__":
    main()
