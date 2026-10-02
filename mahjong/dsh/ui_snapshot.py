# -*- coding: utf-8 -*-
"""dsh/ui_snapshot.py —— 无头渲染 UI_test_back.py 的几个画面存成 PNG，用来肉眼检查排版

用法: python dsh/ui_snapshot.py      (输出到 dsh/shots/*.png)
"""
import collections
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
import tile  # noqa: E402

SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)

SRC = (ROOT / "UI_test_back.py").read_text(encoding="utf-8")
ui = types.SimpleNamespace()
exec(compile(SRC, "UI_test_back.py", "exec"), ui.__dict__)


def mk(cards):
    return [tile.Card(s, r) for s, r in cards]


def save(name):
    ui.draw()
    path = SHOTS / name
    pygame.image.save(ui.screen, str(path))
    print("saved", path)


# ---------- 1. 开始界面（真的是"刚启动"的状态：还没有牌桌） ----------
ui.Player_List = []
ui.deck = []
ui.discard_rows = [[], [], [], []]
ui.Vic_rank = []
ui.GAME_STATE = ui.STATE_BEGIN
ui.current = 0
ui.messages = collections.deque(maxlen=5)
ui.banner_text = ""
save("1_begin.png")

# ---------- 2. 我的回合（有副露/弃牌/听牌提示/按钮） ----------
hand = mk([(1, 1)] * 3 + [(1, 2)] * 2 + [(3, 6)] * 3 + [(3, 7)] * 3 + [(3, 8)] * 3)   # 14张,碰碰胡
ui.Player_List = [
    tile.Player(hand, [mk([(2, 3)] * 3), mk([(1, 9)] * 4)], False, False),
    tile.Player(mk([(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 3 + [(3, 2)] * 2),
                [mk([(1, 5)] * 3)], False, False),
    tile.Player(mk([(2, 2)] * 4 + [(2, 5)] * 4 + [(2, 8)] * 3 + [(3, 4)] * 2),
                [mk([(3, 1)] * 3), mk([(3, 9)] * 4)], False, False),
    tile.Player(mk([(2, 6)] * 4 + [(2, 9)] * 4 + [(3, 1)] * 3 + [(3, 9)] * 2),
                [mk([(2, 7)] * 4)], True, False),
]
ui.deck = [tile.Card(1, 1)] * 30
ui.discard_rows = [
    mk([(1, 4), (1, 7), (2, 1), (2, 9), (3, 5), (3, 8)]),
    mk([(1, 6), (2, 2), (2, 4), (3, 3), (3, 6), (1, 9), (2, 5)]),
    mk([(1, 8), (3, 1), (3, 4), (2, 6), (1, 3)]),
    mk([(2, 7), (3, 2), (3, 7), (1, 5), (2, 8), (3, 9), (2, 3), (1, 2)]),
]
ui.GAME_STATE = ui.STATE_WAIT_DISCARD
ui.current = 0
ui.selected = 5
ui.has_picked = True
ui.need_draw = False
ui.pick = hand[-1]
ui.difficulty = 2
ui.messages = collections.deque(
    ["玩家3 先出牌", "玩家2碰 五万", "玩家4暗杠 七筒",
     "玩家1打出四条", "玩家3自摸，2番"], maxlen=5)
ui.banner_text = "可以自摸胡牌！"
ui.banner_until = 9e9
ui.ting_cache = tile.ting_card(ui.Player_List[0])
ui.response_actions = set()
save("2_my_turn.png")

# ---------- 3. 响应阶段（碰/杠/胡/过） ----------
ui.GAME_STATE = ui.STATE_WAIT_RESPONSE
ui.response_actions = {"碰", "胡"}
ui.last_card = tile.Card(1, 5)
ui.discarder = 3
ui.discard_rows[3].append(ui.last_card)
ui.banner_text = "玩家4 碰"
ui.banner_until = 9e9
save("3_response.png")

# ---------- 4. 结算界面 ----------
ui.Vic_rank = [(3, 4), (1, 2)]
ui.Player_List[3].Vic_bool = True
ui.Player_List[1].Vic_bool = True
ui.deck = []
ui.GAME_STATE = ui.STATE_GAME_OVER
ui.banner_text = "本局结束"
save("4_settlement.png")
