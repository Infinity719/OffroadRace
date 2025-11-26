import pygame, math, random, sys, threading, time
import socketio

# --------------------
# Config
SCREEN_WIDTH, SCREEN_HEIGHT = 900, 600
FPS = 60

SERVER_URL = "https://a9da330b-9744-400e-bfbd-f9e3a37b3155-00-qtjj697xlce0.spock.replit.dev"  # <--- Hier Server-URL eintragen

# Terrain
TERRAIN_LENGTH = 8000
TERRAIN_FREQ = 0.01
TERRAIN_AMPLITUDE = 120
TERRAIN_VARIANCE = 6
TERRAIN_START_HEIGHT = 380
TERRAIN_SEED = 12345

# Physics
GRAVITY = 0.6
FRICTION = 0.985
ACCEL = 0.45
BRAKE = 0.6
MAX_SPEED = 20
JUMP_FORCE = -11

# Colors
WHITE, BLACK, GREEN, SKY, YELLOW, RED, BLUE, DARK = (255,255,255),(0,0,0),(34,177,76),(135,206,235),(255,255,0),(200,30,30),(30,120,200),(20,20,20)

# --------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Hill Climb Racing - Multiplayer")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
large_font = pygame.font.SysFont(None, 48)

terrain = []

def generate_terrain():
    rng = random.Random(TERRAIN_SEED)
    t = []
    for x in range(TERRAIN_LENGTH):
        y = TERRAIN_START_HEIGHT + math.sin(x*TERRAIN_FREQ)*TERRAIN_AMPLITUDE + rng.randint(-TERRAIN_VARIANCE,TERRAIN_VARIANCE)
        t.append((x,int(y)))
    return t

terrain = generate_terrain()

# --------------------
class Car:
    def __init__(self,x,color=RED,nickname="Player"):
        self.x = float(x)
        self.y = float(terrain[int(x)][1]-30)
        self.vx = 0.0
        self.vy = 0.0
        self.w = 60
        self.h = 30
        self.color = color
        self.nickname = nickname
        self.on_ground = True
        self.distance = self.x
        self.angle = 0.0
    def physics_step(self,accel,brake,jump):
        if accel: self.vx+=ACCEL
        if brake: self.vx-=BRAKE
        self.vx*=FRICTION
        self.vx = max(min(self.vx,MAX_SPEED),-MAX_SPEED)
        self.vy+=GRAVITY
        self.x+=self.vx
        self.y+=self.vy
        if jump and self.on_ground:
            self.vy=JUMP_FORCE
            self.on_ground=False
        self.resolve_collision()
        if self.x>self.distance: self.distance=self.x
    def resolve_collision(self):
        ix=int(self.x)
        ix=max(0,min(ix,len(terrain)-2))
        x1,y1=terrain[ix];x2,y2=terrain[ix+1]
        t=(self.x-x1)/(x2-x1) if x2!=x1 else 0
        terrain_y=y1*(1-t)+y2*t
        bottom=self.y+self.h
        if bottom>=terrain_y:
            self.y=terrain_y-self.h
            self.vy=0
            self.on_ground=True
            self.angle=math.degrees(math.atan2(y2-y1,x2-x1))
        else:
            self.on_ground=False
    def draw(self,surf,offset_x):
        sx=int(self.x-offset_x)
        sy=int(self.y)
        pygame.draw.rect(surf,self.color,(sx,sy,self.w,self.h))
        wheel_y=sy+self.h
        pygame.draw.circle(surf,DARK,(int(sx+14),int(wheel_y)),9)
        pygame.draw.circle(surf,DARK,(int(sx+46),int(wheel_y)),9)
        shadow = pygame.Rect(sx+5,sy+self.h+8,self.w-10,6)
        pygame.draw.ellipse(surf,(0,0,0,50),shadow)

# --------------------
# Networking
sio = socketio.Client(reconnection=True)
network_players={}
your_id=None
connected_flag=False

def network_connect():
    global connected_flag
    try: sio.connect(SERVER_URL, wait=False)
    except: pass

@sio.event
def connect():
    global connected_flag
    connected_flag=True
    print("[Net] Connected")

@sio.event
def disconnect():
    global connected_flag
    connected_flag=False
    print("[Net] Disconnected")

@sio.on('init')
def on_init(data):
    global your_id, terrain
    your_id = data.get('your_id')
    server_terrain=data.get('terrain')
    if server_terrain: terrain[:]=server_terrain
    players=data.get('players')
    if players:
        for pid,st in players.items(): network_players[pid]=st

@sio.on('game_state')
def on_game_state(data):
    network_players.clear()
    for pid,st in data.get('players',{}).items(): network_players[pid]=st

@sio.on('player_joined')
def on_player_joined(data):
    pid=data.get('id');p=data.get('player')
    if pid and p: network_players[pid]=p

@sio.on('player_left')
def on_player_left(data):
    pid=data.get('id')
    if pid and pid in network_players: network_players.pop(pid)

def send_local_state(car):
    if not connected_flag: return
    try:
        sio.emit('player_update',{"x":car.x,"y":car.y,"vx":car.vx,"vy":car.vy,"distance":car.distance,"nickname":car.nickname,"color":car.color})
    except: pass

# --------------------
# Simple demo loop
def main():
    local_car=Car(100,color=RED,nickname="You")
    offset_x=0
    last_send=0
    send_interval=1/15
    while True:
        dt=clock.tick(FPS)/1000
        for event in pygame.event.get():
            if event.type==pygame.QUIT: sys.exit()
        keys=pygame.key.get_pressed()
        acc=keys[pygame.K_RIGHT]
        brk=keys[pygame.K_LEFT]
        jump=keys[pygame.K_UP]
        local_car.physics_step(acc,brk,jump)
        now=time.time()
        if now-last_send>=send_interval: send_local_state(local_car); last_send=now
        offset_x=local_car.x-220
        screen.fill(SKY)
        draw_terrain(offset_x)
        # draw other players
        for pid,st in network_players.items():
            if pid==sio.sid: continue
            col=tuple(st.get('color',(100,100,100)))
            pygame.draw.rect(screen,col,(int(st['x']-offset_x),int(st['y']),60,30))
        local_car.draw(screen,offset_x)
        pygame.display.flip()

def draw_terrain(offset_x):
    start_index=max(0,int(offset_x)-50)
    end_index=min(len(terrain)-1,int(offset_x+SCREEN_WIDTH)+50)
    pts=[(x-offset_x,y) for x,y in terrain[start_index:end_index+1]]
    if len(pts)>1:
        poly=[(pts[0][0],SCREEN_HEIGHT)]+pts+[(pts[-1][0],SCREEN_HEIGHT)]
        pygame.draw.polygon(screen,GREEN,poly)
        for i in range(len(pts)-1):
            pygame.draw.line(screen,(0,120,0),pts[i],pts[i+1],3)

if __name__=="__main__":
    threading.Thread(target=network_connect,daemon=True).start()
    main()