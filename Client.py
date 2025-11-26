import pygame
import socketio
import threading
import time

# -----------------------
# Config
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Server URL (ersetze durch deine Railway-URL)
SERVER_URL = "https://deine-railway-url.up.railway.app"

sio = socketio.Client()

# -----------------------
# Game state
player_id = None
players = {}
terrain = []

# -----------------------
# Pygame setup
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Offroad Racing")
clock = pygame.time.Clock()

# -----------------------
# SocketIO handlers
@sio.event
def connect():
    print("Connected to server")

@sio.event
def disconnect():
    print("Disconnected from server")

@sio.on('init')
def on_init(data):
    global player_id, players, terrain
    player_id = data['your_id']
    players = data['players']
    terrain = data['terrain']

@sio.on('player_joined')
def on_player_joined(data):
    players[data['id']] = data['player']

@sio.on('player_left')
def on_player_left(data):
    if data['id'] in players:
        players.pop(data['id'])

@sio.on('game_state')
def on_game_state(data):
    for pid, p in data['players'].items():
        players[pid] = p

# -----------------------
# Connect to server in separate thread
def connect_to_server():
    sio.connect(SERVER_URL)

threading.Thread(target=connect_to_server, daemon=True).start()

# -----------------------
# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((135, 206, 235))  # Sky blue

    # Draw terrain
    for i in range(len(terrain)-1):
        pygame.draw.line(screen, (34,139,34), terrain[i], terrain[i+1], 3)

    # Draw players
    for p in players.values():
        pygame.draw.rect(screen, p['color'], (p['x']%SCREEN_WIDTH, p['y'], 20, 20))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
