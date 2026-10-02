# -*- coding: utf-8 -*-
"""四川麻将 pygame 界面（与 tile.py 配套）

运行:  python UI_test_back.py
打包:  pyinstaller -F -w -n 四川麻将 UI_test_back.py

结构:
    状态机  game_begin -> wait_discard / ai_turn -> wait_response -> ... -> game_over
    switch_turn()  只负责"轮到谁"，绝不覆盖 wait_response
    open_response() 出牌后统一入口: 先判点炮胡(胡优先)，再判碰/杠(只问离出牌者最近的一家)
    已胡玩家在"轮转"和"响应扫描"里都会被跳过
    结束条件: 牌堆摸完 或 只剩 1 人未胡
"""

import random
import time
from collections import deque

import pygame

import tile

# ==================== 窗口 / 字体 ====================
WIN_W, WIN_H = 1280, 720
FPS = 60

pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("四川麻将")
font = pygame.font.SysFont("simhei", 24)        # 常规
font_s = pygame.font.SysFont("simhei", 16)      # 小字（提示/信息）
font_l = pygame.font.SysFont("simhei", 40)      # 结算

# ==================== 颜色 ====================
C_BG = (0, 100, 0)
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_BACK = (50, 50, 150)
C_BTN = (210, 210, 210)
C_BTN_OFF = (120, 120, 120)
C_HL = (255, 255, 200)
C_TEXT = (255, 255, 255)
C_HINT = (255, 255, 160)
C_WARN = (255, 90, 90)

# ==================== 布局 ====================
CARD_W, CARD_H, GAP = 60, 80, 5          # 玩家手牌
HAND_X, HAND_Y = 200, 505
PICK_OFFSET = 30                         # 刚摸到的牌右移，便于区分

MELD_W, MELD_H = 36, 48                  # 副露小牌
MELD_H_STEP, MELD_V_STEP = 22, 20        # 一副露内部的重叠步长（横排/竖排）
MELD_PAD = 14                            # 两副露之间留白
HUMAN_MELD_X, HUMAN_MELD_Y = 200, 452    # 玩家1：摆在手牌上方
TOP_MELD_Y = 58                          # 对家：牌背下方（朝中心）
SIDE_MELD_Y = 120                        # 左右两家：竖排，从上方开始
LEFT_MELD_X = 66                         # 左家：牌背右侧（朝中心）
RIGHT_MELD_X = 1188                      # 右家：牌背左侧（朝中心）

BACK_W_S, BACK_H_S, BACK_GAP_S = 32, 44, 2   # 对家（顶部横排）
TOP_Y = 8
LEFT_X, LEFT_Y, RIGHT_X, STACK_STEP = 18, 140, 1230, 26   # 左右两家竖排

DISCARD_X, DISCARD_Y = 255, 110          # 每人一条弃牌带（原版弃牌区的样子）
DISCARD_W, DISCARD_H, DISCARD_GAP = 46, 54, 3
DISCARD_PER_ROW = 14
DISCARD_ROW_GAP = 68
DISCARD_LABEL_X = 110

INFO_X = 60                              # 左上状态
SIDE_PANEL_X = 1000                      # 右侧：听牌提示 / 牌局消息
BANNER_Y = 404                           # 中央提示横幅
HINT_Y, HINT_RIGHT = 444, 980            # 中央右下角的"可以碰/胡"提示

BTN_W, BTN_H, BTN_Y = 90, 40, 620

AI_DELAY = 0.8            # AI 行动间隔（秒）
BANNER_TIME = 1.6         # 提示横幅停留时间

# ==================== 状态常量 ====================
STATE_BEGIN = "game_begin"
STATE_WAIT_DISCARD = "wait_discard"
STATE_AI_TURN = "ai_turn"
STATE_WAIT_RESPONSE = "wait_response"
STATE_GAME_OVER = "game_over"

STATE_NAME = {
    STATE_BEGIN: "选择难度",
    STATE_WAIT_DISCARD: "等你出牌",
    STATE_AI_TURN: "AI 行动中",
    STATE_WAIT_RESPONSE: "等你碰/杠/胡",
    STATE_GAME_OVER: "本局结束",
}

# ==================== 全局游戏状态 ====================
GAME_STATE = STATE_BEGIN
difficulty = 2
current = 0                 # 当前该谁行动
discarder = -1              # 最近一张牌的出牌者（响应阶段用）
last_card = None            # 最近打出的牌
pick = None                 # 当前玩家刚摸到的牌（没摸牌就是 None）
need_draw = True            # 当前玩家是否还需要摸牌
has_picked = False          # 人类手牌里是否含刚摸的牌（只影响显示）
selected = -1               # 人类选中的手牌下标
response_actions = set()    # 人类在响应阶段可用的动作
ting_cache = None           # 人类听牌提示缓存
messages = deque(maxlen=5)  # 左下消息
Vic_rank = []               # [(玩家下标, 番数)]
banner_text = ""
banner_until = 0.0
last_ai_time = 0.0
running = True
ai_fallback_warned = False

deck = []
Player_List = []
discard_rows = [[], [], [], []]     # 每人一条弃牌带，互不重叠


# ==================== 小工具 ====================
def log(text):
    messages.append(text)


def banner(text, seconds=BANNER_TIME):
    global banner_text, banner_until
    banner_text = text
    banner_until = time.time() + seconds


def active_count():
    """还没胡牌的人数"""
    return sum(1 for p in Player_List if not p.Vic_bool)


def next_active(idx):
    """idx 之后第一个没胡牌的玩家"""
    for k in range(1, 5):
        j = (idx + k) % 4
        if not Player_List[j].Vic_bool:
            return j
    return idx


def all_discards():
    """所有弃牌（供 AI 判断安全牌）"""
    return [c for row in discard_rows for c in row]


def take_discard(d):
    """这张牌被吃走：从弃牌区移除"""
    if discard_rows[d]:
        discard_rows[d].pop()


def card_rect(i):
    """人类手牌第 i 张的矩形（绘制与点击共用）"""
    x = HAND_X + i * (CARD_W + GAP)
    if has_picked and i == len(Player_List[0].hand) - 1:
        x += PICK_OFFSET
    return pygame.Rect(x, HAND_Y, CARD_W, CARD_H)


def game_over_check():
    """只剩 1 人未胡 或 牌堆摸完"""
    global GAME_STATE
    if len(deck) == 0 or active_count() <= 1:
        GAME_STATE = STATE_GAME_OVER
        log("牌局结束")
        banner("本局结束", 5)
        return True
    return False


# ==================== 状态切换 ====================
def switch_turn(j, need_draw_flag=True):
    """轮转到玩家 j。wait_response 由响应流程掌管，这里不会去覆盖它"""
    global current, need_draw, selected, pick, has_picked, ting_cache
    global response_actions, GAME_STATE, last_ai_time

    current = j
    need_draw = need_draw_flag
    selected = -1
    pick = None                 # 关键: 碰/杠后不摸牌，绝不沿用上一张旧牌
    has_picked = False
    ting_cache = None
    response_actions = set()

    if game_over_check():
        return
    last_ai_time = time.time()
    GAME_STATE = STATE_WAIT_DISCARD if j == 0 else STATE_AI_TURN


def draw_tile(j):
    """给玩家 j 摸一张牌，返回摸到的牌（牌堆空返回 None）"""
    global deck, pick, has_picked
    if not deck:
        pick = None
        return None
    deck, pick = tile.pick_card(deck)
    if pick is None:
        return None
    Player_List[j].hand = tile.Cards_sort(Player_List[j].hand)   # 先排序再放摸到的牌
    Player_List[j].hand.append(pick)
    has_picked = (j == 0)
    return pick


def do_win(j, by_ron, from_player=None):
    """记一次胡牌"""
    fan = tile.calculate(Player_List[j])
    Player_List[j].Vic_bool = True
    Vic_rank.append((j, fan))
    if by_ron:
        log(f"玩家{j+1}胡(玩家{from_player+1}) {fan}番")
        banner(f"玩家{j+1} 胡牌 {fan}番")
    else:
        log(f"玩家{j+1}自摸 {fan}番")
        banner(f"玩家{j+1} 自摸 {fan}番")


# ==================== 响应阶段（碰/杠/胡） ====================
def ron_candidates(d):
    """能点炮胡的玩家（从出牌者下家开始按顺序）"""
    out = []
    for k in range(1, 4):
        j = (d + k) % 4
        if Player_List[j].Vic_bool:
            continue
        if tile.can_Ron(Player_List[j], last_card):
            out.append(j)
    return out


def pon_opportunity(d, skip=()):
    """能碰/明杠的玩家 -> (j, can_kon, can_pon)；只返回离出牌者最近的一家"""
    for k in range(1, 4):
        j = (d + k) % 4
        if j in skip or Player_List[j].Vic_bool:
            continue
        can_kon = tile.can_ming_Kon(last_card, Player_List[j])
        can_pon = tile.can_Pon(last_card, Player_List[j])
        if can_kon or can_pon:
            return (j, can_kon, can_pon)
    return None


def open_response(d):
    """某家打出 last_card 之后的统一入口"""
    global GAME_STATE, response_actions, discarder

    discarder = d
    ron = ron_candidates(d)
    human_ron = 0 in ron

    # 1) 点炮胡：AI 立刻胡（胡优先于碰杠）
    ai_ron = [j for j in ron if j != 0]
    for j in ai_ron:
        Player_List[j].hand.append(last_card)      # 先收牌再算番，番数才准
        do_win(j, True, d)
    if ai_ron:
        take_discard(d)
    if game_over_check():
        return

    # 2) 碰/明杠：只问离出牌者最近的一家
    op = pon_opportunity(d)
    actions = set()
    if human_ron:
        actions.add("胡")
    if op is not None and op[0] == 0:
        if op[1]:
            actions.add("杠")
        if op[2]:
            actions.add("碰")

    if actions:                                    # 人类有选择 -> 等按钮
        response_actions = actions
        GAME_STATE = STATE_WAIT_RESPONSE
        return

    if op is not None:                             # 轮到 AI 决定
        j, can_kon, can_pon = op
        if tile.can_ai_PonKon(Player_List[j], last_card, difficulty):
            do_chi(j, "杠" if can_kon else "碰", d)
            return

    finish_response(d)


def finish_response(d):
    """没人响应：轮到出牌者的下家"""
    switch_turn(next_active(d))


def do_chi(j, action, d):
    """碰 或 明杠"""
    if action == "杠":
        Player_List[j] = tile.do_ming_Kon(last_card, Player_List[j])
        take_discard(d)
        log(f"玩家{j+1}明杠 {last_card}")
        banner(f"玩家{j+1} 明杠")
        switch_turn(j, True)          # 杠后补摸一张再出牌
    else:
        Player_List[j] = tile.do_Pon(last_card, Player_List[j])
        take_discard(d)
        log(f"玩家{j+1}碰 {last_card}")
        banner(f"玩家{j+1} 碰")
        switch_turn(j, False)         # 碰后直接出牌，不摸牌


# ==================== 人类玩家动作 ====================
def human_prepare():
    """人类回合：摸牌 + 听牌提示（每回合只算一次）"""
    global need_draw, ting_cache
    if need_draw:
        need_draw = False
        if draw_tile(0) is None:
            game_over_check()
            return
    if ting_cache is None:
        ting_cache = tile.ting_card(Player_List[0])


def human_discard():
    """出牌按钮"""
    global selected, last_card, has_picked, ting_cache
    if selected < 0 or selected >= len(Player_List[0].hand):
        return
    card = Player_List[0].hand[selected]
    Player_List[0], last_card = tile.My_outcard(Player_List[0], card)
    Player_List[0].hand = tile.Cards_sort(Player_List[0].hand)
    discard_rows[0].append(last_card)
    selected = -1
    has_picked = False
    ting_cache = None
    log(f"你打出 {last_card}")
    open_response(0)


def human_win():
    """胡按钮：响应阶段的点炮胡 / 自己回合的自摸"""
    if GAME_STATE == STATE_WAIT_RESPONSE:
        d = discarder
        Player_List[0].hand.append(last_card)      # 收下点炮的牌
        take_discard(d)
        do_win(0, True, d)
        if game_over_check():
            return
        switch_turn(next_active(d))
    else:
        do_win(0, False)
        if game_over_check():
            return
        switch_turn(next_active(0))


def human_ankon():
    """自己回合暗杠（杠按钮），杠完补摸一张继续出牌"""
    global pick, need_draw, has_picked, ting_cache
    if pick is None or not tile.can_an_Kon(pick, Player_List[0]):
        return
    kon_card = pick
    Player_List[0] = tile.do_an_Kon(pick, Player_List[0])
    log(f"你暗杠 {kon_card}")
    banner(f"暗杠 {kon_card}")
    pick = None
    need_draw = True
    has_picked = False
    ting_cache = None


def human_pass():
    """过按钮：放弃这次响应；若别家还能碰/杠则让给别家"""
    op = pon_opportunity(discarder, skip=(0,))
    if op is not None:
        j, can_kon, can_pon = op
        if tile.can_ai_PonKon(Player_List[j], last_card, difficulty):
            do_chi(j, "杠" if can_kon else "碰", discarder)
            return
    finish_response(discarder)


# ==================== AI 回合 ====================
def ai_discard(j):
    """AI 出牌（带兜底）

    注意: tile.ai_choose_hard() 里是 might_outcard.append(Card(suit_bit, rank_bit))，
    返回的是"新造的同名牌"，而 Card 没有定义 __eq__，于是 tile.ai_outcard() 里
    player.hand.remove(single_out) 会抛 ValueError（难度3必崩）。
    tile.py 不改的前提下，这里兜底成随机出牌，保证界面能跑完。
    正确修法（tile.py 第 327 行）：改成从手牌里取真正的对象，例如
        for c in player.hand:
            if c.suit_bit == suit_bit and c.rank_bit == rank_bit:
                might_outcard.append(c); break
    """
    global ai_fallback_warned
    try:
        Player_List[j], card = tile.ai_outcard(Player_List[j], all_discards(), difficulty)
        return card
    except ValueError:
        if not ai_fallback_warned:
            ai_fallback_warned = True
            log("AI出牌异常→改随机出牌")
        card = random.choice(Player_List[j].hand)
        Player_List[j], card = tile.My_outcard(Player_List[j], card)
        return card


def ai_step():
    """AI 的一步：摸牌 -> 暗杠 -> 自摸 -> 出牌 -> 开响应"""
    global last_card, last_ai_time, pick
    j = current
    last_ai_time = time.time()

    if need_draw:
        if draw_tile(j) is None:
            game_over_check()
            return
        if pick is not None and tile.can_an_Kon(pick, Player_List[j]):
            if random.randint(0, 1) == 1:
                kon_card = pick
                Player_List[j] = tile.do_an_Kon(pick, Player_List[j])
                log(f"玩家{j+1}暗杠 {kon_card}")
                banner(f"玩家{j+1} 暗杠")
                if draw_tile(j) is None:           # 暗杠补摸
                    game_over_check()
                    return
        if tile.can_Vic(Player_List[j]):           # 自摸
            Player_List[j].hand = tile.Cards_sort(Player_List[j].hand)
            do_win(j, False)
            if game_over_check():
                return
            switch_turn(next_active(j))
            return

    last_card = ai_discard(j)
    if last_card is None:
        game_over_check()
        return
    discard_rows[j].append(last_card)
    log(f"玩家{j+1}打出{last_card}")
    open_response(j)


# ==================== 按钮 ====================
def visible_buttons():
    """按当前状态给出按钮（位置互不重叠，enabled 决定能否点）"""
    btns = []
    if GAME_STATE == STATE_BEGIN:
        for i, name in enumerate(("简单", "普通", "困难")):
            btns.append({"text": name, "x": 460 + i * 120, "y": 360,
                         "w": 100, "h": 44, "enabled": True})
    elif GAME_STATE == STATE_WAIT_DISCARD and current == 0 and not Player_List[0].Vic_bool:
        can_kon = pick is not None and tile.can_an_Kon(pick, Player_List[0])
        btns.append({"text": "出牌", "x": 200, "y": BTN_Y, "w": BTN_W, "h": BTN_H,
                     "enabled": selected >= 0})
        btns.append({"text": "杠", "x": 300, "y": BTN_Y, "w": BTN_W, "h": BTN_H,
                     "enabled": can_kon})
        btns.append({"text": "胡", "x": 400, "y": BTN_Y, "w": BTN_W, "h": BTN_H,
                     "enabled": tile.can_Vic(Player_List[0])})
    elif GAME_STATE == STATE_WAIT_RESPONSE:
        for i, name in enumerate(("碰", "杠", "胡", "过")):
            btns.append({"text": name, "x": 300 + i * 100, "y": BTN_Y,
                         "w": BTN_W, "h": BTN_H,
                         "enabled": name == "过" or name in response_actions})
    elif GAME_STATE == STATE_GAME_OVER:
        btns.append({"text": "退出", "x": 590, "y": 615, "w": 100, "h": 44, "enabled": True})
    return btns


def hit(btn, pos):
    return btn["x"] <= pos[0] <= btn["x"] + btn["w"] and btn["y"] <= pos[1] <= btn["y"] + btn["h"]


def on_button(text):
    global running, difficulty
    if text in ("简单", "普通", "困难"):
        difficulty = {"简单": 1, "普通": 2, "困难": 3}[text]
        reset_game(difficulty)
    elif text == "出牌":
        human_discard()
    elif text == "胡":
        human_win()
    elif text == "杠":
        if GAME_STATE == STATE_WAIT_RESPONSE:
            do_chi(0, "杠", discarder)
        else:
            human_ankon()
    elif text == "碰":
        do_chi(0, "碰", discarder)
    elif text == "过":
        human_pass()
    elif text == "退出":
        running = False


def handle_click(pos):
    """先判按钮，再判手牌选择"""
    global selected
    for btn in visible_buttons():
        if btn["enabled"] and hit(btn, pos):
            on_button(btn["text"])
            return
    if GAME_STATE == STATE_WAIT_DISCARD and current == 0 and not Player_List[0].Vic_bool:
        for i in range(len(Player_List[0].hand)):
            if card_rect(i).collidepoint(pos):
                selected = i
                return


# ==================== 绘制 ====================
def draw_card(x, y, card, w=CARD_W, h=CARD_H, hl=False, small=False):
    pygame.draw.rect(screen, C_HL if hl else C_WHITE, (x, y, w, h))
    pygame.draw.rect(screen, C_BLACK, (x, y, w, h), 2)
    if card is not None:
        f = font_s if small else font
        text = f.render(str(card), True, C_BLACK)
        screen.blit(text, (x + (w - text.get_width()) // 2, y + (h - text.get_height()) // 2))


def draw_back(x, y, w, h):
    pygame.draw.rect(screen, C_BACK, (x, y, w, h))
    pygame.draw.rect(screen, C_BLACK, (x, y, w, h), 2)


def melds_width(melds):
    """横排副露占的总宽度（用于居中）"""
    total = 0
    for meld in melds:
        if meld:
            total += (len(meld) - 1) * MELD_H_STEP + MELD_W + MELD_PAD
    return max(total - MELD_PAD, 0) if total else 0


def draw_melds_h(melds, x, y):
    """横排画副露（朝向中心），返回排完后的 x"""
    for meld in melds:
        if not meld:
            continue
        for i, card in enumerate(meld):
            draw_card(x + i * MELD_H_STEP, y, card, MELD_W, MELD_H, small=True)
        x += (len(meld) - 1) * MELD_H_STEP + MELD_W + MELD_PAD
    return x


def draw_melds_v(melds, x, y):
    """竖排画副露（左右两家，朝中心方向），返回排完后的 y"""
    for meld in melds:
        if not meld:
            continue
        for i, card in enumerate(meld):
            draw_card(x, y + i * MELD_V_STEP, card, MELD_W, MELD_H, small=True)
        y += (len(meld) - 1) * MELD_V_STEP + MELD_H + MELD_PAD
    return y


def draw_ai_hands():
    # 对家（下标 2）：顶部横排牌背，副露摆在牌背下方（朝中心）
    n = min(len(Player_List[2].hand), 14)
    total = n * (BACK_W_S + BACK_GAP_S) - BACK_GAP_S
    x0 = (WIN_W - total) // 2
    for i in range(n):
        draw_back(x0 + i * (BACK_W_S + BACK_GAP_S), TOP_Y, BACK_W_S, BACK_H_S)
    draw_melds_h(Player_List[2].melds, (WIN_W - melds_width(Player_List[2].melds)) // 2, TOP_MELD_Y)
    if Player_List[2].Vic_bool:
        screen.blit(font_s.render("已胡牌", True, C_WARN), (x0 + total + 8, TOP_Y + 12))

    # 左家（下标 1）：左侧竖排牌背，副露摆在牌背右侧（朝中心）
    n = min(len(Player_List[1].hand), 14)
    for i in range(n):
        draw_back(LEFT_X, LEFT_Y + i * STACK_STEP, BACK_H_S, BACK_W_S)
    draw_melds_v(Player_List[1].melds, LEFT_MELD_X, SIDE_MELD_Y)
    if Player_List[1].Vic_bool:
        screen.blit(font_s.render("已胡牌", True, C_WARN), (LEFT_X, LEFT_Y + n * STACK_STEP + 6))

    # 右家（下标 3）：右侧竖排牌背，副露摆在牌背左侧（朝中心）
    n = min(len(Player_List[3].hand), 14)
    for i in range(n):
        draw_back(RIGHT_X, LEFT_Y + i * STACK_STEP, BACK_H_S, BACK_W_S)
    draw_melds_v(Player_List[3].melds, RIGHT_MELD_X, SIDE_MELD_Y)
    if Player_List[3].Vic_bool:
        screen.blit(font_s.render("已胡牌", True, C_WARN), (RIGHT_X - 10, LEFT_Y + n * STACK_STEP + 6))


def draw_discards():
    """每人一条弃牌带，用原版弃牌区那样的白牌网格，互不重叠"""
    for j in range(4):
        row_y = DISCARD_Y + j * DISCARD_ROW_GAP
        row = discard_rows[j]
        label = f"玩家{j+1} 弃牌 {len(row)}"
        screen.blit(font_s.render(label, True, C_TEXT),
                    (DISCARD_LABEL_X, row_y + DISCARD_H // 2 - 8))
        for i, card in enumerate(row[-DISCARD_PER_ROW:]):
            draw_card(DISCARD_X + i * (DISCARD_W + DISCARD_GAP), row_y,
                      card, DISCARD_W, DISCARD_H, small=True)


def draw_info_panels():
    # 左上: 状态
    screen.blit(font_s.render(f"状态：{STATE_NAME.get(GAME_STATE, GAME_STATE)}", True, C_TEXT), (INFO_X, 14))
    screen.blit(font_s.render(f"剩余牌：{len(deck)}   难度：{difficulty}", True, C_TEXT), (INFO_X, 36))
    screen.blit(font_s.render(f"轮到：玩家{current+1}   未胡：{active_count()}人", True, C_TEXT), (INFO_X, 58))
    screen.blit(font_s.render("你是玩家1（最下方）", True, C_TEXT), (INFO_X, 80))

    # 右侧: 听牌提示
    x, y = SIDE_PANEL_X, 110
    if GAME_STATE == STATE_WAIT_DISCARD and current == 0:
        screen.blit(font_s.render("听牌提示：", True, C_HINT), (x, y))
        y += 24
        if ting_cache:
            for (suit, rank), wait_cards in list(ting_cache.items())[:5]:
                out_name = f"{tile.ch_trans[rank]}{tile.Suit_name[suit]}"
                waits = " ".join(str(c) for c in wait_cards[:4])
                screen.blit(font_s.render(f"打{out_name} 听 {waits}", True, C_HINT), (x, y))
                y += 22
        else:
            screen.blit(font_s.render("（还没听牌）", True, C_TEXT), (x, y))
            y += 22
    elif GAME_STATE == STATE_WAIT_RESPONSE and not Player_List[0].Vic_bool:
        # 响应阶段手上是 13 张，tile.ting_card 要求 14 张，这里用 can_Ron 直接算"现在听什么"
        screen.blit(font_s.render("当前听：", True, C_HINT), (x, y))
        y += 24
        waits = [f"{tile.ch_trans[i % 9 + 1]}{tile.Suit_name[i // 9 + 1]}"
                 for i in range(27) if tile.can_Ron(Player_List[0], tile.Card(i // 9 + 1, i % 9 + 1))]
        screen.blit(font_s.render(" ".join(waits) if waits else "未听牌", True, C_HINT), (x, y))
        y += 22

    # 右侧: 消息
    y = 290
    screen.blit(font_s.render("牌局消息：", True, C_TEXT), (x, y))
    y += 24
    for msg in messages:
        screen.blit(font_s.render(msg, True, C_TEXT), (x, y))
        y += 22


def draw_human_area():
    # 副露：摆在自己上方（手牌之上，朝向桌面中心）
    if Player_List[0].melds:
        screen.blit(font_s.render("我的副露", True, C_HINT), (HUMAN_MELD_X, HUMAN_MELD_Y - 18))
        draw_melds_h(Player_List[0].melds, HUMAN_MELD_X, HUMAN_MELD_Y)

    # 手牌
    for i, card in enumerate(Player_List[0].hand):
        r = card_rect(i)
        draw_card(r.x, r.y - (10 if i == selected else 0), card, CARD_W, CARD_H, hl=(i == selected))
    screen.blit(font_s.render("我的手牌（点牌选中，再点“出牌”）", True, C_TEXT),
                (HAND_X, HAND_Y + CARD_H + 6))
    if Player_List[0].Vic_bool:
        screen.blit(font.render("你已胡牌", True, C_WARN), (HAND_X + 380, HAND_Y + 24))


def draw_center():
    now = time.time()
    if banner_text and now < banner_until:
        text = font_l.render(banner_text, True, C_BLACK)
        box = pygame.Rect(0, 0, text.get_width() + 40, text.get_height() + 20)
        box.center = (WIN_W // 2, BANNER_Y)
        pygame.draw.rect(screen, (255, 230, 120), box)
        pygame.draw.rect(screen, C_BLACK, box, 2)
        screen.blit(text, (box.x + 20, box.y + 10))

    # 可以自摸 / 可以响应的提醒（右下角，右对齐，避免压到副露）
    hint = ""
    if GAME_STATE == STATE_WAIT_DISCARD and current == 0 and tile.can_Vic(Player_List[0]):
        hint = "可以自摸胡牌！点「胡」"
    elif GAME_STATE == STATE_WAIT_RESPONSE and response_actions:
        acts = "/".join(sorted(response_actions))
        hint = f"可以 {acts} 玩家{discarder+1} 的 {last_card}"
    if hint:
        text = font.render(hint, True, C_WARN)
        screen.blit(text, (HINT_RIGHT - text.get_width(), HINT_Y))


def draw_buttons():
    for btn in visible_buttons():
        color = C_BTN if btn["enabled"] else C_BTN_OFF
        pygame.draw.rect(screen, color, (btn["x"], btn["y"], btn["w"], btn["h"]))
        pygame.draw.rect(screen, C_BLACK, (btn["x"], btn["y"], btn["w"], btn["h"]), 2)
        text = font.render(btn["text"], True, C_BLACK if btn["enabled"] else (60, 60, 60))
        screen.blit(text, (btn["x"] + (btn["w"] - text.get_width()) // 2,
                           btn["y"] + (btn["h"] - text.get_height()) // 2))


def draw_begin():
    text = font_l.render("四川麻将", True, C_WHITE)
    screen.blit(text, (WIN_W // 2 - text.get_width() // 2, 240))
    text = font.render("请选择难度", True, C_WHITE)
    screen.blit(text, (WIN_W // 2 - text.get_width() // 2, 310))
    tip = font_s.render("玩法：点手牌选中 -> 点「出牌」；能碰/杠/胡时下排按钮会亮起", True, C_HINT)
    screen.blit(tip, (WIN_W // 2 - tip.get_width() // 2, 430))


def draw_settlement():
    """结算界面: 名次 + 番数"""
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    box = pygame.Rect(0, 0, 620, 330)
    box.center = (WIN_W // 2, 340)
    pygame.draw.rect(screen, (25, 45, 25), box)
    pygame.draw.rect(screen, (255, 215, 0), box, 2)

    text = font_l.render("本局结算", True, (255, 215, 0))
    screen.blit(text, (box.centerx - text.get_width() // 2, box.y + 20))

    y = box.y + 100
    if Vic_rank:
        for idx, (j, fan) in enumerate(Vic_rank):
            line = font.render(f"第 {idx+1} 名    玩家{j+1}    {fan} 番", True, C_WHITE)
            screen.blit(line, (box.centerx - 170, y))
            y += 38
        others = [j for j in range(4) if not Player_List[j].Vic_bool]
        txt = "未胡牌：" + ("、".join(f"玩家{j+1}" for j in others) if others else "无")
        screen.blit(font.render(txt, True, C_WHITE), (box.centerx - 170, y + 14))
    else:
        screen.blit(font.render("所有玩家均未胡牌", True, C_WHITE), (box.centerx - 90, y))


def draw():
    screen.fill(C_BG)
    if Player_List:                     # 还没选难度时没有牌桌，只有标题界面
        draw_ai_hands()
        draw_discards()
        draw_info_panels()
        draw_human_area()
        draw_center()
    draw_buttons()
    if GAME_STATE == STATE_BEGIN:
        draw_begin()
    if GAME_STATE == STATE_GAME_OVER:
        draw_settlement()


# ==================== 一局初始化 ====================
def reset_game(diff):
    global deck, Player_List, discard_rows, Vic_rank, messages
    global selected, pick, last_card, has_picked, response_actions, difficulty

    difficulty = diff
    deck = tile.Cards()
    hands, deck = tile.Out_card(deck)
    Player_List = [tile.Player(h, [], False, False) for h in hands]
    discard_rows = [[], [], [], []]
    Vic_rank = []
    messages = deque(maxlen=5)
    selected = -1
    pick = None
    last_card = None
    has_picked = False
    response_actions = set()

    first = random.randint(0, 3)
    log(f"玩家{first+1} 先出牌")
    banner(f"玩家{first+1} 先出牌")
    switch_turn(first)


# ==================== 状态推进 ====================
def update():
    if GAME_STATE == STATE_WAIT_DISCARD and current == 0:
        human_prepare()
    elif GAME_STATE == STATE_AI_TURN:
        if time.time() - last_ai_time >= AI_DELAY:
            ai_step()


# ==================== 主循环 ====================
def main():
    global running
    clock = pygame.time.Clock()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_click(event.pos)
        update()
        draw()
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
