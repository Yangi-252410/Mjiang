import pygame

pygame.init()
pygame.display.set_caption("麻将")
screen = pygame.display.set_mode((1280,720))

running = True
QUIT_key = pygame.K_x

while running:
    screen.fill((0,140,0))
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == QUIT_key:
                running = False

pygame.quit()
