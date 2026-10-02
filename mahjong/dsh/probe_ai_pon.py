# -*- coding: utf-8 -*-
"""dsh/probe_ai_pon.py —— 查清"AI 从不肯碰/杠"到底是界面的问题还是 tile.py 的策略问题

只读 tile.py，不修改任何文件。
"""
import copy
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tile  # noqa: E402


def mk(cards):
    return [tile.Card(s, r) for s, r in cards]


print("=== 1. ting_card 本身能否工作（构造一副听牌） ===")
# 副露: 六条x3 ; 手牌 11 张: 一万x3 二万x3 三万x3 四万x2  -> 打四万听四万
p = tile.Player(mk([(1, 1)] * 3 + [(1, 2)] * 3 + [(1, 3)] * 3 + [(1, 4)] * 2),
                [mk([(3, 6)] * 3)], False, False)
info = tile.ting_card(p)
print("   ting_card ->", {f"{tile.ch_trans[r]}{tile.Suit_name[s]}": [str(c) for c in v]
                          for (s, r), v in info.items()})
print("   听牌提示可用:", bool(info))

print("\n=== 2. 手牌13张(0副露)时 ting_card 是否可用 ===")
p13 = tile.Player(mk([(1, 1)] * 3 + [(1, 2)] * 3 + [(1, 3)] * 3 + [(1, 4)] * 3 + [(1, 5)]),
                  [], False, False)
print("   13张听牌手的 ting_card ->", tile.ting_card(p13), " (空 = 判定不了)")
print("   原因: tile.can_Vic 要求 hand+melds 张数 >= 14, 13张直接 return False")

print("\n=== 3. AI 碰的接受率（难度3 = ai_hard） ===")
random.seed(5)
t0 = time.time()
asked = yes_pon = kon_reachable = 0
for _ in range(400):
    # 随机造一副"别家打出一张、我能碰"的局面
    idx = random.randrange(27)
    suit, rank = idx // 9 + 1, idx % 9 + 1
    hand = mk([(suit, rank)] * 2 + [(random.randrange(1, 4), random.randrange(1, 10))
                                    for _ in range(11)])
    player = tile.Player(hand, [], False, False)
    last = tile.Card(suit, rank)
    if not tile.can_Pon(last, player):
        continue
    asked += 1
    if tile.can_ming_Kon(last, player):
        kon_reachable += 1
    if tile.can_ai_PonKon(player, last, 3):
        yes_pon += 1
print(f"   询问 {asked} 次(随机的13张手牌)，ai_hard 答应碰 {yes_pon} 次 "
      f"({100*yes_pon/max(asked,1):.1f}%)，耗时 {time.time()-t0:.1f}s")
print(f"   其中'能杠'的情况 {kon_reachable} 次 —— ai_hard 里 can_Pon 先返回，"
      f"elif can_ming_Kon 永远走不到(杠是死分支)")

print("\n=== 4. 静态牌局里 ai_hard 的判断 ===")
p2 = tile.Player(mk([(1, 1)] * 2 + [(1, 2), (1, 3), (1, 4), (2, 1), (2, 5), (2, 9),
                                      (3, 2), (3, 5), (3, 7)]), [], False, False)
last = tile.Card(1, 1)
print("   手牌 13 张、能碰一万 ->", tile.can_ai_PonKon(p2, last, 3),
      "(碰后必须立刻听牌才肯碰，随机手牌很难满足)")
print("   不碰 ->", tile.can_ai_PonKon(p2, tile.Card(2, 9), 3))
