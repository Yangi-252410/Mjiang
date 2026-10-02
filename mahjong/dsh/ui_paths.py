# -*- coding: utf-8 -*-
"""dsh/ui_paths.py —— 逐条验证 UI_test_back.py 的状态机（碰/杠/胡/过/跳过/结算）

不需要人工点击: 直接构造局面 -> 调用界面里的处理函数 -> 断言结果。
UI_test_back.py 本身不会被修改（源码以 __name__ != "__main__" 的方式 exec，
所以它的 main() 不会启动）。

用法: python dsh/ui_paths.py
"""
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

import tile  # noqa: E402

SRC = (ROOT / "UI_test_back.py").read_text(encoding="utf-8")
ui = types.SimpleNamespace()
exec(compile(SRC, "UI_test_back.py", "exec"), ui.__dict__)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [OK]   " if cond else "  [FAIL] ") + name + ("" if cond else f"  <- {detail}"))


def mk(cards):
    return [tile.Card(s, r) for s, r in cards]


# 各种"死牌": 点数间隔 >=3，凑不出顺子，也没有对子 -> 不会误胡
JUNK13 = [(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 4 + [(2, 9)]
TENPAI = [(1, 1)] * 3 + [(1, 2)] * 2 + [(3, 6)] * 3 + [(3, 7)] * 3 + [(3, 8)] * 2   # 13张，听五条/八条


def setup(hands, melds=None, deck_n=8, state="wait_discard", current=0,
          last=None, disc=1, difficulty=1):
    melds = melds or [[], [], [], []]
    ui.Player_List = [tile.Player(mk(hands[i]),
                                  [[tile.Card(s, r) for s, r in m] for m in melds[i]],
                                  False, False) for i in range(4)]
    ui.deck = [tile.Card(3, 9) for _ in range(deck_n)]
    ui.discard_rows = [[], [], [], []]
    ui.Vic_rank = []
    ui.messages = __import__("collections").deque(maxlen=5)
    ui.GAME_STATE = state
    ui.current = current
    ui.last_card = tile.Card(*last) if last else None
    ui.discarder = disc
    ui.response_actions = set()
    ui.need_draw = False
    ui.selected = -1
    ui.ting_cache = None
    ui.has_picked = False
    ui.pick = None
    ui.banner_text = ""
    ui.banner_until = 0
    ui.difficulty = difficulty
    ui.discard_rows[disc].append(ui.last_card) if ui.last_card else None


def overlaps(btns):
    bad = []
    for i in range(len(btns)):
        for j in range(i + 1, len(btns)):
            a, b = btns[i], btns[j]
            if not a["enabled"] or not b["enabled"]:
                continue
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                    and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                bad.append((a["text"], b["text"]))
    return bad


print("=== 0. 程序刚启动、还没选难度时能正常绘制 ===")
ui.Player_List = []
ui.deck = []
ui.discard_rows = [[], [], [], []]
ui.Vic_rank = []
ui.messages = __import__("collections").deque(maxlen=5)
ui.GAME_STATE = ui.STATE_BEGIN
ui.current = 0
ui.last_card = None
ui.discard_rows = [[], [], [], []]
try:
    ui.draw()
    ok, err = True, ""
except Exception as e:                       # noqa: BLE001
    ok, err = False, repr(e)
check("空牌桌 + 开始界面 绘制不报错", ok, err)
try:
    ui.update()
    ok2, err2 = True, ""
except Exception as e:                       # noqa: BLE001
    ok2, err2 = False, repr(e)
check("空牌桌 + 开始界面 update() 不报错", ok2, err2)

print("\n=== 1. 按钮不重叠（各状态） ===")
setup([JUNK13] * 4, state="game_begin")
check("开始界面按钮不重叠", not overlaps(ui.visible_buttons()), overlaps(ui.visible_buttons()))
setup([TENPAI + [(3, 8)], JUNK13, JUNK13, JUNK13], state="wait_discard", current=0)
btns = ui.visible_buttons()
check("出牌界面按钮不重叠", not overlaps(btns), overlaps(btns))
check("能自摸时『胡』可用", any(b["text"] == "胡" and b["enabled"] for b in btns))
ui.selected = 0
check("选中牌后『出牌』可用", any(b["text"] == "出牌" and b["enabled"] for b in ui.visible_buttons()))
setup([JUNK13] * 4, state="wait_response", last=(3, 5))
ui.response_actions = {"碰", "杠", "胡"}
btns = ui.visible_buttons()
check("响应界面按钮不重叠", not overlaps(btns), overlaps(btns))
check("响应界面四个按钮都在",
      {b["text"] for b in btns} == {"碰", "杠", "胡", "过"},
      sorted(b["text"] for b in btns))

print("\n=== 2. 人类点炮胡 ===")
setup([TENPAI, JUNK13, JUNK13, JUNK13], last=(3, 5), disc=1)
ui.open_response(1)
check("进入等待响应", ui.GAME_STATE == ui.STATE_WAIT_RESPONSE, ui.GAME_STATE)
check("提示可以胡", "胡" in ui.response_actions, ui.response_actions)
ui.update()
check("等待响应时 update() 不会自动推进", ui.GAME_STATE == ui.STATE_WAIT_RESPONSE, ui.GAME_STATE)
ui.on_button("胡")
check("玩家1已胡牌", ui.Player_List[0].Vic_bool)
check("记入名次", ui.Vic_rank == [(0, 1)], ui.Vic_rank)
check("点炮的牌进了手牌(14张)", len(ui.Player_List[0].hand) == 14, len(ui.Player_List[0].hand))
check("弃牌区把这张牌移走", len(ui.discard_rows[1]) == 0, ui.discard_rows[1])
check("轮到下家", ui.current == 2 and ui.GAME_STATE == ui.STATE_AI_TURN, (ui.current, ui.GAME_STATE))

print("\n=== 3. 人类碰 ===")
PON13 = [(2, 3)] * 2 + [(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 3
JUNK_B = [(2, 5)] * 4 + [(2, 8)] * 4 + [(2, 9)] * 4 + [(3, 2)]      # 别家抓不到我打出的牌
setup([PON13, JUNK_B, JUNK_B, JUNK_B], last=(2, 3), disc=1)
ui.open_response(1)
check("提示可以碰", ui.response_actions == {"碰"}, ui.response_actions)
ui.on_button("碰")
check("副露为3张", len(ui.Player_List[0].melds) == 1 and len(ui.Player_List[0].melds[0]) == 3)
check("手牌剩11张", len(ui.Player_List[0].hand) == 11, len(ui.Player_List[0].hand))
check("碰后立刻由自己出牌(不摸牌)", ui.current == 0 and ui.GAME_STATE == ui.STATE_WAIT_DISCARD and ui.need_draw is False)
ui.selected = 0
ui.on_button("出牌")
check("碰后可正常出牌", len(ui.Player_List[0].hand) == 10 and len(ui.discard_rows[0]) == 1,
      (len(ui.Player_List[0].hand), len(ui.discard_rows[0])))

print("\n=== 4. 人类明杠 ===")
KON13 = [(2, 3)] * 3 + [(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 2
setup([KON13, JUNK13, JUNK13, JUNK13], last=(2, 3), disc=1)
ui.open_response(1)
check("提示可以杠", "杠" in ui.response_actions, ui.response_actions)
ui.on_button("杠")
check("副露为4张", len(ui.Player_List[0].melds[0]) == 4)
check("杠后需要补摸", ui.need_draw is True and ui.current == 0)
ui.update()
check("补摸后手牌11张(4张在杠里)", len(ui.Player_List[0].hand) == 11, len(ui.Player_List[0].hand))

print("\n=== 5. 人类过 ===")
setup([PON13, JUNK13, JUNK13, JUNK13], last=(2, 3), disc=1)
ui.open_response(1)
ui.on_button("过")
check("过牌后不碰", not ui.Player_List[0].melds)
check("过牌后轮到下家", ui.current == 2, ui.current)

print("\n=== 6. AI 点炮胡 / AI 碰 ===")
setup([JUNK13, JUNK13, TENPAI, JUNK13], last=(3, 5), disc=1)
ui.open_response(1)
check("AI(玩家3)点炮胡", ui.Player_List[2].Vic_bool and ui.Vic_rank[0][0] == 2, ui.Vic_rank)
check("胡牌后跳过已胡玩家", ui.current == 3, ui.current)
AIPON = [(2, 3)] * 2 + [(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 3
_real_easy = tile.ai_easy
tile.ai_easy = lambda: True                     # 让难度1的碰杠判定必定为"要"
setup([JUNK13, AIPON, JUNK13, JUNK13], last=(2, 3), disc=0, difficulty=1)
ui.open_response(0)
check("AI(玩家2)碰牌", len(ui.Player_List[1].melds) == 1 and ui.current == 1,
      (len(ui.Player_List[1].melds), ui.current))
check("AI碰后直接出牌(不摸牌)", ui.need_draw is False and ui.GAME_STATE == ui.STATE_AI_TURN,
      (ui.need_draw, ui.GAME_STATE))
tile.ai_easy = _real_easy

print("\n=== 7. 已胡玩家被跳过 ===")
setup([JUNK13] * 4, state="wait_discard", current=0)
ui.Player_List[1].Vic_bool = True
check("next_active 跳过已胡", ui.next_active(0) == 2, ui.next_active(0))
ui.last_card = tile.Card(2, 3)
check("响应扫描跳过已胡", ui.ron_candidates(0) == [] and ui.pon_opportunity(0) is None)
ui.current = 1
check("已胡玩家没有按钮", ui.visible_buttons() == [],
      [b["text"] for b in ui.visible_buttons()])
ui.current = 0
ui.Player_List[2].Vic_bool = True
ui.Player_List[3].Vic_bool = True
ok = ui.game_over_check()
check("只剩1人未胡 -> 结束", ok and ui.GAME_STATE == ui.STATE_GAME_OVER,
      (ok, ui.GAME_STATE, ui.active_count(), len(ui.deck)))

print("\n=== 8. 玩家自摸 / 暗杠 ===")
WIN14 = [(1, 1)] * 3 + [(1, 2)] * 2 + [(3, 6)] * 3 + [(3, 7)] * 3 + [(3, 8)] * 3
setup([WIN14, JUNK13, JUNK13, JUNK13], state="wait_discard", current=0)
check("自摸时『胡』可用", any(b["text"] == "胡" and b["enabled"] for b in ui.visible_buttons()))
ui.on_button("胡")
check("自摸记入名次(碰碰胡2番)", ui.Vic_rank == [(0, 2)], ui.Vic_rank)
ANKON14 = [(2, 9)] * 4 + [(2, 1)] * 4 + [(2, 4)] * 4 + [(2, 7)] * 2
setup([ANKON14, JUNK13, JUNK13, JUNK13], state="wait_discard", current=0)
ui.pick = tile.Card(2, 9)
ui.need_draw = False
check("暗杠时『杠』可用", any(b["text"] == "杠" and b["enabled"] for b in ui.visible_buttons()))
ui.on_button("杠")
check("暗杠副露4张", len(ui.Player_List[0].melds[0]) == 4)
ui.update()
check("暗杠后补摸一张", len(ui.Player_List[0].hand) == 11, len(ui.Player_List[0].hand))

print("\n=== 9. 结算界面 ===")
setup([JUNK13, JUNK13, TENPAI, JUNK13], last=(3, 5), disc=1)
ui.open_response(1)
ui.deck = []
ui.game_over_check()
check("牌堆摸完 -> 结束", ui.GAME_STATE == ui.STATE_GAME_OVER)
check("结算有退出按钮", any(b["text"] == "退出" for b in ui.visible_buttons()))
try:
    ui.draw()
    ok = True
    err = ""
except Exception as e:                       # noqa: BLE001
    ok, err = False, repr(e)
check("结算界面绘制不报错", ok, err)

print(f"\n通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    print("失败项：" + "、".join(FAIL))
    sys.exit(1)
