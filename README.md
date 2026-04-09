# Comp115_PRO-2
Archer Training game
# 🏹 Archer Training

A 2D arcade game built with Python and Pygame. Choose your archer, shoot down training dummies, and survive the full 60 seconds before you get overrun.

---

## Gameplay

- Training dummies march across the screen from both sides — shoot them before they reach you
- Missing a dummy costs you a heart; lose all five and it's game over
- Difficulty ramps up over time: dummies spawn faster and move quicker the longer you survive
- Beat the clock to post your final score

---

## Controls

| Key | Action |
|-----|--------|
| `A` / `D` | Move left / right |
| `W` | Jump |
| `Space` | Shoot |
| `←` / `→` | Cycle archer on the menu |
| `Enter` | Start game |
| `R` | Restart after game over |
| `Esc` | Quit |

---

## Getting Started

### Requirements

- Python 3.10+
- pygame-ce

```bash
pip install pygame-ce
```

### Running the game

```bash
python game.py
```

---

## Project Structure

```
project/
├── game.py
├── README.md
├── pro2/
│   ├── BG.jpg
│   ├── Arrow/
│   │   └── arrow.png
│   ├── TrainingDummy/
│   │   └── NoArmor/
│   │       ├── Idle/
│   │       └── Hited/
│   ├── all_colored_archers/
│   │   ├── blue/
│   │   │   ├── idle/
│   │   │   ├── run/
│   │   │   └── shooting/
│   │   └── ... (one folder per archer colour)
│   └── sound/
│       ├── bow.mp3
│       ├── arrow impact.mp3
│       ├── hit.mp3
│       └── BG music.mp3
```

Each archer folder under `all_colored_archers/` must contain three subfolders — `idle`, `run`, and `shooting` — with frames named `0.png`, `1.png`, `2.png`, etc.

---

## Built With

- [Python](https://www.python.org/)
- [pygame-ce](https://pyga.me/) — community edition fork of Pygame
