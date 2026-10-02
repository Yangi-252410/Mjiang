import pygame
import tile
import random
import time

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("四川麻将")
font = pygame.font.SysFont("simhei", 24)

start_x,start_y = 200,500
card_w,card_h = 60,80

last_ai_time = time.time()
ai_delay = 1   # 1秒

buttons = [
    {"text": "出牌", "x": 420, "y": 620, "w": 80, "h": 40},
    {"text": "碰",   "x": 520, "y": 620, "w": 80, "h": 40},
    {"text": "杠",   "x": 620, "y": 620, "w": 80, "h": 40},
    {"text": "胡",   "x": 720, "y": 620, "w": 80, "h": 40},
    {"text": "过",   "x": 720, "y": 620, "w": 80, "h": 40},
]

opponent_count = 13     #对家Ui
back_w, back_h = 40, 55
back_gap = 0
total_w = opponent_count * (back_w + back_gap) - back_gap
opp_start_x = (1280 - total_w) // 2   # 居中
opp_y = 30
gap = 5

left_count = 13     #左家UI
left_x = 30
left_start_y = 150

right_count = 13
right_x = 1280 - 30 - back_h        #右家UI
right_start_y = 150

#弃牌区
discard_pile = []   # 示例
discard_x = 150
discard_y = 100
discard_w = 50
discard_h = 65
discard_gap = 3
cards_per_row = 10

 
selected = -1
running = True

deck = tile.Cards()     #创建牌库
player_list,deck = tile.Out_card(deck)  #玩家分牌，返回剩余牌库
Player_List = [tile.Player(hand, [], False, False) for hand in player_list]
#状态机
STATE_WAIT_DISCARD = "wait_discard"    # 等待玩家出牌
has_picked = False
player_picked = False


STATE_AI_TURN = "ai_turn"              # AI回合
STATE_GAME_OVER = "game_over"
STATE_BEGIN = "game_begin"
STATE_WAIT_RESPONSE = "wait_response"   # 等待玩家碰/杠/胡

current = random.randint(0,len(Player_List)-1)   #当前轮盘顺序

GAME_STATE = STATE_WAIT_DISCARD#STATE_BEGIN
last_card = None        #定义上次出牌
pick = None             #定义摸到的牌


#状态轮换
def switch_turn():
    global GAME_STATE,current
    if len(deck) == 0:
        GAME_STATE = STATE_GAME_OVER
    elif current == 0:
        GAME_STATE = STATE_WAIT_DISCARD
    else:
        GAME_STATE = STATE_AI_TURN
        
switch_turn()

while running:
    if Player_List[current].Vic_bool == True:
        current= (current+1)%4
        continue
    
    screen.fill((0,100,0))      #幕布颜色：绿

    state_text = font.render(f"状态：{GAME_STATE}", True, (255, 255, 255))
    screen.blit(state_text, (20, 60))
    
    deck_text = font.render(f"剩余牌：{len(deck)}", True, (255, 255, 255))
    screen.blit(deck_text, (20, 30))
    
    turn_text = font.render(f"轮到玩家{current+1}", True, (255, 255, 255))
    screen.blit(turn_text, (560, 440))
    # 对家
    opp_text = font.render(f"{len(Player_List[2].hand)}张", True, (255, 255, 255))
    screen.blit(opp_text, (opp_start_x + total_w + 10, opp_y))

    # 左家
    left_text = font.render(f"{len(Player_List[1].hand)}张", True, (255, 255, 255))
    screen.blit(left_text, (left_x, left_start_y - 30))

    # 右家
    right_text = font.render(f"{len(Player_List[3].hand)}张", True, (255, 255, 255))
    screen.blit(right_text, (right_x, right_start_y - 30))

    
    if GAME_STATE == STATE_GAME_OVER:
        text = font.render("游戏结束", True, (255, 0, 0))
        screen.blit(text, (500, 300))
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if GAME_STATE == STATE_WAIT_DISCARD:
                mx,my = event.pos
                for btn in buttons:
                    if current != 0:
                        break       #判断是否玩家出牌
                    if btn["x"] <= mx <= btn["x"] + btn["w"] and btn["y"] <= my <= btn["y"] + btn["h"]:
                        if btn['text'] == '出牌' and selected >= 0:
                            last_ai_time = time.time()
                            last_card = Player_List[0].hand[selected]
                            card = Player_List[0].hand.pop(selected)
                            discard_pile.append(card)
                            selected = -1
                            current = (current+1)%4
                            player_picked = False
                            has_picked = False
                            switch_turn()
                            break
                else:
                    for i in range(len(Player_List[0].hand)):
                        x = start_x + i*(card_w+gap)
                        if has_picked and i == len(Player_List[0].hand)-1:
                            x += 30
                        y = start_y
                        if x <= mx <= x+card_w and y <= my <= y+ card_h:
                            selected = i
                            break
                        
    if GAME_STATE == STATE_AI_TURN:
        current_time = time.time()
        if current_time - last_ai_time >= ai_delay:
            last_ai_time = current_time
            deck,pick = tile.pick_card(deck)    #摸牌
            has_picked = True 
            if pick:
                Player_List[current].hand.append(pick)
                Player_List[current].hand = tile.Cards_sort(Player_List[current].hand)
                if tile.can_Vic(Player_List[current]):
                    print(f'玩家{current+1}自摸了')
                    Player_List[current].Vic_bool = True
                    current = (current + 1) % 4
                    switch_turn()
                    continue
            Player_List[current],last_card = tile.ai_outcard(Player_List[current],discard_pile,2)
            if last_card:
                discard_pile.append(last_card)

            current = (current+1)%4
            player_picked = False
            has_picked = False
            switch_turn()
        
    if GAME_STATE == STATE_WAIT_DISCARD and not player_picked:
        
        deck,pick = tile.pick_card(deck)    #摸牌
        has_picked = True 
        if pick:
            Player_List[current].hand = tile.Cards_sort(Player_List[current].hand)  #手牌排序
            Player_List[current].hand.append(pick)          #加入摸到的牌
            if tile.can_Vic(Player_List[0]):
                print('你自摸了')
                Player_List[current].Vic_bool = True
        has_picked = True
        player_picked = True
        switch_turn()
    for i,card_name in enumerate(Player_List[0].hand):     #玩家手牌绘制
        x = start_x + i*(card_w + gap)
        y = start_y-10 if i == selected else start_y
        if has_picked and i == len(Player_List[0].hand)-1:
            x += 30 
            pygame.draw.rect(screen,(255,255,200),(x,y,card_w,card_h))
        else:
            pygame.draw.rect(screen,(255,255,255),(x,y,card_w,card_h))
        pygame.draw.rect(screen,(0,0,0),(x,y,card_w,card_h),2)
        text = font.render(str(card_name),True,(0,0,0))
        text_x = x + (card_w - text.get_width())//2
        text_y = y + (card_h - text.get_height())//2
        screen.blit(text,(text_x,text_y))
        
        
    for i in range(opponent_count):         #对家画牌2
        x = opp_start_x + i * (back_w + back_gap)
        pygame.draw.rect(screen, (50, 50, 150), (x, opp_y, back_w, back_h))
        pygame.draw.rect(screen, (0, 0, 0), (x, opp_y, back_w, back_h), 2)

    for i in range(left_count):         #左家画牌1
        y = left_start_y + i * (back_h + back_gap)/2   # 竖排
        pygame.draw.rect(screen, (50, 50, 150), (left_x, y, back_h, back_w))   # 注意宽高互换
        pygame.draw.rect(screen, (0, 0, 0), (left_x, y, back_h, back_w), 2)

    for i in range(right_count):        #右家画牌3
        y = right_start_y + i * (back_h + back_gap)/2
        pygame.draw.rect(screen, (50, 50, 150), (right_x, y, back_h, back_w))
        pygame.draw.rect(screen, (0, 0, 0), (right_x, y, back_h, back_w), 2)
        
    for btn in buttons:         #四个按钮，出牌，碰，杠，胡
        pygame.draw.rect(screen, (200, 200, 200), (btn["x"], btn["y"], btn["w"], btn["h"]))
        pygame.draw.rect(screen, (0, 0, 0), (btn["x"], btn["y"], btn["w"], btn["h"]), 2)
        text = font.render(btn["text"], True, (0, 0, 0))
        text_x = btn["x"] + (btn["w"] - text.get_width()) // 2
        text_y = btn["y"] + (btn["h"] - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))
    
    
    for i, card in enumerate(discard_pile):    #弃牌区绘制
        if not discard_pile:
            break
        row = i // cards_per_row
        col = i % cards_per_row
        x = discard_x + col * (discard_w + discard_gap)
        y = discard_y + row * (discard_h + discard_gap)
        
        pygame.draw.rect(screen, (255, 255, 255), (x, y, discard_w, discard_h))
        pygame.draw.rect(screen, (0, 0, 0), (x, y, discard_w, discard_h), 2)
    
        text = font.render(str(card), True, (0, 0, 0))
        text_x = x + (discard_w - text.get_width()) // 2
        text_y = y + (discard_h - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))
    
    response_player = None
    response_type = None

    for i in range(1,4):
        idx = (current+i)%4
        if Player_List[idx].Vic_bool == True:
            continue
        if idx == 0:
            if tile.can_Ron(Player_List[idx],last_card):
                response_player = idx
                response_type = 'hu'
                break
            if tile.can_ming_Kon(last_card,Player_List[idx]):
                response_player = idx
                response_type = 'kon'
                break
            if tile.can_Pon(last_card,Player_List[idx]):
                response_player = idx
                response_type = 'pon'
                break
        else:
            if tile.can_Ron(Player_List[idx],last_card):
                response_player = idx
                response_type = 'hu'
                break
            if tile.can_ming_Kon(last_card,Player_List[idx]):
                response_player = idx
                response_type = 'kon'
                break
            if tile.can_Pon(last_card,Player_List[idx]):
                response_player = idx
                response_type = 'pon'
                break
    if response_player == 0:
        GAME_STATE == STATE_WAIT_RESPONSE
    elif response_player is not None:
        match response_type:
            choice = random.randint(0,1)
            case 'hu':
                if choice:
                    
            case 'kon':
            case 'pon':
        
    pygame.display.flip()
pygame.quit()
