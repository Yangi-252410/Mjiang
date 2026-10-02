# -*- coding: utf-8 -*-
"""dsh/ui_autoplay.py —— UI_test_back.py 的无头(自动)测试

做法: 读取 ../UI_test_back.py 源码 -> 在内存里打两个补丁
      1) AI_DELAY 改成 0，加速整局
      2) 把 pygame.event.get() 换成 _auto_events()，由机器人代替鼠标点击
      3) 在文件末尾追加不变量检查并打印结果
源文件本身不会被修改。

用法: python dsh/ui_autoplay.py [局数]
"""
import io
import json
import os
import random
import re
import sys
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

HERE = Path(__file__).resolve().parent
SRC_PATH = HERE.parent / "UI_test_back.py"
sys.path.insert(0, str(HERE.parent))          # 让被 exec 的源码能 import tile

PREAMBLE = '''
_AUTO = {"step": 0, "done": False, "frames": 0, "t0": 0.0, "err": None}
_REAL_GET = None


def _auto_btn(text):
    for b in visible_buttons():
        if b["text"] == text and b["enabled"]:
            return pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                      {"pos": (b["x"] + b["w"] // 2,
                                               b["y"] + b["h"] // 2), "button": 1})
    return None


def _auto_events():
    global _REAL_GET
    if _REAL_GET is None:
        _REAL_GET = pygame.event.get
        _AUTO["t0"] = time.time()
    evs = list(_REAL_GET())
    if _AUTO["done"]:
        return evs
    _AUTO["frames"] += 1
    if _AUTO["frames"] > 6000 or time.time() - _AUTO["t0"] > 120:
        _AUTO["done"] = True
        evs.append(pygame.event.Event(pygame.QUIT))
        return evs
    try:
        if GAME_STATE == STATE_BEGIN:
            if _AUTO["frames"] > 3:      # 前几帧先空跑，复现"刚启动还没选难度"的画面
                e = _auto_btn("困难")
                if e:
                    evs.append(e)
        elif GAME_STATE == STATE_GAME_OVER:
            _AUTO["done"] = True
            evs.append(pygame.event.Event(pygame.QUIT))
        elif GAME_STATE == STATE_WAIT_RESPONSE:
            opts = [b["text"] for b in visible_buttons() if b["enabled"]]
            for pref in ("胡", "杠", "碰", "过"):
                if pref in opts and (pref != "过" or random.random() < 0.35):
                    e = _auto_btn(pref)
                    if e:
                        evs.append(e)
                        break
        elif GAME_STATE == STATE_WAIT_DISCARD and current == 0 and not Player_List[0].Vic_bool:
            n = len(Player_List[0].hand)
            if n:
                if (_FORCE_WIN and not _AUTO.get("rigged") and _AUTO["frames"] > 20):
                    # 给玩家1 发一副"打出去/摸进来就能胡"的牌；先验证合法性再采用
                    old = list(Player_List[0].hand)
                    m = len(Player_List[0].melds)
                    sets = [[tile.Card(1, 1)] * 3, [tile.Card(1, 2)] * 3,
                            [tile.Card(1, 3)] * 3, [tile.Card(1, 5)] * 3]
                    cand = [c for s in sets[:max(4 - m, 0)] for c in s] + [tile.Card(1, 7)] * 2
                    Player_List[0].hand = cand
                    if tile.can_Vic(Player_List[0]):
                        _AUTO["rigged"] = True
                        _AUTO["step"] = 0
                    else:
                        Player_List[0].hand = old
                if _AUTO["step"] == 0:
                    for pref in ("胡", "杠"):
                        if pref == "胡" or random.random() < 0.9:   # 能胡就胡，别手滑
                            e = _auto_btn(pref)
                            if e:
                                evs.append(e)
                                return evs
                    r = card_rect(random.randrange(n))
                    evs.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                  {"pos": (r.centerx, r.centery), "button": 1}))
                    _AUTO["step"] = 1
                else:
                    e = _auto_btn("出牌")
                    if e:
                        evs.append(e)
                    _AUTO["step"] = 0
    except Exception as ex:                       # 机器人出错不该掩盖真实异常
        _AUTO["err"] = repr(ex)
    return evs


_PK = {"asked": 0, "yes": 0}
_ai_pk = tile.can_ai_PonKon


def _pk_count(player, last_card, difficulty):
    _PK["asked"] += 1
    r = _ai_pk(player, last_card, difficulty)
    if r:
        _PK["yes"] += 1
    return r


tile.can_ai_PonKon = _pk_count
'''

CHECKS = '''
_live = [c for p in Player_List for c in p.hand]
for _p in Player_List:
    for _m in _p.melds:
        _live = _live + list(_m)
_live = _live + list(deck)
_kinds = {}
for _c in _live:
    _k = (_c.suit_bit, _c.rank_bit)
    _kinds[_k] = _kinds.get(_k, 0) + 1
_RESULT["state"] = GAME_STATE
_RESULT["winners"] = [[j, f] for j, f in Vic_rank]
_RESULT["hands"] = [[len(p.hand), len(p.melds), p.Vic_bool] for p in Player_List]
_RESULT["deck_left"] = len(deck)
_RESULT["live"] = len(_live)
_RESULT["dup_obj"] = len(_live) - len({id(c) for c in _live})
_RESULT["over4"] = sorted(v for v in _kinds.values() if v > 4)
_RESULT["discards"] = sum(len(r) for r in discard_rows)
_RESULT["meld_lens"] = [[len(m) for m in p.melds] for p in Player_List]
_RESULT["ponkon"] = _PK
_RESULT["frames"] = _AUTO["frames"]
_RESULT["rigged"] = bool(_AUTO.get("rigged"))
_RESULT["bot_err"] = _AUTO["err"]
_RESULT["active"] = active_count()
print("AUTOPLAY_RESULT " + json.dumps(_RESULT, ensure_ascii=False))
'''


def build_source(seed, force_win=False):
    src = SRC_PATH.read_text(encoding="utf-8")
    assert src.count("pygame.event.get()") == 1, "预期只有一处 pygame.event.get()"
    src = src.replace("pygame.event.get()", "_auto_events()")
    src = src.replace("AI_DELAY = 0.8", "AI_DELAY = 0.0")
    pre = "_FORCE_WIN = %r\n" % force_win + PREAMBLE
    src = src.replace("import tile", "import tile\nimport json\n" + pre, 1)
    src = src.replace('if __name__ == "__main__":\n    main()',
                      'if __name__ == "__main__":\n    random.seed(%d)\n    main()\n' % seed + CHECKS, 1)
    return src


def run_one(seed, force_win=False):
    ns = {"__name__": "__main__", "_RESULT": {}}
    buf = io.StringIO()
    err = None
    try:
        with redirect_stdout(buf):
            exec(compile(build_source(seed, force_win), "ui_autoplay_src", "exec"), ns)
    except Exception:
        err = traceback.format_exc()
    out = buf.getvalue()
    res = dict(ns.get("_RESULT", {}))
    m = re.search(r"AUTOPLAY_RESULT (\{.*\})", out)
    if m:
        res.update(json.loads(m.group(1)))
    if err:
        res["exception"] = err.strip().splitlines()[-3:]
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force_win = "--force-win" in sys.argv
    rounds = int(args[0]) if args else 8
    bad = 0
    for seed in range(rounds):
        r = run_one(seed, force_win)
        problems = []
        if force_win and r.get("rigged") and not any(j == 0 for j, _ in r.get("winners", [])):
            problems.append("强制发胡牌后玩家1 没有胡牌")
        if force_win and r.get("rigged") and r.get("state") != "game_over":
            problems.append("胡牌后没能走到结算")
        if "exception" in r:
            problems.append("异常: " + " | ".join(r["exception"]))
        if r.get("state") != "game_over":
            problems.append(f"没走到结算 (state={r.get('state')})")
        if r.get("dup_obj") and not force_win:
            problems.append(f"同一张牌被重复引用 {r['dup_obj']} 次")
        if r.get("over4") and not force_win:
            problems.append(f"某花色点数超过4张: {r['over4']}")
        if r.get("live", 0) > 108:
            problems.append(f"存活牌数 {r['live']} > 108")
        if r.get("bot_err"):
            problems.append("机器人异常: " + r["bot_err"])
        if r.get("active", 0) > 1 and r.get("deck_left", 0) > 0:
            problems.append("结束时既没摸完牌也没剩1人")
        if problems:
            bad += 1
        print(f"seed={seed} 状态={r.get('state')} 胡牌={r.get('winners')} "
              f"手牌={r.get('hands')} 副露张数={r.get('meld_lens')} "
              f"AI碰杠询问={r.get('ponkon')} 剩余牌堆={r.get('deck_left')} "
              f"存活牌={r.get('live')} 弃牌={r.get('discards')} 帧={r.get('frames')}")
        for p in problems:
            print("    !! " + p)
    print(f"\n共 {rounds} 局，有问题 {bad} 局")


if __name__ == "__main__":
    main()
