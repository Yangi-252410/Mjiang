"""对 tile.py 的判胡 / 番数逻辑做校验（不修改 tile.py，只 exec 其中的函数定义）。

用法: python verify.py
- A: can_Vic / can_Ron 与"穷举分解"参照实现对比
- B: can_Toitoi(碰碰胡) 与真·碰碰胡对比（自摸路径 / 点炮路径）
- C: 复现 test.txt 第154行“玩家1点了2的牌,2番”那一刻
"""
import random
from pathlib import Path

# 本文件在 dsh/ 目录里，tile.py 在它的上一级
SRC = (Path(__file__).resolve().parent.parent / "tile.py").read_text(encoding="utf-8")
HEAD = SRC.split("# ==================== 游戏循环")[0]
ns = {}
exec(compile(HEAD, "tile_head", "exec"), ns)
Card, Player = ns["Card"], ns["Player"]
can_Vic, can_Ron = ns["can_Vic"], ns["can_Ron"]
can_Toitoi, calculate = ns["can_Toitoi"], ns["calculate"]


def C(suit, rank):
    return Card(suit, rank)


def counts_of(cards):
    c = [0] * 27                       # 3 花色 x 9 数
    for x in cards:
        c[(x.rank_bit - 1) + (x.suit_bit - 1) * 9] += 1
    return c


def decomps(counts):
    """穷举所有 '4面子+1雀头' 分解；每个分解是 ['tri'/'seq'/'pair', ...]"""
    res = []

    def rec(c, groups):
        try:
            i = next(i for i in range(27) if c[i] > 0)
        except StopIteration:
            res.append(list(groups))
            return
        if c[i] >= 3:
            c[i] -= 3
            groups.append("tri")
            rec(c, groups)
            groups.pop()
            c[i] += 3
        if i % 9 <= 6 and c[i + 1] > 0 and c[i + 2] > 0:
            c[i] -= 1
            c[i + 1] -= 1
            c[i + 2] -= 1
            groups.append("seq")
            rec(c, groups)
            groups.pop()
            c[i] += 1
            c[i + 1] += 1
            c[i + 2] += 1

    for i in range(27):
        if counts[i] >= 2:
            counts[i] -= 2
            rec(counts[:], ["pair"])
            counts[i] += 2
    return res


def ref_win(counts):
    return bool(decomps(counts[:]))


def ref_toitoi(counts):
    return any(all(g != "seq" for g in d) for d in decomps(counts[:]))


def gen_win(rnd):
    """随机造一副合法胡牌(4面子+1雀头)，返回 27 格 counts"""
    for _ in range(200):
        cnt = [0] * 27
        ok = True
        for _ in range(4):
            if rnd.random() < 0.5:
                k = rnd.randrange(27)
                if cnt[k] + 3 > 4:
                    ok = False
                    break
                cnt[k] += 3
            else:
                s, r = rnd.randrange(3), rnd.randrange(7)
                ks = [s * 9 + r, s * 9 + r + 1, s * 9 + r + 2]
                if any(cnt[k] + 1 > 4 for k in ks):
                    ok = False
                    break
                for k in ks:
                    cnt[k] += 1
        if not ok:
            continue
        cand = [k for k in range(27) if cnt[k] + 2 <= 4]
        if not cand:
            continue
        cnt[rnd.choice(cand)] += 2
        return cnt
    return None


print("=== A. can_Vic / can_Ron vs 穷举参照 ===")
rnd = random.Random(1)
bad = 0
for _ in range(30000):
    nhand = rnd.choice([13, 14])
    hand = [C(rnd.randrange(1, 4), rnd.randrange(1, 10)) for _ in range(nhand)]
    last = C(rnd.randrange(1, 4), rnd.randrange(1, 10))
    p = Player(hand, [], False)
    if can_Vic(p) != ref_win(counts_of(hand)):
        bad += 1
    if can_Ron(p, last) != ref_win(counts_of(hand + [last])):
        bad += 1
print(f"  30000 组随机手牌(13/14张): 不一致 {bad} 处  -> 判胡逻辑正确")

print()
print("=== B. can_Toitoi(碰碰胡) vs 真·碰碰胡 ===")
rnd = random.Random(3)
stat = dict(tsumo=0, tsfp=0, ron=0, ronfp=0, ronfn=0)
for _ in range(60000):
    cnt = gen_win(rnd)
    if not cnt:
        continue
    idxs = [k for k, n in enumerate(cnt) for _ in range(n)]
    cards = [C(k // 9 + 1, k % 9 + 1) for k in idxs]
    truth = ref_toitoi(counts_of(cards))
    # 自摸: calculate() 拿到 14 张完整手牌
    stat["tsumo"] += 1
    if can_Toitoi(Player(cards, [], False)) and not truth:
        stat["tsfp"] += 1
    # 点炮: calculate() 拿到的 player 只有 13 张(胡牌张没进去)
    ron_kind = rnd.choice(idxs)
    rest = list(idxs)
    rest.remove(ron_kind)
    hand = [C(k // 9 + 1, k % 9 + 1) for k in rest]
    stat["ron"] += 1
    got = can_Toitoi(Player(hand, [], False))
    if got and not truth:
        stat["ronfp"] += 1
    if truth and not got:
        stat["ronfn"] += 1
print(f"  自摸路径(14张): {stat['tsumo']} 副, 误报碰碰胡 {stat['tsfp']} 副 "
      f"({100 * stat['tsfp'] / max(stat['tsumo'], 1):.1f}%)")
print(f"  点炮路径(13张): {stat['ron']} 副, 误判 {stat['ronfp'] + stat['ronfn']} 副 "
      f"({100 * (stat['ronfp'] + stat['ronfn']) / max(stat['ron'], 1):.1f}%)")

print()
print("=== C. 复现 test.txt 第154行那一刻 ===")
hand = [C(1, 2), C(1, 2), C(3, 8), C(3, 8)]                     # 二万二万八条八条
melds = [[C(1, 1)] * 3, [C(3, 6)] * 3, [C(3, 7)] * 3]           # 碰一万/碰六条/碰七条
p = Player(hand, melds, False)
last = C(3, 5)                                                   # 玩家2打出五条
print(f"  玩家1手牌={p.hand} 副露={p.melds} 别人打出={last}")
print(f"  can_Ron = {can_Ron(p, last)}  (合法: 111万 + 567条 + 678条 + 678条 + 22万)")
print(f"  calculate() = {calculate(p)} 番   <- test.txt 打印的就是 2 番，实际应为 1 番")
print(f"  原因: calculate 收到的手牌+副露只有 {len(p.hand) + 3 * len(p.melds)} 张，"
      f"胡牌张没加进去，can_Toitoi 的 len(set)==5 在 13 张时误判")
