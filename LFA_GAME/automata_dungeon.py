import pygame
import sys
import math
import random
import re
from enum import Enum, auto
from collections import deque

from automata_graph_dfa import all_shortest_paths, bfs_path, all_simple_paths
from automata_validator import dfa, pda

GRID_W, GRID_H = 40, 30
TILE = 20
SIDEBAR_W = 400
SCREEN_W = GRID_W * TILE + SIDEBAR_W
SCREEN_H = GRID_H * TILE

WALL, FLOOR = 1, 0

C_BG       = (15, 15, 20)
C_PANEL    = (25, 25, 35)
C_WALL     = (60, 60, 80)
C_FLOOR    = (30, 30, 38)
C_TEXT     = (220, 220, 220)
C_TEXT_DIM = (140, 140, 150)
C_ACCENT   = (240, 200, 80)
C_HILITE   = (90, 180, 240)
C_PORTAL   = (200, 80, 220)
C_POTION   = (170, 110, 240)
C_GOAL     = (90, 220, 120)
C_START    = (180, 180, 220)
C_GOOD     = (90, 220, 120)
C_BAD      = (220, 80, 80)
C_GHOST_WANDER       = (100, 120, 220)
C_GHOST_CHASE        = (220, 60, 60)
C_GHOST_FRIGHTENED   = (30, 30, 160)
C_GHOST_FRIGHT_FLASH = (220, 220, 240)
C_GHOST_RETURN       = (180, 180, 200)
C_DOT                = (220, 200, 180)
C_POWER_PILL         = (255, 180, 60)
C_PACMAN             = (255, 220, 0)

_SYM_COLOR = {
    'a': (100, 200, 255),
    'b': (255, 160,  80),
}

def _clamp_rgb(c):
    return (max(0, min(255, int(c[0]))),
            max(0, min(255, int(c[1]))),
            max(0, min(255, int(c[2]))))

def tint(color, mul=1.0, add=0):
    return _clamp_rgb((color[0]*mul + add, color[1]*mul + add, color[2]*mul + add))

def _wrap_path_lines(font, path_str, max_w):

    segments = path_str.split(" -> ")
    lines = []
    current = segments[0]
    for seg in segments[1:]:
        candidate = current + " -> " + seg
        if font.size(candidate)[0] <= max_w:
            current = candidate
        else:
            lines.append(current)
            current = "  " + seg
    if current:
        lines.append(current)
    return lines

class CellularAutomataMap:

    def __init__(self, w, h, fill=0.45, iterations = 5, seed=None):
        rng = random.Random(seed); self.w, self.h = w, h
        self.grid = [[WALL if rng.random() < fill else FLOOR
                      for _ in range(w)] for _ in range(h)]
        for x in range(w): self.grid[0][x] = self.grid[h-1][x] = WALL
        for y in range(h): self.grid[y][0] = self.grid[y][w-1] = WALL
        for _ in range(iterations): self._step()

    def _wn(self, x, y):
        n = 0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.w and 0 <= ny < self.h:
                    if self.grid[ny][nx] == WALL: n += 1
                else: n += 1
        return n

    def _step(self):
        new = [r[:] for r in self.grid]
        for y in range(1, self.h-1):
            for x in range(1, self.w-1):
                new[y][x] = WALL if self._wn(x,y) >= 5 else FLOOR
        self.grid = new

    def is_floor(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and self.grid[y][x] == FLOOR

    def random_floor(self, rng=None):
        rng = rng or random
        for _ in range(2000):
            x = rng.randint(1, self.w-2); y = rng.randint(1, self.h-2)
            if self.grid[y][x] == FLOOR: return (x, y)
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] == FLOOR: return (x, y)
        return (1, 1)

    def floor_tiles(self):
        return [(x, y) for y in range(self.h) for x in range(self.w)
                if self.grid[y][x] == FLOOR]

    def largest_component(self):
        seen = set(); best = set()
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] != FLOOR or (x,y) in seen: continue
                comp = set(); q = deque([(x,y)])
                while q:
                    cx, cy = q.popleft()
                    if (cx,cy) in comp: continue
                    comp.add((cx,cy)); seen.add((cx,cy))
                    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        if self.is_floor(cx+dx, cy+dy) and (cx+dx,cy+dy) not in comp:
                            q.append((cx+dx, cy+dy))
                if len(comp) > len(best): best = comp
        return best

    def passage_width(self, x, y):
        if not self.is_floor(x, y): return 0
        hx = 1
        for dx in (1, -1):
            cx = x + dx
            while self.is_floor(cx, y):
                hx += 1; cx += dx
        vy = 1
        for dy in (1, -1):
            cy = y + dy
            while self.is_floor(x, cy):
                vy += 1; cy += dy
        return min(hx, vy)

    def reachable_from(self, start, blocked):
        seen = {start}; q = deque([start])
        while q:
            cx, cy = q.popleft()
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                n = (cx+dx, cy+dy)
                if n in seen or n in blocked: continue
                if not self.is_floor(*n): continue
                seen.add(n); q.append(n)
        return seen

class LSystem:
    def __init__(self, axiom, rules): self.axiom, self.rules = axiom, rules
    def derive(self, n):
        s = self.axiom
        for _ in range(n): s = "".join(self.rules.get(c, c) for c in s)
        return s

OAK_TREE        = LSystem("0", {"1": "11", "0": "1[0]0[0]0"})
CACTUS          = LSystem("0", {"1": "11", "0": "10[0]0"})
LICHEN          = LSystem("0", {"1": "1",  "0": "0[0]0"})
WILLOW          = LSystem("0", {"1": "11", "0": "1[0]1[0]0"})
PALM            = LSystem("0", {"1": "11", "0": "1[0]1[0]1"})
KELP            = LSystem("0", {"1": "11", "0": "10"})
OBSIDIAN_MOSS   = LSystem("0", {"1": "1",  "0": "0[0]0[0]"})
PINE            = LSystem("0", {"1": "11", "0": "1[0]1[0]0"})
TUMBLEWEED      = LSystem("0", {"1": "1",  "0": "1[0]0[0]1"})
ARCTIC_POPPY    = LSystem("0", {"1": "11", "0": "1[0]0"})
BIOLUM_MUSHROOM = LSystem("0", {"1": "1",  "0": "1[0]0"})
PETRI           = LSystem("0", {"1": "1",  "0": "0[0]0"})
IVY             = LSystem("0", {"1": "11", "0": "10[0]0"})
WITHERED_ROOT   = LSystem("0", {"1": "1",  "0": "1[0]0"})
FERN            = LSystem("0", {"1": "11", "0": "1[0]1[0]0"})
BAMBOO          = LSystem("0", {"1": "111","0": "10"})

BIOME_TYPES = [
    {"name": "Forest",    "color": (0, 140, 90),    "plant": "Oak",                   "ls": OAK_TREE,        "angle": 28, "len": 6.0},
    {"name": "Desert",    "color": (220, 190, 90),  "plant": "Cactus",                "ls": CACTUS,          "angle": 18, "len": 6.5},
    {"name": "Tundra",    "color": (120, 170, 220), "plant": "Lichen",                "ls": LICHEN,          "angle": 24, "len": 5.0},
    {"name": "Swamp",     "color": (100, 130, 70),  "plant": "Willow",                "ls": WILLOW,          "angle": 32, "len": 6.0},
    {"name": "Jungle",    "color": (0, 210, 90),    "plant": "Palm",                  "ls": PALM,            "angle": 20, "len": 7.0},
    {"name": "Ocean",     "color": (10, 40, 120),   "plant": "Kelp",                  "ls": KELP,            "angle": 12, "len": 7.5},
    {"name": "Volcano",   "color": (200, 60, 40),   "plant": "Obsidian Moss",         "ls": OBSIDIAN_MOSS,   "angle": 26, "len": 5.5},
    {"name": "Mountain",  "color": (110, 120, 130), "plant": "Pine",                  "ls": PINE,            "angle": 24, "len": 6.2},
    {"name": "Canyon",    "color": (190, 110, 60),  "plant": "Tumbleweed",            "ls": TUMBLEWEED,      "angle": 34, "len": 5.6},
    {"name": "Glacier",   "color": (100, 210, 210), "plant": "Arctic Poppy",          "ls": ARCTIC_POPPY,    "angle": 22, "len": 5.2},
    {"name": "Cave",      "color": (50, 30, 70),    "plant": "Bioluminescent Mushroom","ls": BIOLUM_MUSHROOM, "angle": 28, "len": 4.8},
    {"name": "Lab",       "color": (230, 230, 235), "plant": "Petri Dish Culture",    "ls": PETRI,           "angle": 18, "len": 4.6},
    {"name": "Core",      "color": (240, 210, 80),  "plant": "Ivy",                   "ls": IVY,             "angle": 26, "len": 5.4},
    {"name": "Void",      "color": (80, 50, 120),   "plant": "Withered Root",         "ls": WITHERED_ROOT,   "angle": 20, "len": 5.0},
    {"name": "Zone",      "color": (220, 60, 210),  "plant": "Fern",                  "ls": FERN,            "angle": 30, "len": 5.6},
    {"name": "Grid",      "color": (0, 190, 90),    "plant": "Bamboo",                "ls": BAMBOO,          "angle": 12, "len": 7.0},
]

def choose_biome(rng):
    return rng.choice(BIOME_TYPES)

class Tree:
    def __init__(self, base_px, base_py, lsystem, trunk_color, leaf_color,
                 iterations=5, segment_len=6.0, angle_deg=45.0, start_heading=-90.0):
        self.string = lsystem.derive(iterations)
        self.segments = []; self.leaves = []; self.footprint = set()
        self.trunk_color = trunk_color
        self.leaf_color = leaf_color
        self._render(base_px, base_py, start_heading, segment_len,
                     math.radians(angle_deg))

    def _record(self, px, py):
        gx, gy = int(px//TILE), int(py//TILE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            self.footprint.add((gx, gy))

    def _render(self, x, y, heading_deg, length, angle):
        heading = math.radians(heading_deg); stack = []
        for ch in self.string:
            if ch in "01":
                nx = x + math.cos(heading)*length
                ny = y + math.sin(heading)*length
                self.segments.append((x, y, nx, ny, ch == "0"))
                self._record(x, y); self._record(nx, ny)
                if ch == "0": self.leaves.append((nx, ny))
                x, y = nx, ny
            elif ch == "[":
                stack.append((x, y, heading, length))
                heading -= angle; length /= 1.25
            elif ch == "]":
                if stack: x, y, heading, length = stack.pop()
                heading += angle

class ForestPlanner:
    def __init__(self, ca_map, reserved_tiles=None, anchor_tiles=None,
                 target_count=8, seed=None, plant_profile=None):
        self.ca = ca_map
        self.reserved = set(reserved_tiles or [])
        self.anchors = list(anchor_tiles or [])
        self.rng = random.Random(seed)
        self.target = target_count
        self.plant_profile = plant_profile or BIOME_TYPES[0]
        self.trees = []
        self.blocked = set()
        self.trunk_positions = set()
        self._density = self._build_density_field()
        self._clearings = self._pick_clearings()
        self._plant_all()

    def _build_density_field(self):
        D = [[0.0]*self.ca.w for _ in range(self.ca.h)]
        for y in range(self.ca.h):
            for x in range(self.ca.w):
                if not self.ca.is_floor(x, y):
                    continue
                walls = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0: continue
                        nx, ny = x+dx, y+dy
                        if not self.ca.is_floor(nx, ny):
                            walls += 1
                        D[y][x] = walls / 8.0
        return D

    def _pick_clearings(self):
        opens = [(x, y) for y in range(self.ca.h) for x in range(self.ca.w)
                 if self._density[y][x] < 0.25 and self.ca.is_floor(x, y)]
        self.rng.shuffle(opens)
        clearings = []
        for c in opens:
            if all(abs(c[0]-d[0]) + abs(c[1]-d[1]) > 6 for d in clearings):
                clearings.append(c)
            if len(clearings) >= 3:
                break
        return clearings

    def _near_clearing(self, x, y, radius=3):
        for cx, cy in self._clearings:
            if abs(x-cx) + abs(y-cy) <= radius:
                return True
        return False

    def _candidate_pool(self):
        pool = []
        for y in range(self.ca.h):
            for x in range(self.ca.w):
                if not self.ca.is_floor(x, y): continue
                if (x, y) in self.reserved: continue
                if (x, y) in self.trunk_positions: continue
                if self.ca.passage_width(x, y) <= 1: continue
                if y > 0 and not self.ca.is_floor(x, y-1): continue
                if self._near_clearing(x, y, radius=2): continue
                weight = 0.2 + self._density[y][x]
                pool.append(((x, y), weight))
        return pool

    def _weighted_pick(self, pool):
        total = sum(w for _, w in pool)
        if total <= 0: return None
        r = self.rng.uniform(0, total); cum = 0
        for tile, w in pool:
            cum += w
            if r <= cum:
                return tile
        return pool[-1][0]

    def _plant_all(self):
        pool = self._candidate_pool()
        tries = 0
        budget = max(60, self.target * 12)
        while len(self.trees) < self.target and tries < budget:
            tries += 1
            tile = self._weighted_pick(pool)
            if tile is None: break
            tx, ty = tile
            trunk_color = tint(self.plant_profile["color"], mul=0.35)
            leaf_color = tint(self.plant_profile["color"], mul=1.1, add=10)
            tree = Tree(
                tx*TILE + TILE//2, ty*TILE + TILE - 1,
                lsystem=self.plant_profile["ls"],
                trunk_color=trunk_color,
                leaf_color=leaf_color,
                iterations=self.rng.choice([4, 4, 5]),
                segment_len=self.rng.uniform(self.plant_profile["len"]*0.85,
                                             self.plant_profile["len"]*1.15),
                angle_deg=self.rng.uniform(self.plant_profile["angle"]*0.85,
                                           self.plant_profile["angle"]*1.15),
            )
            footprint = tree.footprint
            touches_wall_or_outside = False
            for (fx, fy) in footprint:
                if not (0 <= fx < self.ca.w and 0 <= fy < self.ca.h):
                    touches_wall_or_outside = True; break
                if not self.ca.is_floor(fx, fy):
                    touches_wall_or_outside = True; break
            if touches_wall_or_outside: continue
            if footprint & self.reserved: continue
            if footprint & self.blocked:  continue
            if tile in self.trunk_positions: continue
            if any(self.ca.passage_width(x, y) <= 1 for (x, y) in footprint):
                continue
            new_blocked = self.blocked | footprint
            if not self._anchors_still_connected(new_blocked):
                continue
            self.trees.append(tree)
            self.blocked = new_blocked
            self.trunk_positions.add(tile)
            pool = [(t, w) for (t, w) in pool if t != tile]

    def _anchors_still_connected(self, blocked):
        if len(self.anchors) < 2: return True
        start = self.anchors[0]
        if not self.ca.is_floor(*start) or start in blocked:
            return False
        seen = self.ca.reachable_from(start, blocked)
        return all(a in seen for a in self.anchors)

    def draw(self, screen):
        for t in self.trees:
            for (x1, y1, x2, y2, _) in t.segments:
                pygame.draw.line(screen, t.trunk_color, (x1, y1), (x2, y2), 2)
            for (lx, ly) in t.leaves:
                pygame.draw.circle(screen, t.leaf_color, (int(lx), int(ly)), 2)

class GhostPFSM:
    def __init__(self, rng):
        self.rng = rng
        self.state = "WANDER"
        self._transitions = {
            ("WANDER",     "player_near"):    [("CHASE", 0.85), ("WANDER", 0.15)],
            ("WANDER",     "player_far"):     "WANDER",
            ("WANDER",     "power_pill"):     "FRIGHTENED",
            ("CHASE",      "player_near"):    "CHASE",
            ("CHASE",      "player_far"):     [("WANDER", 0.70), ("CHASE", 0.30)],
            ("CHASE",      "power_pill"):     "FRIGHTENED",
            ("FRIGHTENED", "touched_player"): "RETURN",
            ("FRIGHTENED", "pill_expired"):   "WANDER",
            ("FRIGHTENED", "player_far"):     [("WANDER", 0.55), ("FRIGHTENED", 0.45)],
            ("RETURN",     "at_base"):        "WANDER",
        }

    def step(self, event):
        key = (self.state, event)
        target = self._transitions.get(key)
        if target is None:
            return self.state
        if isinstance(target, list):
            r = self.rng.random()
            acc = 0.0
            for s, p in target:
                acc += p
                if r <= acc:
                    self.state = s
                    return self.state
            self.state = target[-1][0]
        else:
            self.state = target
        return self.state

class Ghost:
    _COLORS = {
        "WANDER":     C_GHOST_WANDER,
        "CHASE":      C_GHOST_CHASE,
        "FRIGHTENED": C_GHOST_FRIGHTENED,
        "RETURN":     C_GHOST_RETURN,
    }
    _MOVE_INTERVAL = {"WANDER": 10, "CHASE": 7, "FRIGHTENED": 12, "RETURN": 5}

    def __init__(self, room_id, x, y, rng, start_room_id):
        self.room_id = room_id
        self.x = x
        self.y = y
        self.rng = rng
        self.start_room_id = start_room_id
        self.controller = GhostPFSM(rng)
        self.frightened_frames = 0
        self._flash = False
        self._move_timer = 0
        self._prev_pos = None

    @property
    def state(self):
        return self.controller.state

    def color(self):
        if self.state == "FRIGHTENED":
            return C_GHOST_FRIGHT_FLASH if self._flash else C_GHOST_FRIGHTENED
        return self._COLORS.get(self.state, C_GHOST_RETURN)

    def activate_frightened(self, frames=300):
        self.controller.state = "FRIGHTENED"
        self.frightened_frames = frames

    def update(self, graph_nodes, player_room_id, player_x, player_y, power_pill_active):
        events = []
        if power_pill_active and self.state != "FRIGHTENED":
            events.append("power_pill")
        if self.state == "FRIGHTENED":
            self.frightened_frames -= 1
            self._flash = self.frightened_frames < 120 and (self.frightened_frames // 10) % 2 == 0
            if self.frightened_frames <= 0:
                events.append("pill_expired")
        else:
            if self.room_id == player_room_id:
                dist = abs(self.x - player_x) + abs(self.y - player_y)
                events.append("player_near" if dist <= 6 else "player_far")
            else:
                events.append("player_far")
        if self.state == "RETURN" and self.room_id == self.start_room_id:
            spawn = graph_nodes[self.start_room_id].spawn
            if (self.x, self.y) == spawn:
                events.append("at_base")
        for ev in events:
            prev = self.controller.state
            self.controller.step(ev)
            if self.controller.state != prev:
                if self.controller.state == "FRIGHTENED":
                    self.frightened_frames = 300
                break
        self._move_timer += 1
        if self._move_timer >= self._MOVE_INTERVAL.get(self.state, 10):
            self._move_timer = 0
            self._do_move(graph_nodes, player_room_id, (player_x, player_y))

    def _do_move(self, graph_nodes, player_room_id, player_pos):
        room = graph_nodes[self.room_id]
        s = self.state
        if s == "WANDER":
            self._step_wander(room)
        elif s == "CHASE":
            if self.room_id == player_room_id:
                self._step_toward(room, player_pos)
            else:
                self._step_toward_portal(room, player_room_id, graph_nodes)
        elif s == "FRIGHTENED":
            if self.room_id == player_room_id:
                self._step_away(room, player_pos)
            else:
                self._step_random(room)
        elif s == "RETURN":
            if self.room_id == self.start_room_id:
                spawn = graph_nodes[self.start_room_id].spawn
                self._step_toward(room, spawn)
            else:
                self._step_toward_portal(room, self.start_room_id, graph_nodes)

    def _step_random(self, room):
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]
        self.rng.shuffle(dirs)
        for d in dirs:
            if self._try_move(room, d[0], d[1]):
                return

    def _step_wander(self, room):
        preferred, fallback = [], []
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = self.x + dx, self.y + dy
            if self._prev_pos and (nx, ny) == self._prev_pos:
                fallback.append((dx, dy))
            else:
                preferred.append((dx, dy))
        self.rng.shuffle(preferred)
        self.rng.shuffle(fallback)
        for dx, dy in preferred + fallback:
            if self._try_move(room, dx, dy):
                return

    def _step_toward(self, room, target):
        tx, ty = target
        dirs = sorted([(1,0),(-1,0),(0,1),(0,-1)],
                      key=lambda d: abs(self.x + d[0] - tx) + abs(self.y + d[1] - ty))
        for dx, dy in dirs:
            if self._try_move(room, dx, dy):
                return

    def _step_away(self, room, target):
        tx, ty = target
        dirs = sorted([(1,0),(-1,0),(0,1),(0,-1)],
                      key=lambda d: -(abs(self.x + d[0] - tx) + abs(self.y + d[1] - ty)))
        for dx, dy in dirs:
            if self._try_move(room, dx, dy):
                return

    def _step_toward_portal(self, room, target_room_id, graph_nodes):
        dist = {target_room_id: 0}
        q = deque([target_room_id])
        while q:
            nid = q.popleft()
            for _, (dest_id, _, _, _) in graph_nodes[nid].portals_to.items():
                if dest_id not in dist:
                    dist[dest_id] = dist[nid] + 1
                    q.append(dest_id)
        best_tile, best_d = None, 10**9
        for tile, (dest_id, _, _, _) in room.portals_to.items():
            d = dist.get(dest_id, 10**9)
            if d < best_d:
                best_d, best_tile = d, tile
        if best_tile:
            self._step_toward(room, best_tile)
        else:
            self._step_random(room)

    def _try_move(self, room, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if not room.ca.is_floor(nx, ny):
            return False
        if (nx, ny) in room.forest.blocked:
            return False
        if (nx, ny) in room.portals_to:
            if self.state == "RETURN":
                dest_id, dest_tile, _, _ = room.portals_to[(nx, ny)]
                self.room_id = dest_id
                self._prev_pos = None
                self.x, self.y = dest_tile
                return True
            return False
        self._prev_pos = (self.x, self.y)
        self.x, self.y = nx, ny
        return True

class RoomNode:
    _next_id = 0
    def __init__(self, type_):
        self.id = RoomNode._next_id; RoomNode._next_id += 1
        self.type = type_
        self.biome = None
        self.ca = None; self.forest = None
        self.spawn = None
        self.portals_to = {}
        self.mx = 0.0; self.my = 0.0
        self.room_number = None
        self.dots = set()
        self.power_pill_tile = None

class RoomGraph:
    def __init__(self, max_iters=12, min_nodes=4, seed=None):
        RoomNode._next_id = 0
        self.rng = random.Random(seed)
        start = RoomNode("START")
        end = RoomNode("END")
        self.nodes = {start.id: start, end.id: end}
        self.edges = set(); self.edge_types = {}
        self.history = []
        self.start_id = start.id
        self.end_id = end.id
        self._add_edge(start.id, end.id, "normal")
        self._derive(max_iters, min_nodes)
        self._assign_room_numbers()
        self._layout()

    def _add_edge(self, a, b, kind="normal"):
        if a == b: return
        e = frozenset((a, b))
        self.edges.add(e); self.edge_types[e] = kind

    def _neighbors(self, nid):
        return [next(iter(e - {nid})) for e in self.edges if nid in e]

    def _find_all_edges(self):
        return list(self.edges)

    def _find_all_triangles(self):
        triangles = []
        ids = list(self.nodes.keys())
        neighbors = {nid: set(self._neighbors(nid)) for nid in ids}
        for i in range(len(ids)):
            a = ids[i]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                if b not in neighbors[a]: continue
                for k in range(j + 1, len(ids)):
                    c = ids[k]
                    if c in neighbors[a] and c in neighbors[b]:
                        triangles.append((a, b, c))
        return triangles

    def _replace_edge_with_line(self, edge):
        a_id, b_id = tuple(edge)
        kind = self.edge_types.get(edge, "normal")
        self.edges.discard(edge); self.edge_types.pop(edge, None)
        z = RoomNode("ROOM"); self.nodes[z.id] = z
        self._add_edge(a_id, z.id, kind)
        self._add_edge(z.id, b_id, kind)
        return [z.id]

    def _replace_edge_with_triangle(self, edge):
        a_id, b_id = tuple(edge)
        kind = self.edge_types.get(edge, "normal")
        z = RoomNode("ROOM"); self.nodes[z.id] = z
        self._add_edge(a_id, z.id, kind)
        self._add_edge(z.id, b_id, kind)
        return [z.id]

    def _upgrade_triangle_to_square(self, tri):
        a_id, b_id, c_id = tri
        edges = [frozenset((a_id, b_id)), frozenset((b_id, c_id)), frozenset((a_id, c_id))]
        remove_edge = self.rng.choice(edges)
        y_id, z_id = tuple(remove_edge)
        kind = self.edge_types.get(remove_edge, "normal")
        self.edges.discard(remove_edge); self.edge_types.pop(remove_edge, None)
        w = RoomNode("ROOM"); self.nodes[w.id] = w
        self._add_edge(y_id, w.id, kind)
        self._add_edge(w.id, z_id, kind)
        return [w.id], (y_id, z_id)

    def _derive(self, max_iters, min_nodes):
        for _ in range(max_iters):
            edges = self._find_all_edges()
            triangles = self._find_all_triangles()
            if not edges: break
            if triangles and self.rng.random() < 0.5:
                tri = self.rng.choice(triangles)
                created, removed_edge = self._upgrade_triangle_to_square(tri)
                self.history.append(("triangle_to_square", list(tri), created, list(removed_edge)))
                continue
            edge = self.rng.choice(edges)
            if self.rng.random() < 0.60:
                created = self._replace_edge_with_line(edge)
                self.history.append(("edge_to_line", list(edge), created))
            else:
                created = self._replace_edge_with_triangle(edge)
                self.history.append(("edge_to_triangle", list(edge), created))

    def _assign_room_numbers(self):
        num = 1
        for nid in sorted(self.nodes.keys()):
            node = self.nodes[nid]
            if node.type == "ROOM":
                node.room_number = num
                num += 1

    def _node_label(self, nid):
        node = self.nodes.get(nid)
        if not node: return f"?{nid}"
        return room_label(node)

    def audit_log_lines(self, limit=8):
        lines = []
        start_idx = max(0, len(self.history) - limit)
        for i, entry in enumerate(self.history[start_idx:], start=start_idx + 1):
            rule = entry[0]
            if rule == "edge_to_line":
                a_id, b_id = entry[1]; z_id = entry[2][0]
                a = self._node_label(a_id); b = self._node_label(b_id); z = self._node_label(z_id)
                lines.append(f"{i}. line: {a}--{b} -> {a}--{z}--{b}")
            elif rule == "edge_to_triangle":
                a_id, b_id = entry[1]; z_id = entry[2][0]
                a = self._node_label(a_id); b = self._node_label(b_id); z = self._node_label(z_id)
                lines.append(f"{i}. tri: {a}--{b} + {a}--{z} + {z}--{b}")
            elif rule == "triangle_to_square":
                a_id, b_id, c_id = entry[1]; w_id = entry[2][0]; y_id, z_id = entry[3]
                a = self._node_label(a_id); b = self._node_label(b_id); c = self._node_label(c_id)
                w = self._node_label(w_id); y = self._node_label(y_id); z = self._node_label(z_id)
                lines.append(f"{i}. square: {a}-{b}-{c} -> insert {w} on {y}-{z}")
        return lines

    def _bfs_ids(self, start):
        d = {start: 0}; q = deque([start])
        while q:
            u = q.popleft()
            for v in self._neighbors(u):
                if v not in d:
                    d[v] = d[u] + 1; q.append(v)
        return d

    def _layout(self):
        ids = list(self.nodes.keys()); n = len(ids)
        for i, nid in enumerate(ids):
            ang = 2*math.pi*i/max(1,n)
            self.nodes[nid].mx = math.cos(ang); self.nodes[nid].my = math.sin(ang)
        for _ in range(80):
            forces = {nid: [0.0, 0.0] for nid in ids}
            for i in range(n):
                for j in range(i+1, n):
                    a, b = self.nodes[ids[i]], self.nodes[ids[j]]
                    dx, dy = a.mx - b.mx, a.my - b.my
                    d2 = dx*dx + dy*dy + 0.01; f = 0.04/d2
                    forces[a.id][0] += dx*f; forces[a.id][1] += dy*f
                    forces[b.id][0] -= dx*f; forces[b.id][1] -= dy*f
            for e in self.edges:
                a_id, b_id = tuple(e)
                a, b = self.nodes[a_id], self.nodes[b_id]
                dx, dy = b.mx - a.mx, b.my - a.my
                forces[a.id][0] += dx*0.05; forces[a.id][1] += dy*0.05
                forces[b.id][0] -= dx*0.05; forces[b.id][1] -= dy*0.05
            for nid in ids:
                n_ = self.nodes[nid]; fx, fy = forces[nid]
                n_.mx += fx - n_.mx*0.01; n_.my += fy - n_.my*0.01

def room_label(node):
    if node.type == "START": return "start"
    if node.type == "END": return "end"
    num = node.room_number if node.room_number is not None else node.id
    return f"room{num}"

class World:
    def __init__(self, max_iters=12, min_nodes=4, seed=None, tree_count=8):
        self.graph = RoomGraph(max_iters=max_iters, min_nodes=min_nodes, seed=seed)
        self.rng = random.Random(seed)
        self.tree_count = tree_count
        self.ghosts = []
        for node in self.graph.nodes.values():
            self._make_room_ca(node)
        self._place_portal_tiles()
        self._grow_forests()
        self._populate_dots()
        self._place_power_pills()
        self._spawn_ghosts()
        start = self.graph.nodes[self.graph.start_id]
        self.current_room_id = start.id
        self.player_x, self.player_y = start.spawn

    def _make_room_ca(self, node):
        if node.biome is None:
            node.biome = choose_biome(self.rng)
        node.ca = CellularAutomataMap(GRID_W, GRID_H, seed=self.rng.randint(0, 1<<30))
        comp = node.ca.largest_component() or set(node.ca.floor_tiles())
        if comp:
            cx = sum(p[0] for p in comp) / len(comp)
            cy = sum(p[1] for p in comp) / len(comp)
            spawn = min(comp, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
        else:
            spawn = node.ca.random_floor(self.rng)
        node.spawn = spawn

    def _place_portal_tiles(self):
        for edge in self.graph.edges:
            node_ids = list(edge)
            if len(node_ids) != 2: continue
            id_a, id_b = node_ids
            node_a = self.graph.nodes[id_a]
            node_b = self.graph.nodes[id_b]
            tile_a = self._pick_special_tile(node_a, preferred_side=self._side_toward(node_a, node_b))
            tile_b = self._pick_special_tile(node_b, preferred_side=self._side_toward(node_b, node_a))
            label_b = room_label(node_b)
            label_a = room_label(node_a)
            node_a.portals_to[tile_a] = (id_b, tile_b, node_b.type, label_b)
            node_b.portals_to[tile_b] = (id_a, tile_a, node_a.type, label_a)

    def _used_special_tiles(self, node):
        return {node.spawn} | set(node.portals_to.keys())

    def _side_toward(self, node, other):
        dx = other.mx - node.mx
        dy = other.my - node.my
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        return "bottom" if dy >= 0 else "top"

    def _pick_special_tile(self, node, min_dist=6, preferred_side=None):
        comp = node.ca.largest_component()
        used = self._used_special_tiles(node)
        cands = []
        for c in comp:
            if c in used: continue
            ok = True
            for u in used:
                if abs(c[0]-u[0]) + abs(c[1]-u[1]) < min_dist:
                    ok = False; break
            if ok:
                cands.append(c)
        if not cands:
            cands = [c for c in comp if c not in used]
        if not cands:
            return node.spawn
        if preferred_side:
            margin = 3
            side_cands = []
            for x, y in cands:
                if preferred_side == "left" and x <= margin:
                    side_cands.append((x, y))
                elif preferred_side == "right" and x >= node.ca.w - 1 - margin:
                    side_cands.append((x, y))
                elif preferred_side == "top" and y <= margin:
                    side_cands.append((x, y))
                elif preferred_side == "bottom" and y >= node.ca.h - 1 - margin:
                    side_cands.append((x, y))
            if side_cands:
                cands = side_cands
        sx, sy = node.spawn
        cands.sort(key=lambda p: -((p[0]-sx)**2 + (p[1]-sy)**2))
        cut = max(1, len(cands) // 3)
        return self.rng.choice(cands[:cut])

    def _grow_forests(self):
        for node in self.graph.nodes.values():
            specials = self._used_special_tiles(node)
            buffered = set(specials)
            for (x, y) in specials:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        buffered.add((x+dx, y+dy))
            anchors = [node.spawn] + [t for t in specials if t != node.spawn]
            node.forest = ForestPlanner(
                node.ca, reserved_tiles=buffered, anchor_tiles=anchors,
                target_count=self.tree_count,
                seed=self.rng.randint(0, 1<<30),
                plant_profile=node.biome,
            )

    def _populate_dots(self):
        for node in self.graph.nodes.values():
            comp = node.ca.largest_component() or set(node.ca.floor_tiles())
            blocked = node.forest.blocked if node.forest else set()
            special = self._used_special_tiles(node)
            node.dots = {t for t in comp if t not in blocked and t not in special}

    def _place_power_pills(self):
        for node in self.graph.nodes.values():
            if node.type != "ROOM": continue
            special = self._used_special_tiles(node)
            cands = [t for t in node.dots if t not in special]
            if cands:
                pill = self.rng.choice(cands)
                node.power_pill_tile = pill
                node.dots.discard(pill)

    def _spawn_ghosts(self):
        for node in self.graph.nodes.values():
            used = self._used_special_tiles(node)
            blocked = node.forest.blocked if node.forest else set()
            comp = node.ca.largest_component() or set(node.ca.floor_tiles())
            cands = [c for c in comp if c not in used and c not in blocked]
            self.rng.shuffle(cands)
            for tile in cands[:2]:
                g = Ghost(node.id, tile[0], tile[1], self.rng, self.graph.start_id)
                self.ghosts.append(g)

    def current_room(self):
        return self.graph.nodes[self.current_room_id]

    def passable(self, x, y):
        r = self.current_room()
        if not r.ca.is_floor(x, y): return False
        if (x, y) in r.forest.blocked: return False
        return True

    def step_player(self, dx, dy, on_event=None):
        nx, ny = self.player_x + dx, self.player_y + dy
        if not self.passable(nx, ny): return False
        self.player_x, self.player_y = nx, ny
        r = self.current_room()
        if (nx, ny) in r.portals_to:
            dest_id, dest_tile, dest_type, _ = r.portals_to[(nx, ny)]
            self.current_room_id = dest_id
            self.player_x, self.player_y = dest_tile
            if on_event: on_event(("portal", dest_id, dest_type))
        return True

class Level:
    name = "Level"
    description = ""
    GRAPH_ITERS = 10
    MIN_NODES = 4
    TREE_COUNT = 6

    def __init__(self):
        self.world = World(max_iters=self.GRAPH_ITERS, min_nodes=self.MIN_NODES,
                           tree_count=self.TREE_COUNT)
        self.hp = 20
        self.score = 0
        self.won = False
        self._pacman_frame = 0
        self._pacman_dir = (1, 0)
        self._power_pill_frames = 0
        graph = self.world.graph
        self._all_paths = all_shortest_paths(graph._neighbors, graph.start_id, graph.end_id)
        self._path_set = {tuple(p) for p in self._all_paths}
        self._traversal = [graph.start_id]
        self._word_sequence = []
        self._post_init()
        self._write_level_config()

    def _post_init(self):
        pass

    def _write_level_config(self):
        graph = self.world.graph
        nodes = graph.nodes
        states = [room_label(nodes[nid]) for nid in sorted(nodes.keys())]
        sigma = ["p" + lbl for lbl in states]
        start_lbl = room_label(nodes[graph.start_id])
        accept_lbl = room_label(nodes[graph.end_id])
        sp_edges = set()
        for path in self._all_paths:
            for i in range(len(path) - 1):
                sp_edges.add((path[i], path[i + 1]))
        trans = []
        for (a_id, b_id) in sp_edges:
            a_lbl = room_label(nodes[a_id])
            b_lbl = room_label(nodes[b_id])
            trans.append(f"{a_lbl}, p{b_lbl}, {b_lbl}")
        trans.sort()
        audit = graph.audit_log_lines(limit=200)
        lines = (
            ["[Sigma]"] + sigma + ["[Stop]",
             "[States]"] + states + ["[Stop]",
             "[Start]", start_lbl, "[Stop]",
             "[Accept]", accept_lbl, "[Stop]",
             "[Transitions]"] + trans + ["[Stop]", "",
             "[AuditLog]"] + audit + ["[Stop]", ""]
        )
        with open("configDFA.txt", "w") as f:
            f.write("\n".join(lines))

    def _append_traversal_log(self, accepted):
        graph = self.world.graph
        nodes = graph.nodes
        trav_str = " -> ".join(room_label(nodes[rid]) for rid in self._traversal)
        result = "ACCEPTED (shortest path)" if accepted else "REJECTED (not shortest path)"
        with open("configDFA.txt", "a") as f:
            f.write("\n".join(["[TraversalLog]", trav_str, f"Result: {result}", "[Stop]", ""]))

    def on_event(self, ev):
        if ev[0] == "portal":
            dest_id = ev[1]
            self._traversal.append(dest_id)
            nodes = self.world.graph.nodes
            self._word_sequence.append("p" + room_label(nodes[dest_id]))
            if dest_id == self.world.graph.end_id:
                result = dfa(self._word_sequence)
                if result == "acceptat":
                    self.won = True
                    self._append_traversal_log(accepted=True)
                else:
                    self.hp = 0
                    self._append_traversal_log(accepted=False)

    def is_won(self): return self.won
    def is_lost(self): return self.hp <= 0

    def draw_hud(self, screen, font, font_big):
        graph = self.world.graph
        nodes = graph.nodes
        x0 = GRID_W * TILE + 12
        max_w = SIDEBAR_W - 24
        y = 50

        screen.blit(font.render(f"Score: {self.score}", True, C_ACCENT), (x0, y))
        y += 18
        room = self.world.current_room()
        biome_name = room.biome["name"] if room.biome else "Unknown"
        biome_color = tint(room.biome["color"], mul=1.05, add=10) if room.biome else C_TEXT_DIM
        screen.blit(font.render(f"Biome: {biome_name}", True, biome_color), (x0, y))
        y += 18
        goal_lbl = room_label(nodes[graph.end_id])
        screen.blit(font.render(f"Goal: {goal_lbl}", True, C_GOAL), (x0, y))
        y += 18
        cur_lbl = room_label(nodes[self.world.current_room_id])
        screen.blit(font.render(f"Current: {cur_lbl}", True, C_TEXT), (x0, y))
        y += 20
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1)
        y += 8

        screen.blit(font.render("Navigate from start to end", True, C_TEXT_DIM), (x0, y))
        y += 16
        screen.blit(font.render("via the shortest path.", True, C_TEXT_DIM), (x0, y))
        y += 22

        screen.blit(font.render("Shortest Path Routes:", True, C_ACCENT), (x0, y))
        y += 18
        if self._all_paths:
            for path in self._all_paths:
                path_str = " -> ".join(room_label(nodes[rid]) for rid in path)
                for line in _wrap_path_lines(font, path_str, max_w):
                    screen.blit(font.render(line, True, C_HILITE), (x0, y))
                    y += 15
                y += 4
        else:
            screen.blit(font.render("(no path found)", True, C_BAD), (x0, y))
            y += 15
        y += 4
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1)
        y += 8

        screen.blit(font.render("Your path:", True, C_ACCENT), (x0, y))
        y += 16
        trav_str = " -> ".join(room_label(nodes[rid]) for rid in self._traversal)
        for line in _wrap_path_lines(font, trav_str, max_w):
            screen.blit(font.render(line, True, C_TEXT), (x0, y))
            y += 15

        screen.blit(font.render("WASD  M map  R restart  Esc menu", True, C_TEXT_DIM),
                    (x0, SCREEN_H - 28))

    def _collect_dots(self):
        room = self.world.current_room()
        pos = (self.world.player_x, self.world.player_y)
        if pos in room.dots:
            room.dots.discard(pos)
            self.score += 10

    def _check_power_pill(self):
        room = self.world.current_room()
        pos = (self.world.player_x, self.world.player_y)
        if room.power_pill_tile == pos:
            room.power_pill_tile = None
            self._power_pill_frames = 300
            self.score += 50
            for g in self.world.ghosts:
                g.activate_frightened(300)

    def try_move(self, dx, dy):
        if dx != 0 or dy != 0:
            self._pacman_dir = (dx, dy)
        self.world.step_player(dx, dy, on_event=self.on_event)
        if not self.is_won() and not self.is_lost():
            self._collect_dots()
            self._check_power_pill()

    def try_scan(self):
        pass

    def draw_world(self, screen):
        r = self.world.current_room()
        floor_color = tint(r.biome["color"], mul=0.35, add=10) if r.biome else C_FLOOR
        wall_color = tint(r.biome["color"], mul=0.18) if r.biome else C_WALL
        for y in range(GRID_H):
            for x in range(GRID_W):
                rect = pygame.Rect(x*TILE, y*TILE, TILE, TILE)
                if r.ca.grid[y][x] == WALL:
                    pygame.draw.rect(screen, wall_color, rect)
                else:
                    pygame.draw.rect(screen, floor_color, rect)
        for (dx, dy) in r.dots:
            pygame.draw.circle(screen, C_DOT,
                               (dx*TILE + TILE//2, dy*TILE + TILE//2), 3)
        if r.power_pill_tile:
            ppx, ppy = r.power_pill_tile
            pygame.draw.circle(screen, C_POWER_PILL,
                               (ppx*TILE + TILE//2, ppy*TILE + TILE//2), 6)
        if r.type == "START":
            self._mark(screen, r.spawn, C_START, "S")
        if r.type == "END":
            self._mark(screen, r.spawn, C_GOAL, "E")
        badge_font = pygame.font.SysFont("consolas", 8, bold=True)
        for (px, py), (dest_id, _, dest_type, label) in r.portals_to.items():
            self._mark(screen, (px, py), C_PORTAL, label)
            t = badge_font.render(label, True, (20, 20, 25))
            badge = pygame.Rect(px*TILE + 1, py*TILE + TILE - 12, t.get_width() + 4, t.get_height() + 2)
            pygame.draw.rect(screen, (245, 235, 255), badge)
            pygame.draw.rect(screen, C_PORTAL, badge, 1)
            screen.blit(t, (badge.x + 2, badge.y + 1))
        r.forest.draw(screen)
        self._draw_ghosts(screen)
        self._draw_pacman(screen)

    def update(self):
        if self.is_won() or self.is_lost():
            return
        power_active = self._power_pill_frames > 0
        if power_active:
            self._power_pill_frames -= 1
        player_room_id = self.world.current_room_id
        px, py = self.world.player_x, self.world.player_y
        for g in self.world.ghosts:
            g.update(self.world.graph.nodes, player_room_id, px, py, power_active)
            if g.room_id == player_room_id and g.x == px and g.y == py:
                if g.state == "FRIGHTENED":
                    g.controller.step("touched_player")
                    self.score += 200
                elif g.state in ("WANDER", "CHASE"):
                    self.hp = 0
                    return

    def _draw_pacman(self, screen):
        self._pacman_frame = (self._pacman_frame + 1) % 32
        cx = self.world.player_x * TILE + TILE // 2
        cy = self.world.player_y * TILE + TILE // 2
        r = TILE // 2 - 2
        frame = (self._pacman_frame // 4) % 8
        mouth_deg = frame * 5 if frame < 4 else (7 - frame) * 5
        dir_map = {(1, 0): 0, (-1, 0): 180, (0, 1): 90, (0, -1): 270}
        base_deg = dir_map.get(self._pacman_dir, 0)
        base = math.radians(base_deg)
        half = math.radians(max(mouth_deg, 3))
        pts = [(cx, cy)]
        steps = 24
        for i in range(steps + 1):
            angle = (base + half) + (2 * math.pi - 2 * half) * i / steps
            pts.append((cx + int(r * math.cos(angle)),
                        cy + int(r * math.sin(angle))))
        pygame.draw.polygon(screen, C_PACMAN, pts)
        _eye_off = {
            (1, 0):  (int(r * 0.20), -int(r * 0.45)),
            (-1, 0): (-int(r * 0.20), -int(r * 0.45)),
            (0, -1): (int(r * 0.35), -int(r * 0.30)),
            (0, 1):  (int(r * 0.35),  int(r * 0.10)),
        }
        eox, eoy = _eye_off.get(self._pacman_dir, (int(r * 0.20), -int(r * 0.45)))
        pygame.draw.circle(screen, (0, 0, 0), (cx + eox, cy + eoy), 2)

    def _draw_ghosts(self, screen):
        lbl_font = pygame.font.SysFont("consolas", 9, bold=True)
        rid = self.world.current_room_id
        for g in self.world.ghosts:
            if g.room_id != rid: continue
            gx = g.x * TILE + TILE // 2
            gy = g.y * TILE + TILE // 2
            r = TILE // 2 - 3
            color = g.color()
            if g.state == "RETURN":
                for ox in (-3, 3):
                    pygame.draw.ellipse(screen, (210, 210, 255),
                                        pygame.Rect(gx + ox - 2, gy - 3, 5, 6))
                    pygame.draw.circle(screen, (0, 0, 160), (gx + ox, gy - 1), 2)
            else:
                pygame.draw.ellipse(screen, color,
                                    pygame.Rect(gx - r, gy - r, r * 2, r * 2))
                pygame.draw.rect(screen, color,
                                 pygame.Rect(gx - r, gy, r * 2, r // 2 + 2))
                br = max(2, r // 3)
                for i in range(3):
                    bx = gx - r + br + i * br * 2
                    pygame.draw.circle(screen, color, (bx, gy + r // 2 + 2), br)
                for ox in (-r // 3, r // 3 + 1):
                    pygame.draw.ellipse(screen, (255, 255, 255),
                                        pygame.Rect(gx + ox - 2, gy - r // 2 - 1, 4, 5))
                    pygame.draw.circle(screen, (0, 0, 200),
                                       (gx + ox, gy - r // 3), max(1, r // 4))
            t = lbl_font.render(g.state[0], True, (255, 255, 255))
            screen.blit(t, (gx - t.get_width() // 2, gy - TILE // 2 - 11))

    def _mark(self, screen, tile, color, label):
        x, y = tile
        rect = pygame.Rect(x*TILE+2, y*TILE+2, TILE-4, TILE-4)
        pygame.draw.rect(screen, color, rect, 2)
        font = pygame.font.SysFont("consolas", 11, bold=True)
        t = font.render(label, True, color)
        screen.blit(t, (x*TILE + 6, y*TILE + 4))

class Level1(Level):
    name = "1. DFA - Shortest Path"
    description = "Navigate from start to end via the shortest route."
    GRAPH_ITERS = 4
    MIN_NODES = 4
    TREE_COUNT = 5

class Level2(Level):
    name = "2. PDA — Potion Stack"
    description = "Collect the potion before reaching the end."
    GRAPH_ITERS = 12
    MIN_NODES = 8
    TREE_COUNT = 7

    def _post_init(self):
        self._pda_stack = ["Z0"]
        self._potion_taken = False
        self._potion_room_id = None
        self._potion_tile = None
        self._pda_paths = []
        self._pda_path_set = set()
        self._setup_pda()

    def _setup_pda(self):
        from collections import Counter
        graph = self.world.graph
        neighbors_fn = graph._neighbors

        intermediates = []
        for path in self._all_paths:
            intermediates.extend(path[1:-1])

        if intermediates:
            counts = Counter(intermediates)
            self._potion_room_id = counts.most_common(1)[0][0]
        else:

            candidates = [nid for nid in graph.nodes
                          if nid not in (graph.start_id, graph.end_id)]
            if candidates:
                self._potion_room_id = self.world.rng.choice(candidates)

        if self._potion_room_id is not None:
            leg1 = bfs_path(neighbors_fn, graph.start_id, self._potion_room_id)
            leg2 = bfs_path(neighbors_fn, self._potion_room_id, graph.end_id)
            if leg1 and leg2:
                self._pda_paths = [leg1 + leg2[1:]]   
            else:
                self._pda_paths = list(self._all_paths)
        else:
            self._pda_paths = list(self._all_paths)

        self._pda_path_set = {tuple(p) for p in self._pda_paths}

        if self._potion_room_id is not None:
            potion_node = graph.nodes[self._potion_room_id]
            self._potion_tile = self._pick_potion_tile(potion_node)
            potion_node.dots.discard(self._potion_tile)

    def _pick_potion_tile(self, node):

        used = self.world._used_special_tiles(node)
        blocked = node.forest.blocked if node.forest else set()
        comp = node.ca.largest_component() or set(node.ca.floor_tiles())
        cands = [c for c in comp if c not in used and c not in blocked]
        if not cands:
            return node.spawn
        sx, sy = node.spawn
        cands.sort(key=lambda p: -((p[0]-sx)**2 + (p[1]-sy)**2))
        return self.world.rng.choice(cands[:max(1, len(cands)//3)])

    def _write_level_config(self):
        self._write_pda_config()

    def _write_pda_config(self):
        graph = self.world.graph
        nodes = graph.nodes
        states = [room_label(nodes[nid]) for nid in sorted(nodes.keys())] + ["ACCEPT"]
        sigma = ["p" + room_label(nodes[nid]) for nid in sorted(nodes.keys())] + ["pickup"]
        gamma = ["X"]
        start_lbl = room_label(nodes[graph.start_id])
        end_lbl = room_label(nodes[graph.end_id])
        pr_lbl = (room_label(nodes[self._potion_room_id])
                  if self._potion_room_id is not None else "none")

        sp_edges = set()
        for path in self._pda_paths:
            for i in range(len(path) - 1):
                sp_edges.add((path[i], path[i + 1]))

        trans = []
        for (a_id, b_id) in sp_edges:
            a = room_label(nodes[a_id])
            b = room_label(nodes[b_id])
            trans.append(f"{a}, p{b}, epsilon, {b}, epsilon")

        if self._potion_room_id is not None:
            trans.append(f"{pr_lbl}, pickup, epsilon, {pr_lbl}, X")
            trans.append(f"{end_lbl}, epsilon, X, ACCEPT, epsilon")
        else:
            trans.append(f"{end_lbl}, epsilon, epsilon, ACCEPT, epsilon")
        trans.sort()

        audit = graph.audit_log_lines(limit=200)
        lines = (
            ["[Sigma]"] + sigma + ["[Stop]",
             "[Gamma]"] + gamma + ["[Stop]",
             "[States]"] + states + ["[Stop]",
             "[Start]", start_lbl, "[Stop]",
             "[Accept]", "ACCEPT", "[Stop]",
             "[Transitions]"] + trans + ["[Stop]", "",
             f"# Potion room: {pr_lbl}", "",
             "[AuditLog]"] + audit + ["[Stop]", ""]
        )
        with open("configPDA.txt", "w") as f:
            f.write("\n".join(lines))

    def _append_pda_traversal_log(self, accepted, reason=""):
        graph = self.world.graph
        nodes = graph.nodes
        trav_str = " -> ".join(room_label(nodes[rid]) for rid in self._traversal)
        if accepted:
            result = "ACCEPTED (shortest path + potion collected)"
        elif reason == "missing_potion":
            result = "REJECTED (correct path but potion not collected)"
        else:
            result = "REJECTED (not a valid shortest path)"
        with open("configPDA.txt", "a") as f:
            f.write("\n".join([
                "[TraversalLog]", trav_str,
                f"Stack at end: {self._pda_stack}",
                f"Result: {result}", "[Stop]", ""
            ]))

    def _check_potion(self):
        if self._potion_taken or self._potion_tile is None:
            return
        room = self.world.current_room()
        if room.id != self._potion_room_id:
            return
        if (self.world.player_x, self.world.player_y) == self._potion_tile:
            self._potion_taken = True
            self._pda_stack.append("X")
            self._word_sequence.append("pickup")

    def try_move(self, dx, dy):
        if dx != 0 or dy != 0:
            self._pacman_dir = (dx, dy)
        self.world.step_player(dx, dy, on_event=self.on_event)
        if not self.is_won() and not self.is_lost():
            self._collect_dots()
            self._check_power_pill()
            self._check_potion()

    def on_event(self, ev):
        if ev[0] == "portal":
            dest_id = ev[1]
            self._traversal.append(dest_id)
            nodes = self.world.graph.nodes
            self._word_sequence.append("p" + room_label(nodes[dest_id]))
            if dest_id == self.world.graph.end_id:
                result = pda(self._word_sequence)
                if result == "acceptat":
                    self.won = True
                    self._append_pda_traversal_log(accepted=True)
                else:
                    self.hp = 0
                    reason = "missing_potion" if not self._potion_taken else "wrong_path"
                    self._append_pda_traversal_log(accepted=False, reason=reason)

    def draw_world(self, screen):
        super().draw_world(screen)
        if not self._potion_taken and self._potion_tile and self._potion_room_id is not None:
            room = self.world.current_room()
            if room.id == self._potion_room_id:
                px, py = self._potion_tile
                rect = pygame.Rect(px*TILE + 2, py*TILE + 2, TILE - 4, TILE - 4)
                pygame.draw.rect(screen, C_POTION, rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 2)
                badge_font = pygame.font.SysFont("consolas", 12, bold=True)
                t = badge_font.render("V", True, (15, 15, 20))
                screen.blit(t, (px*TILE + TILE//2 - t.get_width()//2,
                                py*TILE + TILE//2 - t.get_height()//2))

    def draw_hud(self, screen, font, font_big):
        graph = self.world.graph
        nodes = graph.nodes
        x0 = GRID_W * TILE + 12
        max_w = SIDEBAR_W - 24
        y = 50

        screen.blit(font.render(f"Score: {self.score}", True, C_ACCENT), (x0, y))
        y += 18
        room = self.world.current_room()
        biome_name = room.biome["name"] if room.biome else "Unknown"
        biome_color = tint(room.biome["color"], mul=1.05, add=10) if room.biome else C_TEXT_DIM
        screen.blit(font.render(f"Biome: {biome_name}", True, biome_color), (x0, y))
        y += 18
        goal_lbl = room_label(nodes[graph.end_id])
        screen.blit(font.render(f"Goal: {goal_lbl}", True, C_GOAL), (x0, y))
        y += 18
        cur_lbl = room_label(nodes[self.world.current_room_id])
        screen.blit(font.render(f"Current: {cur_lbl}", True, C_TEXT), (x0, y))
        y += 18

        if self._potion_room_id is not None:
            pr_lbl = room_label(nodes[self._potion_room_id])
            potion_color = C_GOOD if self._potion_taken else C_POTION
            status = "collected" if self._potion_taken else "not collected"
            screen.blit(font.render(
                f"Potion [{pr_lbl}]: {status}",
                True, potion_color), (x0, y))
            y += 18
        stack_top_first = list(reversed(self._pda_stack))
        stack_color = C_GOOD if "X" in self._pda_stack else C_TEXT_DIM
        screen.blit(font.render("Stack: [" + ", ".join(stack_top_first) + "]", True, stack_color), (x0, y))
        y += 20

        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1)
        y += 8

        screen.blit(font.render("Collect potion, then reach end", True, C_TEXT_DIM), (x0, y))
        y += 16
        screen.blit(font.render("via shortest path. PDA validates.", True, C_TEXT_DIM), (x0, y))
        y += 22

        screen.blit(font.render("Valid PDA Paths:", True, C_ACCENT), (x0, y))
        y += 18
        if self._pda_paths:
            for path in self._pda_paths:
                path_str = " -> ".join(room_label(nodes[rid]) for rid in path)
                for line in _wrap_path_lines(font, path_str, max_w):
                    screen.blit(font.render(line, True, C_HILITE), (x0, y))
                    y += 15
                y += 4
        else:
            screen.blit(font.render("(no valid PDA path)", True, C_BAD), (x0, y))
            y += 15
        y += 4
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1)
        y += 8

        screen.blit(font.render("Your path:", True, C_ACCENT), (x0, y))
        y += 16
        trav_str = " -> ".join(room_label(nodes[rid]) for rid in self._traversal)
        for line in _wrap_path_lines(font, trav_str, max_w):
            screen.blit(font.render(line, True, C_TEXT), (x0, y))
            y += 15

        screen.blit(font.render("WASD  M map  R restart  Esc menu", True, C_TEXT_DIM),
                    (x0, SCREEN_H - 28))

def _common_prefix(lst):
    p = ''
    for chars in zip(*lst):
        if len(set(chars)) == 1:
            p += chars[0]
        else:
            break
    return p

def _compress_run(s):
    if not s:
        return ''
    out = []
    i = 0
    while i < len(s):
        c = s[i]; j = i + 1
        while j < len(s) and s[j] == c:
            j += 1
        count = j - i
        if count == 1:
            out.append(c)
        elif count == 2:
            out.append(c + c)
        else:
            out.append(f'{c}{{{count}}}')
        i = j
    return ''.join(out)

def _try_star(non_empty, has_empty):
    if not non_empty:
        return None
    unit = min(non_empty, key=len)
    if not unit:
        return None
    for m in non_empty:
        reps, rem = divmod(len(m), len(unit))
        if rem != 0 or unit * reps != m:
            return None
    counts   = sorted(len(m) // len(unit) for m in non_empty)
    expected = list(range(1, counts[-1] + 1))
    if counts != expected:
        return None
    pat = _compress_run(unit)
    if len(pat) > 1:
        pat = f'({pat})'
    return pat, ('*' if has_empty else '+')

def _simplify(p):
    return re.sub(r'(.)\1\*', r'\1+', p)

def _build_alternation(mids):
    has_empty = '' in mids
    non_empty = sorted(set(m for m in mids if m))
    if not non_empty:
        return ''
    if len(non_empty) == 1:
        part = _compress_run(non_empty[0])
        return f'({part})?' if has_empty else part
    star = _try_star(non_empty, has_empty)
    if star:
        pat, q = star
        return pat + q
    sub_pre  = _common_prefix(non_empty)
    tails    = [m[len(sub_pre):] for m in non_empty]
    sub_suf  = _common_prefix([t[::-1] for t in tails])[::-1]
    sub_mids = [t[: len(t) - len(sub_suf) if sub_suf else len(t)] for t in tails]
    if sub_pre or sub_suf:
        sub_unique    = sorted(set(sub_mids))
        sub_has_empty = '' in sub_unique
        sub_non_empty = [m for m in sub_unique if m]
        sub_star      = _try_star(sub_non_empty, sub_has_empty)
        if sub_star:
            sp, sq = sub_star
            sub_inner = sp + sq
        elif sub_has_empty:
            sub_parts = [_compress_run(m) for m in sub_non_empty]
            sub_inner = ('(' + '|'.join(sub_parts) + ')?' if sub_parts else '')
        elif len(sub_non_empty) == 1:
            sub_inner = _compress_run(sub_non_empty[0])
        else:
            sub_inner = '(' + '|'.join(_compress_run(m) for m in sub_non_empty) + ')'
        result = _compress_run(sub_pre) + sub_inner + _compress_run(sub_suf)
        return f'({result})?' if has_empty else result
    parts = '|'.join(_compress_run(m) for m in non_empty)
    return f'({parts})?' if has_empty else f'({parts})'

def _build_pattern(sequences):
    unique    = sorted(set(sequences))
    has_empty = '' in unique
    non_empty = [s for s in unique if s]
    if not unique:
        return '.*'
    if not non_empty:
        return ''
    if len(non_empty) == 1:
        core = _compress_run(non_empty[0])
        return f'({core})?' if has_empty else core
    pre   = _common_prefix(non_empty)
    tails = [s[len(pre):] for s in non_empty]
    suf   = _common_prefix([t[::-1] for t in tails])[::-1]
    mids  = [t[: len(t) - len(suf) if suf else len(t)] for t in tails]
    unique_mids = sorted(set(mids))
    if has_empty:
        unique_mids = sorted(set(unique_mids + ['']))
    if all(not m for m in unique_mids):
        core = _compress_run(pre + suf)
        return f'({core})?' if has_empty else core
    inner  = _build_alternation(unique_mids)
    core   = _compress_run(pre) + inner + _compress_run(suf)
    result = f'({core})?' if has_empty else core
    return _simplify(result)

def _build_nfa(sequences):
    states = ['q0']
    transitions = []
    accept_states = []
    for idx, seq in enumerate(sorted(set(sequences))):
        if not seq:
            continue
        first = f'q{idx}c0'
        states.append(first)
        transitions.append(f'q0, epsilon, {first}')
        prev = first
        for i, ch in enumerate(seq):
            nxt = f'q{idx}c{i + 1}'
            states.append(nxt)
            transitions.append(f'{prev}, {ch}, {nxt}')
            prev = nxt
        accept_states.append(prev)
    if not accept_states:
        accept_states = ['q0']
    return states, transitions, accept_states

class Level3Regex(Level):
    name        = "3. Regex — Glyph Hunt"
    description = "Collect letter glyphs to build a word matching the regex."
    GRAPH_ITERS = 8
    MIN_NODES   = 7
    TREE_COUNT  = 5
    _ALPHABET   = ['a', 'b']

    def _post_init(self):
        self._sym             = {}
        self._word            = ""
        self._pattern         = ""
        self._valid_seqs      = []
        self._matched         = None
        self._glyph_tiles     = {}
        self._collected_rooms = set()
        self._assign_symbols()
        self._generate_pattern()
        self._place_glyphs()

    def _assign_symbols(self):
        for nid, node in sorted(self.world.graph.nodes.items()):
            if node.type == 'ROOM':
                self._sym[nid] = self.world.rng.choice(self._ALPHABET)

    def _path_seq(self, path):
        return ''.join(self._sym[r] for r in path if r in self._sym)

    def _generate_pattern(self):
        graph     = self.world.graph
        all_paths = all_simple_paths(
            graph._neighbors, graph.start_id, graph.end_id,
            max_extra=3, max_paths=48,
        )
        seqs = [self._path_seq(p) for p in all_paths]
        self._valid_seqs = list(dict.fromkeys(s for s in seqs))
        if not self._valid_seqs:
            self._valid_seqs = ['']
        self._pattern = _build_pattern(self._valid_seqs)

    def _place_glyphs(self):
        for nid, node in self.world.graph.nodes.items():
            if node.type != 'ROOM':
                continue
            used    = self.world._used_special_tiles(node)
            blocked = node.forest.blocked if node.forest else set()
            comp    = node.ca.largest_component() or set(node.ca.floor_tiles())
            cands   = [t for t in comp if t not in used and t not in blocked]
            if not cands:
                continue
            sx, sy = node.spawn
            cands.sort(key=lambda p: -((p[0]-sx)**2 + (p[1]-sy)**2))
            tile = self.world.rng.choice(cands[:max(1, len(cands) // 4)])
            self._glyph_tiles[nid] = tile
            node.dots.discard(tile)

    def _write_level_config(self):
        graph = self.world.graph
        nodes = graph.nodes
        sym_lines = [
            f"{room_label(nodes[nid])}, {self._sym[nid]}"
            for nid in sorted(self._sym)
        ]
        nfa_states, nfa_trans, nfa_accept = _build_nfa(self._valid_seqs)
        alphabet = sorted(set(''.join(self._valid_seqs))) or list(self._ALPHABET)
        lines = [
            f"[Pattern]",     self._pattern,               "[Stop]", "",
            "[Sigma]",       *alphabet,                   "[Stop]", "",
            "[States]",      *nfa_states,                 "[Stop]", "",
            "[Start]",       "q0",                        "[Stop]", "",
            "[Accept]",      *nfa_accept,                 "[Stop]", "",
            "[Transitions]", "# state, symbol, next_state",
            *nfa_trans,                                   "[Stop]", "",
            "[RoomSymbols]", *sym_lines,                  "[Stop]", "",
            "[ValidSequences]",
            *sorted(set(self._valid_seqs)),               "[Stop]", "",
        ]
        with open("configREGEX.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _log_collection(self, accepted):
        word   = self._word or "(empty)"
        result = (f"ACCEPTED — '{word}' matches /{self._pattern}/"
                  if accepted else
                  f"REJECTED — '{word}' does NOT match /{self._pattern}/")
        with open("configREGEX.txt", "a", encoding="utf-8") as f:
            f.write("\n".join([
                "", "[CollectionLog]",
                f"Word:    {word}",
                f"Pattern: {self._pattern}",
                f"Result:  {result}",
                "[Stop]", "",
            ]))

    def on_event(self, ev):
        pass

    def try_move(self, dx, dy):
        if dx != 0 or dy != 0:
            self._pacman_dir = (dx, dy)
        self.world.step_player(dx, dy)
        pos    = (self.world.player_x, self.world.player_y)
        cur_id = self.world.current_room_id
        if (cur_id in self._glyph_tiles
                and self._glyph_tiles[cur_id] == pos
                and cur_id not in self._collected_rooms):
            sym = self._sym.get(cur_id)
            if sym is not None:
                self._word += sym
                self._collected_rooms.add(cur_id)
                self._matched = None
                try:
                    ok = bool(re.fullmatch(self._pattern, self._word))
                except re.error:
                    ok = False
                if ok:
                    self._matched = True
                    self.won      = True
                    self._log_collection(True)
        if not self.is_won() and not self.is_lost():
            self._collect_dots()
            self._check_power_pill()

    def try_scan(self):
        if self.is_won() or self.is_lost():
            return
        self._word            = ""
        self._collected_rooms = set()
        self._matched         = None

    def draw_world(self, screen):
        super().draw_world(screen)
        badge_font = pygame.font.SysFont("consolas", 9, bold=True)
        room       = self.world.current_room()
        for (px, py), (dest_id, _, _, _) in room.portals_to.items():
            sym = self._sym.get(dest_id)
            if sym is None:
                continue
            color = _SYM_COLOR.get(sym, C_ACCENT)
            t  = badge_font.render(sym, True, (10, 10, 20))
            bx = px * TILE + TILE - t.get_width() - 3
            by = py * TILE + 3
            bg = pygame.Rect(bx - 2, by - 1, t.get_width() + 4, t.get_height() + 2)
            pygame.draw.rect(screen, color, bg)
            screen.blit(t, (bx, by))
        cur_id = self.world.current_room_id
        if cur_id in self._glyph_tiles and cur_id not in self._collected_rooms:
            sym = self._sym.get(cur_id)
            if sym is not None:
                gx, gy = self._glyph_tiles[cur_id]
                color  = _SYM_COLOR.get(sym, C_ACCENT)
                gf     = pygame.font.SysFont("consolas", 13, bold=True)
                rect   = pygame.Rect(gx*TILE+2, gy*TILE+2, TILE-4, TILE-4)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 2)
                t = gf.render(sym, True, (10, 10, 20))
                screen.blit(t, (gx*TILE + TILE//2 - t.get_width()//2,
                                gy*TILE + TILE//2 - t.get_height()//2))

    def draw_hud(self, screen, font, font_big):
        graph = self.world.graph
        nodes = graph.nodes
        x0    = GRID_W * TILE + 12
        max_w = SIDEBAR_W - 24
        y     = 50
        screen.blit(font.render(f"Score: {self.score}", True, C_ACCENT), (x0, y)); y += 18
        room = self.world.current_room()
        bc   = tint(room.biome["color"], 1.05, 10) if room.biome else C_TEXT_DIM
        screen.blit(font.render(f"Biome: {room.biome['name']}", True, bc), (x0, y)); y += 18
        cur_lbl = room_label(nodes[self.world.current_room_id])
        cur_sym = self._sym.get(self.world.current_room_id)
        if cur_sym:
            sc = _SYM_COLOR.get(cur_sym, C_TEXT)
            screen.blit(font.render(f"Room: {cur_lbl}  glyph=", True, C_TEXT), (x0, y))
            ox = x0 + font.size(f"Room: {cur_lbl}  glyph=")[0]
            col_lbl = "collected" if self.world.current_room_id in self._collected_rooms else cur_sym
            c2  = C_TEXT_DIM if self.world.current_room_id in self._collected_rooms else sc
            screen.blit(font.render(col_lbl, True, c2), (ox, y))
        else:
            screen.blit(font.render(f"Room: {cur_lbl}", True, C_TEXT), (x0, y))
        y += 20
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1); y += 8
        screen.blit(font.render("Regex pattern:", True, C_ACCENT), (x0, y)); y += 16
        pat_col = (C_GOOD if self._matched is True
                   else C_BAD if self._matched is False
                   else C_HILITE)
        pf      = pygame.font.SysFont("consolas", 18, bold=True)
        pat_str = self._pattern
        while pat_str:
            chunk = pat_str
            while pf.size(chunk)[0] > max_w and len(chunk) > 1:
                chunk = chunk[:-1]
            screen.blit(pf.render(chunk, True, pat_col), (x0, y)); y += 22
            pat_str = pat_str[len(chunk):]
        y += 4
        screen.blit(font.render("Word collected:", True, C_ACCENT), (x0, y)); y += 16
        wd  = self._word if self._word else "(empty)"
        wc  = (C_GOOD if self._matched is True
               else C_BAD if self._matched is False
               else C_TEXT)
        screen.blit(font_big.render(wd, True, wc), (x0, y)); y += 26
        if self._word and self._matched is None:
            try:
                on_track = bool(re.match(self._pattern + ".*", self._word))
            except re.error:
                on_track = False
            hint     = "On track..." if on_track else "Off track — SPACE to reset"
            hint_col = (180, 220, 180) if on_track else (200, 120, 120)
            screen.blit(font.render(hint, True, hint_col), (x0, y))
        y += 18
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y), (x0 + max_w - 12, y), 1); y += 8
        screen.blit(font.render("Valid sequences:", True, C_ACCENT), (x0, y)); y += 16
        for seq in sorted(set(self._valid_seqs))[:12]:
            disp = seq if seq else "(empty)"
            screen.blit(font.render(f"  {disp}", True, C_HILITE), (x0, y)); y += 14
        if len(set(self._valid_seqs)) > 12:
            screen.blit(font.render(f"  … (+{len(set(self._valid_seqs))-12} more)",
                                    True, C_TEXT_DIM), (x0, y)); y += 14
        pygame.draw.line(screen, C_TEXT_DIM, (x0, y + 4), (x0 + max_w - 12, y + 4), 1)
        y += 12
        screen.blit(font.render("Room glyphs:", True, C_ACCENT), (x0, y)); y += 16
        lf = pygame.font.SysFont("consolas", 12)
        for nid in sorted(self._sym):
            sym    = self._sym[nid]
            lbl    = room_label(nodes[nid])
            col    = _SYM_COLOR.get(sym, C_TEXT)
            done   = nid in self._collected_rooms
            marker = " ✓" if done else ""
            dc     = C_TEXT_DIM if done else col
            screen.blit(lf.render(f"  {lbl} = {sym}{marker}", True, dc), (x0, y)); y += 13
        screen.blit(font.render("WASD move  SPACE reset word  M map  R restart",
                                True, C_TEXT_DIM), (x0, SCREEN_H - 28))

LEVELS = [Level1, Level2, Level3Regex]

class Minimap:
    NODE_COLOR = {"START": C_START, "ROOM": (140,140,170),
                  "END": C_GOAL}
    EDGE_COLOR = {"normal": (160,160,160), "portal": C_PORTAL}

    def draw(self, screen, world, level=None):
        graph = world.graph
        ids = list(graph.nodes.keys())
        if not ids: return
        pad = 30; w = GRID_W*TILE - 2*pad; h = SCREEN_H - 2*pad
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10,10,18,235))
        pygame.draw.rect(panel, C_HILITE, panel.get_rect(), 2)
        screen.blit(panel, (pad, pad))
        xs = [graph.nodes[i].mx for i in ids]
        ys = [graph.nodes[i].my for i in ids]
        minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
        rx = max(0.001, maxx-minx); ry = max(0.001, maxy-miny)
        def to_px(n):
            return (int(pad+40+(n.mx-minx)/rx*(w-80)),
                    int(pad+40+(n.my-miny)/ry*(h-80)))
        for e in graph.edges:
            a_id, b_id = tuple(e); kind = graph.edge_types.get(e, "normal")
            ax, ay = to_px(graph.nodes[a_id]); bx, by = to_px(graph.nodes[b_id])
            pygame.draw.line(screen, self.EDGE_COLOR.get(kind, (160,160,160)),
                             (ax,ay), (bx,by), 3 if kind == "portal" else 2)
        font = pygame.font.SysFont("consolas", 11, bold=True)
        for nid in ids:
            n = graph.nodes[nid]; x, y = to_px(n)
            color = tint(n.biome["color"], mul=0.9) if n.biome else self.NODE_COLOR.get(n.type, (140,140,170))
            outline = tint(n.biome["color"], mul=0.55) if n.biome else (10,10,18)
            radius = 18 if nid == world.current_room_id else 14
            if nid == graph.start_id:
                pygame.draw.circle(screen, C_START, (x, y), radius + 6, 3)
            if nid == graph.end_id:
                pygame.draw.circle(screen, C_GOAL, (x, y), radius + 7, 3)
            if (level is not None and getattr(level, '_potion_room_id', None) == nid
                    and not getattr(level, '_potion_taken', True)):
                pygame.draw.circle(screen, C_POTION, (x, y), radius + 5, 3)
            if nid == world.current_room_id:
                pygame.draw.circle(screen, C_HILITE, (x,y), radius+4, 2)
            pygame.draw.circle(screen, color, (x,y), radius)
            pygame.draw.circle(screen, outline, (x,y), radius, 2)
            label = room_label(n)
            t = font.render(label, True, (10,10,18))
            screen.blit(t, (x - t.get_width()//2, y - t.get_height()//2))
        title_font = pygame.font.SysFont("consolas", 18, bold=True)
        screen.blit(title_font.render("ROOM GRAPH (derived by grammar)",
                                      True, C_ACCENT), (pad+16, pad+10))

class AppState(Enum):
    MENU = auto(); PLAYING = auto(); QUIT = auto()

class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_item  = pygame.font.SysFont("consolas", 20)
        self.font_desc  = pygame.font.SysFont("consolas", 14)
        self.selected = 0

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return None
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected = (self.selected+1) % len(LEVELS)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = (self.selected-1) % len(LEVELS)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return LEVELS[self.selected]
                    elif pygame.K_1 <= event.key < pygame.K_1 + len(LEVELS):
                        return LEVELS[event.key - pygame.K_1]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    p = self._hit(event.pos)
                    if p is not None: return LEVELS[p]
                if event.type == pygame.MOUSEMOTION:
                    p = self._hit(event.pos)
                    if p is not None: self.selected = p
            self._draw(); pygame.display.flip(); clock.tick(60)

    def _item_rect(self, i):
        w, h = 520, 56
        return pygame.Rect((SCREEN_W-w)//2, 150+i*(h+12), w, h)

    def _hit(self, pos):
        for i in range(len(LEVELS)):
            if self._item_rect(i).collidepoint(pos): return i
        return None

    def _draw(self):
        self.screen.fill(C_BG)
        title = self.font_title.render("THE AUTOMATA DUNGEON", True, C_ACCENT)
        self.screen.blit(title, ((SCREEN_W - title.get_width())//2, 50))
        sub = self.font_desc.render("Enter = play   Esc = quit   Arrows = select",
                                    True, C_TEXT_DIM)
        self.screen.blit(sub, ((SCREEN_W - sub.get_width())//2, 100))
        for i, cls in enumerate(LEVELS):
            r = self._item_rect(i); sel = (i == self.selected)
            pygame.draw.rect(self.screen, C_PANEL, r)
            pygame.draw.rect(self.screen, C_HILITE if sel else (60,60,80), r, 2)
            lab = self.font_item.render(cls.name, True, C_HILITE if sel else C_TEXT)
            self.screen.blit(lab, (r.x + 16, r.y + 8))
            desc = self.font_desc.render(cls.description, True, C_TEXT_DIM)
            self.screen.blit(desc, (r.x + 16, r.y + 32))

def play_level(screen, level_cls):
    clock = pygame.time.Clock()
    level = level_cls()
    minimap = Minimap()
    font = pygame.font.SysFont("consolas", 14)
    font_big = pygame.font.SysFont("consolas", 22, bold=True)
    MOVE = {pygame.K_LEFT:(-1,0), pygame.K_a:(-1,0),
            pygame.K_RIGHT:(1,0), pygame.K_d:(1,0),
            pygame.K_UP:(0,-1),   pygame.K_w:(0,-1),
            pygame.K_DOWN:(0,1),  pygame.K_s:(0,1)}
    show_minimap = False
    repeat_delay = 180
    repeat_interval = 55
    move_next_time = {}
    pygame.key.set_repeat(0)
    try:
        while True:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return 'menu'
                    elif event.key == pygame.K_r: level = level_cls()
                    elif event.key == pygame.K_m: show_minimap = not show_minimap
                    elif event.key == pygame.K_SPACE and not level.is_won() and not level.is_lost():
                        level.try_scan()
                    elif event.key in MOVE and not level.is_won() and not level.is_lost():
                        dx, dy = MOVE[event.key]; level.try_move(dx, dy)
                        move_next_time[event.key] = now + repeat_delay
                if event.type == pygame.KEYUP:
                    move_next_time.pop(event.key, None)
            if not level.is_won() and not level.is_lost():
                pressed = pygame.key.get_pressed()
                for key in list(move_next_time.keys()):
                    if not pressed[key]:
                        move_next_time.pop(key, None)
                        continue
                    if now >= move_next_time[key]:
                        dx, dy = MOVE[key]; level.try_move(dx, dy)
                        move_next_time[key] = now + repeat_interval
            level.update()
            screen.fill(C_BG)
            level.draw_world(screen)
            pygame.draw.rect(screen, C_PANEL, (GRID_W*TILE, 0, SIDEBAR_W, SCREEN_H))
            head = font_big.render(level.name.split('.',1)[-1].strip(), True, C_ACCENT)
            screen.blit(head, (GRID_W*TILE + 12, 10))
            level.draw_hud(screen, font, font_big)
            if level.is_won():
                _banner(screen, font_big, "LEVEL CLEARED  -  Esc to menu", (60, 220, 100))
            elif level.is_lost():
                _banner(screen, font_big, "GAME OVER  -  R to retry", (220, 80, 80))
            if show_minimap:
                minimap.draw(screen, level.world, level)
            pygame.display.flip(); clock.tick(60)
    finally:
        pygame.key.set_repeat(0)

def _banner(screen, font, text, color):
    s = font.render(text, True, color)
    bg = pygame.Surface((s.get_width()+30, s.get_height()+16), pygame.SRCALPHA)
    bg.fill((0,0,0,200))
    bx = (GRID_W*TILE - bg.get_width())//2
    by = (SCREEN_H - bg.get_height())//2
    screen.blit(bg, (bx, by)); screen.blit(s, (bx + 15, by + 8))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("The Automata Dungeon")
    state = AppState.MENU
    while state != AppState.QUIT:
        if state == AppState.MENU:
            choice = MainMenu(screen).run()
            if choice is None: state = AppState.QUIT
            else:
                state = AppState.QUIT if play_level(screen, choice) == 'quit' \
                                      else AppState.MENU
    pygame.quit(); sys.exit(0)

if __name__ == "__main__":
    main()
