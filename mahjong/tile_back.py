import random
import operator
import collections
import copy

ch_trans = {1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",}
Suit_name ={2:"筒" ,3:"条" ,1:"万" }

class Card:                 #牌class
    def __init__(self,suit,rank):
        self.suit = Suit_name[suit]
        self.rank = ch_trans[rank]
        self.suit_bit = suit
        self.rank_bit = rank            
        
    def call(self):
        return(f"{self.rank}{self.suit}")
    
    def __repr__(self):
        return f"{self.rank}{self.suit}"

class Player:           #给所有玩家定牌
    def __init__(self,hand,melds,Vic_bool,Tin_bool):
        self.hand = hand
        self.melds = melds
        self.Vic_bool = Vic_bool
        self.Tin_bool = Tin_bool
    def __repr__(self):
        return f"Player(hand={len(self.hand)}张, melds={len(self.melds)})"
# ==================== 创建牌堆 ====================
def Cards():   
    cards = []
    for k in range(1,4):
        for j in range(1,5):
            for i in range(1,10):
                card = Card(k,i)
                cards.append(card)
    random.shuffle(cards)
    return cards


# ==================== 发牌 ====================
def Out_card(cards):
    player_list = [[],[],[],[]]
    
    cards_max = 108-1
    cards_output = 13
    
    for player in range(4):
        
        for own in range(cards_output):
            num = random.randint(0,cards_max)
            random_card = cards[num]
            player_list[player].append(random_card)
            del cards[num]
            cards_max-=1
    return player_list,cards            #返回玩家牌，剩余牌


# ==================== 手牌排序 ====================
def Cards_sort(cards_before):
    cards_sorted = sorted(cards_before,key=operator.attrgetter('suit_bit','rank_bit'))
    return cards_sorted
# ==================== 牌组分类 ====================
def cards_suit_sort(hand_cards):
    C_bit=0
    D_bit=0
    T_bit=0
    characters=[]
    dots=[]
    tiles=[]
    for card in hand_cards:
        match card.suit_bit:
            case 1:
                characters.append(card)
                C_bit+=1
            case 2:
                dots.append(card)
                D_bit+=1
            case 3:
                tiles.append(card)
                T_bit+=1
    suit_bit = [C_bit,D_bit,T_bit]
    return characters,dots,tiles,suit_bit

# ==================== 索引生成 ====================
def hand_to_counts(hand):
    counts = [0] * 34
    for card in hand:
        counts[(card.rank_bit-1)+(card.suit_bit-1)*9] +=1
    return counts
# ==================== 判断面子 ====================
def can_form_Mantsu(counts):
    for i in range(34):
        if counts[i]>0:
            break
    else:
        return True
    if counts[i]==4:
        counts[i]-=4
        if can_form_Mantsu(counts):
            return True
        counts[i]+=4
    if counts[i]>=3:
        counts[i]-=3
        if can_form_Mantsu(counts):
            return True
        counts[i]+=3
    if i%9<=6 and counts[i+1]>0 and counts[i+2]>0:
        counts[i]-=1
        counts[i+1]-=1
        counts[i+2]-=1
        if can_form_Mantsu(counts):
            return True
        counts[i]+=1
        counts[i+1]+=1
        counts[i+2]+=1
        
    return False
# ==================== 判断听牌 ====================
def ting_card(player):
    cards_check = [Card(i//9+1,i%9+1) for i in range(27)]
    Ting_card = {}
    for CARD in player.hand[:]:
        key = (CARD.suit_bit,CARD.rank_bit)
        if key in Ting_card:
            continue
        
        test_hand = player.hand[:]
        test_hand.remove(CARD)

        ting_list = []
        for card in cards_check:
            test_hand.append(card)
            temp = Player(test_hand[:],player.melds[:],player.Vic_bool,player.Tin_bool)
            if can_Vic(temp):
                ting_list.append(card)
            test_hand.remove(card)
        if ting_list:
            Ting_card[key] = ting_list
    return Ting_card
# ==================== 判断胡牌 ====================
def can_Vic(player):
    hand = player.hand[:]
    card_num = len(hand)
    for meld in player.melds:
        card_num += len(meld)
    if card_num < 14:
        return False
    hand_cards = hand_to_counts(hand)
    for i in range(34):
        if hand_cards[i]>=2:
            hand_cards[i]-=2
            if can_form_Mantsu(hand_cards):
                return True
            hand_cards[i]+=2
    return False
# ==================== 判断胡牌(点炮) ====================
def can_Ron(player,last_card):
    hand = player.hand[:] + [last_card]
    for meld in player.melds:
        hand.extend(meld)
    hand_cards = hand_to_counts(hand)
    for i in range(34):
        if hand_cards[i]>=2:
            hand_cards[i]-=2
            if can_form_Mantsu(hand_cards):
                return True
            hand_cards[i]+=2
    return False
# ==================== 摸牌 ====================
def pick_card(play_cards,cards):
    if not cards:
        return play_cards,cards
    play_cards.append(cards[-1])
    pick = cards[-1]
    cards.pop()
    return play_cards,cards,pick         #1玩家手牌2牌库

# ==================== 碰杠逻辑2 ====================
def can_Pon(last_card,player):  #碰检测
    card_count = 0
    
    for card in player.hand[:]:
        if (last_card.suit_bit,last_card.rank_bit) == (card.suit_bit,card.rank_bit):
            card_count +=1
            if card_count == 2:
                return True
    return False
def can_ming_Kon(last_card,player):     #明杠检测
    card_count = 0
    for card in player.hand[:]:
        if (last_card.suit_bit,last_card.rank_bit) == (card.suit_bit,card.rank_bit):
            card_count +=1
            if card_count == 3:
                return True
    return False
def can_an_Kon(pick,player):   #暗杠检测
    card_count = 0
    for card in player.hand[:]:
        if (pick.suit_bit,pick.rank_bit) == (card.suit_bit,card.rank_bit):
            card_count +=1
            if card_count == 4:
                return True
    return False
        
def do_Pon(last_card,player):   #碰
    pon_cards = [last_card]
    removed = 0
    for card in player.hand[:]:
        if (last_card.suit_bit,last_card.rank_bit) == (card.suit_bit,card.rank_bit):
            player.hand.remove(card)
            pon_cards.append(card)
            removed+=1
            if removed == 2:
                break
    player.melds.append(pon_cards)
    player.hand = Cards_sort(player.hand)
    
    return player
def do_ming_Kon(last_card,player):   #明杠
    removed = 0
    ming_Kon = [last_card]
    for card in player.hand[:]:
        if (last_card.suit_bit,last_card.rank_bit) == (card.suit_bit,card.rank_bit):
            player.hand.remove(card)
            ming_Kon.append(card)
            removed +=1
            if removed == 3:
                break
    
    player.melds.append(ming_Kon)
    player.hand = Cards_sort(player.hand)
    return player
def do_an_Kon(pick,player):   #暗杠
    removed = 0
    an_Kon = []
    for card in player.hand[:]:
        if (pick.suit_bit,pick.rank_bit) == (card.suit_bit,card.rank_bit):
            player.hand.remove(card)
            an_Kon.append(card)
            removed +=1
            if removed == 4:
                break
    player.melds.append(an_Kon)
    player.hand = Cards_sort(player.hand)
    return player
# ==================== ai判断碰杠 ====================
def ai_easy():
    choice = random.randint(0,1)
    if choice == 1:
        return True
    return False
def ai_normal(player,last_card):
    if can_ming_Kon(last_card,player):
        return True
    elif can_Pon(last_card,player):
        test = copy.deepcopy(player)
        test = do_Pon(last_card,test)
        if ting_card(test):
            return True
        return False
    else:
        return False
def ai_hard(player,last_card):
    if can_Pon(last_card,player):
        Tin_out1 = []
        Tin_num1 = []
        te0 = copy.deepcopy(player)
        Tin_info = ting_card(te0)
        if Tin_info:
            for key,value in Tin_info.items():
                suit,rank = key
                Tin_out1.append(Card(suit,rank))
                Tin_num1.append(len(value))
        else:
            Tin_info = []
        te0 = copy.deepcopy(player)
        test = do_Pon(last_card,te0)    #返回Player参数
        
        Tin_out2 = []
        Tin_num2 = []
        Tin_info = ting_card(test)
        if Tin_info:
            for key,value in Tin_info.items():
                suit,rank = key
                Tin_out2.append(Card(suit,rank))
                Tin_num2.append(len(value))
        else:
            Tin_info = []
        if Tin_info:
            return True
        return False
    elif can_ming_Kon(last_card,player):
        te0 = copy.deepcopy(player)
        test = do_ming_Kon(last_card,te0)    #返回Player参数
        Tin_info2 = ting_card(test)

        if Tin_info2:
            return True
        return False
    else:
        return False 
def can_ai_PonKon(player,last_card,difficulty):
    if difficulty == 1:
        return ai_easy()
    if difficulty == 2:
        return ai_normal(player,last_card)
    if difficulty == 3:
        return ai_hard(player,last_card)

# ==================== ai打牌 ====================
def ai_choose_hard(player,discards):
    discards_count = hand_to_counts(discards)
    hand_count = hand_to_counts(player.hand)

    might_outcard = []

    for i in range(27):
        if hand_count[i] == 1:
            rank_bit = i%9+1
            suit_bit = i//9+1
            left = hand_count[i-1] if i%9>0 else 0
            right = hand_count[i+1] if i%9<8 else 0
            left2 = hand_count[i-2] if i % 9 > 1 else 0
            right2 = hand_count[i+2] if i % 9 < 7 else 0
            if left == 0 and right == 0 and left2 == 0 and right2 == 0:
                might_outcard.append(Card(suit_bit,rank_bit))

    if not might_outcard:
        might_outcard = player.hand[:]

    safe = []
    for card in might_outcard:
        idx = (card.suit_bit-1)*9+(card.rank_bit-1)
        if discards_count[idx] > 0:
            safe.append(card)

    if safe:
        return random.choice(safe)
    else:
        return random.choice(might_outcard)
def ai_choose_normal(player):
    counts = hand_to_counts(player.hand[:])
    for i in range(27):
        if counts[i] == 1:
            card_suit = i//9+1
            card_rank = i%9+1
            left = counts[i-1] if i%9>0 else 0
            right = counts[i+1] if i%9<8 else 0
            left2 = counts[i-2] if i % 9 > 1 else 0
            right2 = counts[i+2] if i % 9 < 7 else 0
            if left == 0 and right == 0 and left2 == 0 and right2 == 0:
                for card in player.hand[:]:
                    if card.suit_bit == card_suit and card.rank_bit == card_rank:
                        return card
    return random.choice(player.hand)
def ai_outcard(player,discards,difficulty):
    dif_set = {1:"easy",2:"normal",3:"hard"}
    difficulty = dif_set[difficulty]
    if not player.hand:
        return player,deck,None
    if difficulty == 'easy':
        single_out = random.choice(player.hand)
    elif difficulty == 'normal':
        single_out = ai_choose_normal(player)
        
    elif difficulty == 'hard':
        single_out = random.choice(player.hand)#ai_choose_hard(player)
    last_card = single_out
    
    player.hand.remove(single_out)
    return player,last_card
# ==================== 玩家打牌 ====================
def My_outcard(player):
    if not player.hand:
        return player,None
    #print(f"玩家的手牌为{player.hand}")
    while True:
        single_out = input("请输入要打的牌")
        Found = False
        for card in player.hand:
            if f"{card.rank}{card.suit}" == single_out:
                last_card = card

                player.hand.remove(card)
                print(f'打出了{card}')
                Found = True
                break
        if Found:
            break
        else:
            print('没有这张牌')

    return player,last_card
# ==================== 番数计数 ====================
def can_Flush(player):      #清一色检测
    hand = player.hand[:]
    for meld in player.melds:
        hand.extend(meld)
    suits = []
    for card in hand:
        suits.append(card.suit_bit)
    return len(set(suits)) == 1      
    
def can_Toitoi(player):         #碰碰胡检测
    hand = player.hand[:]
    for meld in player.melds:
        hand.extend(meld)
    cards_count = hand_to_counts(hand)
    Koutsu = 0
    Jantou = 0
    for i in range(34):
        if cards_count[i] >= 3:
            Koutsu += 1
        if cards_count[i] == 2:
            Jantou += 1
        if Jantou == 1 and Koutsu == 4:
            return True
    return False
def calculate(player):
    num = 1
    if can_Flush(player):
        num = 4
        return num
    if can_Toitoi(player):
        num = 2
        return num
    return num
        
# ==================== 游戏循环 ====================
all_cards = Cards()            #发牌
player_list,deck = Out_card(all_cards)      #解包玩家分牌，剩余牌库
Player_List = [Player(hand,[],False,False) for hand in player_list]       #定义每个玩家，player[]为Player类型，有hand,melds,Vic_bool
discards = []           #弃牌库

max_player = 4
i = random.randint(0,max_player-1)      #最大玩家数量，每一轮玩家开始位置，玩家胜者顺序，

lacks = [0] * 4             #定义玩家缺牌
Vic_rank = []               
Exist_player = [0,1,2,3]    #定义玩家游玩序列，胡牌后跳过该索引

game_over = False
last_card = None    #定义上一张出的牌，摸到的牌
pick = None
Kon_player = None
Pon_player = None
difficulty = None


    
while not difficulty:
    difficulty = int(input('请选择难度 （1 for easy,2 for normal,3 for hard）'))
    if difficulty not in [1,2,3]:
        print ('请重新输入')
        difficulty = None

print (f'你是玩家1，由玩家{i+1}先出牌')
while not game_over and max_player > 0 :
    discard = i
    
    if deck == [] or max_player <= 1:   #牌出完，玩家数只剩下1，结束游戏
        game_over = True
        break
    if not i in Exist_player:           #跳过不在exist_player中的玩家
        i = (i+1)%len(Player_List)
        continue
    
    if Pon_player is None:
        Player_List[i].hand,deck,pick = pick_card(Player_List[i].hand,deck)       #每轮摸牌,跳过碰的玩家摸牌

#摸牌，检测胡牌，检测暗杠，出牌，其他玩家检测胡碰杠，出牌权轮换，

    
    if can_Vic(Player_List[i]):
        fan = calculate(Player_List[i])
        print(f'玩家{i+1}自摸了,{fan}番')#判断自摸
        Exist_player.remove(i)
        Vic_rank.append((i,fan))
        max_player -=1
        Player_List[i].Vic_bool = True
        i = (i + 1) % len(Player_List)
        continue
    
    Player_List[i].hand = Cards_sort(Player_List[i].hand)   #给玩家手牌排序
    
    
        
    if i == 0:  #针对玩家
        
        if can_an_Kon(pick,Player_List[i]):#检测暗杠
            reply = input(f'可输入 Y/N 选择是否暗杠{pick}')
            if reply == 'Y':
                Player_List[i] = do_an_Kon(pick,Player_List[i])
                print(f'您暗杠了{pick}')
                print(f"melds现在是：{Player_List[i].melds}")
                continue
        print(f'牌库还有{len(deck)}张')
        if Pon_player is None:
            print(f'你摸到{pick.rank}{pick.suit}')
            
        ting_info = ting_card(Player_List[i])
        if ting_info:           #人类玩家听牌提示
            print("听牌提示：")
            for (suit_bit,rank_bit),ting_list in ting_info.items():
                card_name = f'{ch_trans[rank_bit]}{Suit_name[suit_bit]}'
                print(f"  打出「{card_name}」听：{ting_list}")
        print(f'您的手牌是{Player_List[i].hand}')
        Player_List[i],last_card = My_outcard(Player_List[i])         #出牌
        
    else:   #针对ai
        if can_an_Kon(pick,Player_List[i]):#检测暗杠
            choice = random.randint(0,1)
            if choice == 1:
                Player_List[i] = do_an_Kon(pick,Player_List[i])
                print(f'玩家{i+1}暗杠了{pick}')
                print(f"melds现在是：{Player_List[i].melds}") 
                continue
        Player_List[i],last_card = ai_outcard(Player_List[i],discards,difficulty)         #ai出牌

    if last_card: 
        print (f'玩家{i+1}打出{last_card}')
        discards.append(last_card)      #默认给弃牌库加一张

    if 0 in lacks:#缺牌检测
        lacks[i] = last_card.suit_bit

    #Ron_num = 0         #点炮数量，可能存在多人共胡

    
    Kon_player = None
    Pon_player = None
    
    for X in range(1,4):
        j = (discard+X)%len(Player_List)
        if j not in Exist_player:
            continue
        if can_Ron(Player_List[j],last_card):  #点炮检测
            fan = calculate(Player_List[j])
            print(f'玩家{j+1}胡了玩家{discard+1}的牌，{fan}番')
            Player_List[j].hand.append(last_card)        #将点炮的牌交给玩家i
            Exist_player.remove(j)
            Vic_rank.append((j,fan))
            max_player -=1
            Player_List[j].Vic_bool = True
            discards.pop()      #默认给弃牌库末尾删除
            #Ron_num +=1
            continue
        if j == 0:      #轮到玩家判断碰杠
            if can_ming_Kon(last_card,Player_List[j]):   #明杠检测
                
                reply = input(f'可输入 Y/N 选择是否明杠{last_card}')
                if reply == 'Y':
                    Player_List[j] = do_ming_Kon(last_card,Player_List[j])
                    print(f'您明杠了{last_card}')
                    print(f"副露现在是：{Player_List[j].melds}")
                    Kon_player = j
                    discards.pop()      #默认给弃牌库末尾删除
                    break       #杠后break该遍历，i也不变，让玩家i再次主循环一次模拟杠后摸牌+打牌
            if can_Pon(last_card,Player_List[j]):       #碰检测
                reply = input(f'可输入 Y/N 选择是否碰{last_card}')
                if reply == 'Y':
                    Player_List[j] = do_Pon(last_card,Player_List[j])
                    print(f'您碰了{last_card}')
                    print(f"副露现在是：{Player_List[j].melds}")
                    Pon_player = j
                    discards.pop()      #默认给弃牌库末尾删除
                    break

        else:           #轮到ai判断碰杠
            if can_ming_Kon(last_card,Player_List[j]):   #明杠检测
                if can_ai_PonKon(Player_List[j],last_card,difficulty):
                    Player_List[j] = do_ming_Kon(last_card,Player_List[j])
                    Kon_player = j
                    print(f'玩家{j+1}明杠了{last_card}')
                    print(f"副露现在是：{Player_List[j].melds}")
                    discards.pop()      #默认给弃牌库末尾删除
                    break 
            if can_Pon(last_card,Player_List[j]):       #碰检测
                if can_ai_PonKon(Player_List[j],last_card,difficulty):
                    Player_List[j] = do_Pon(last_card,Player_List[j])
                    Pon_player = j
                    print(f'玩家{j+1}碰了{last_card}')
                    print(f"副露现在是：{Player_List[j].melds}")
                    discards.pop()      #默认给弃牌库末尾删除
                    break
    
    if Kon_player is not None:
        i = Kon_player
    elif Pon_player is not None:
        i = Pon_player
    else:
        i = (discard+1)%len(Player_List)


i = 0
'''
deck_count = 0
for player in Player_List:
    hand = player.hand[:]
    for meld in player.melds:
        hand.extend(meld)
    deck_count += len(hand)

print(deck_count + len(discards))
'''
if Vic_rank:
    for rank in Vic_rank:
        rank_bit = rank[0]
        fan = rank[1]
        print(f'第{i+1}名,玩家{rank_bit+1},{fan}番')
        i +=1
    print('其余玩家均未胡牌')
else:
    print('所有玩家均未胡牌')
    

