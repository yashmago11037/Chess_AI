# Chess AI

A Python chess engine featuring a Minimax bot with advanced search optimizations, a custom evaluation function, and a pygame GUI. Estimated playing strength: **~2100 ELO**.

---

## Features

### Search (minimax_bot.py)
- **Minimax with Alpha-Beta Pruning** — standard negamax-style tree search
- **Iterative Deepening** — searches depth 1→N, using shallower results to guide move ordering
- **Transposition Table** — Zobrist hashing with exact/upper/lower bound entries (200k entry cap)
- **Null Move Pruning** — skips a turn at depth ≥ 3 to detect and prune bad branches early
- **Quiescence Search** — extends search on captures/promotions to avoid horizon-effect blunders
- **Static Exchange Evaluation (SEE)** — prunes losing captures in quiescence search using LVA recapture simulation
- **Move Ordering** — MVV-LVA for captures, TT best move first, PV move priority, check detection

### Evaluation (evaluate.py)
- Material balance (centipawn values)
- Piece-square tables (PSTs) for all 6 piece types, weighted by game phase
- Pawn structure: doubled, isolated, and passed pawn detection
- Bishop pair bonus
- Rook on open/half-open file bonuses
- Knight outpost detection
- King safety (pawn shield, enemy proximity) blended with endgame king activity
- Mobility scoring with center-weighted bonuses
- Center control (occupation + attack bonuses on 16-square extended center)
- Game phase interpolation (opening → endgame)

### GUI (main.py)
- Pygame-based board rendering with unicode piece glyphs
- Click-to-move with legal move highlighting
- Promotion picker (modal UI)
- Supports **Human**, **Minimax**, and **Stockfish** on either side
- Game result banner + CSV logging (`results_log.csv`)
- Batch game runner for automated testing

---

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/<your-username>/Chess_AI.git
cd Chess_AI
pip install -r requirements.txt
```

---

## Usage

### Play against the bot (Human vs Minimax)
Edit the bottom of `main.py`:
```python
def main():
    game = ChessGame(white_player="human", black_player="minimax", minimax_depth=5)
    game.play()
```
Then run:
```bash
python main.py
```

### Bot vs Bot
```python
game = ChessGame(white_player="minimax", black_player="stockfish", minimax_depth=4)
game.play()
```

### Stockfish Setup (optional)
Download Stockfish from [stockfishchess.org](https://stockfishchess.org/download/) and set the path in `main.py`:
```python
STOCKFISH_PATH = r"path/to/your/stockfish"
```

---

## Project Structure

```
Chess_AI/
├── main.py           # GUI, game loop, Stockfish integration, batch runner
├── minimax_bot.py    # Minimax engine with all search optimizations
├── evaluate.py       # Static board evaluation function
├── requirements.txt
└── README.md
```

---

## Configuration

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `minimax_depth` | `ChessGame(...)` | `5` | Search depth (higher = stronger, slower) |
| `STOCKFISH_PATH` | `main.py` | `None` | Path to Stockfish binary |
| `STOCKFISH_LIMIT` | `main.py` | `time=0.1s` | Stockfish time/depth limit per move |
| `use_null_move_pruning` | `MinimaxBot(...)` | `True` | Enable null-move pruning |

---

## Notes

- Weights in `evaluate.py` are based on intuition and conventional chess engine values — not formally tuned via SPSA or similar methods. Contributions welcome.
- The `evaluate_knight_outposts` function is implemented but currently disabled in the final evaluation (low ELO gain relative to compute cost).
- ELO estimate of ~2100 is based on informal testing; formal benchmarking against known-strength engines has not been performed.
