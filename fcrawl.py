#!/usr/bin/python

# Once upon a time,
import curses
import locale
import math
import os
import platform
import random
import re
import string
import sys

from collections import defaultdict, deque, namedtuple
from datetime import datetime
from itertools import product, starmap
from operator import attrgetter
from optparse import OptionParser

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

# Py3 compat stuff
if sys.version > '3':
    def cmp(a, b):
        return (a > b) - (a < b)
    from collections import UserDict
    UserDict.iteritems = UserDict.items
    dict = UserDict
else:
    range = xrange

def p(s, col):
    ''' Prints a colored string to console (used during startup) '''
    sys.stdout.write('\033[' + col + 'm' + s + '\033[0m'); sys.stdout.flush()

# Globals that pyflakes should ignore
opts = player = stdscr = msgbox = cp = None

# Constants
# --------
# Interface: BH  B = 56x20 board, H=24x24 HUD
#            MH  M = 56x4 message area
# HUD: name/xl[1] hp=[1] hp/place[1] status[2] potions[7] [1]
#      monsters[4] [1] runes[5]
BOARD_X = BOARD_Y = 0
BOARD_WIDTH = 56
BOARD_HEIGHT = 20
MSG_Y = BOARD_HEIGHT
MSG_WIDTH = BOARD_WIDTH
MSG_HEIGHT = 4
HUD_START = BOARD_WIDTH + 1
HUD_WIDTH = 80 - HUD_START

LOS_RADIUS = 4
BASE_SPEED = 2

# For internal calculations only -- initial XL is always *displayed* as 1 in GUI
BASE_XL = 9
# The experience level cap
MAX_XL = +99
# Reaching which level will cause the game to be recorded in your scores file?
SCORING_XL = +5

LEN_MONSTER_LIST = 4

# Color constants
(
    NAVY,    GREEN,  TEAL,     MAROON,
    MAGENTA, BROWN,  DARKGREY, DARKGREY,
    BLUE,    LIME,   AQUA,     RED,
    PINK,    YELLOW, GREY,     WHITE,
) = range(16)

dark_colors = [
    NAVY,    GREEN,  TEAL,     MAROON,
    MAGENTA, BROWN,  DARKGREY, DARKGREY,
]

light_colors = [
    BLUE,    LIME,   AQUA,     RED,
    PINK,    YELLOW, GREY,     WHITE,
]

HP_COLORS = [
    (90, LIME),
    (75, GREEN),
    (50, YELLOW),
    (25, MAROON),
    (0,  RED),
]

# Message area width is MSG_WIDTH=56, these hints need to fit in one line
# (ideally only 55 chars instead of the full width)
# Make sure not to use MAROON since it would trigger -More- prompts!
HINTS = [
    # Flavor blurb" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (DARKGREY,    " You came to the dungeon looking for the Orb of Zot."),
    (DARKGREY,    " The Orb of Zot is a most fabulous artefact. Find it!"),
    (DARKGREY,    " They say an Orb is hidden in this dungeon's depths..."),
    (DARKGREY,    " You feel compelled to go deeper, and deeper, and ..."),
    (DARKGREY,    " A mysterious force seems to drag you downwards."),
    (DARKGREY,    " Weapons and armor seem weirdly absent in the dungeon."),

    # Branches (D Orc Elf Lair Sw Sh Sn Sp V Slime Tomb Choko Zot Surf)
    #             " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (DARKGREY,    " This dungeon is 10 levels deep. Are there others?"),
    (DARKGREY,    " Are orcs people, too? Do they have their own society?"),
    (DARKGREY,    " Is it true that mystic elves live down here somewhere?"),
    (DARKGREY,    " Which beasts will you have to face in the Lair?"),
    (DARKGREY,    " Some caverns are filled with mud. What decays there?"),
    (DARKGREY,    " Could a solid dungeon even hold large bodies of water?"),
    (DARKGREY,    " Who would willingly enter a pit filled with snakes?"),
    (DARKGREY,    " Who would willingly enter a spider's nest?"),
    (DARKGREY,    " Do you remember when you last saw another human being?"),
    (DARKGREY,    " What awaits you in the bosom of the Slime Pits?"),
    (DARKGREY,    " How many lifespans would it take to explore all this?"),
    (DARKGREY,    " Could there be an artifact even greater than the Orb?"),
    (DARKGREY,    " The deeper you go, the more you wonder: Orp? Of Zott?"),
    (DARKGREY,    " How will the Surfac look if you ever return?"),

    # Input, UI   " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (GREY,        " With [hjklyubn], [Shift+Key] runs in that direction."),
    (GREY,        " Press [>] on a staircase (>) to go down those stairs."),
    (GREY,        " Press [<] on a staircase (<) to go up those stairs."),
    (GREY,        " You can stand and wait for one turn by pressing [S]."),
    (BROWN,       " Your potions are displayed in the panel to the right."),
    (GREY,        " Drink potions by pressing the potion's number (0-6)."),
    (BROWN,       " Enemies you encounter show up in the right-hand panel."),
    (BROWN,       " Colors in the enemy list indicate danger levels."),
    (BROWN,       " Your experience level is displayed next to your name."),
    (GREY,        " Your experience level affects damage output and HP."),

    # Mechanics   " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (WHITE,       " Your character is represented by (@) on the map."),
    (GREY,        " Move into enemies to attack them."),
    (GREY,        " Reducing enemies' health will eventually defeat them."),
    (GREY,        " Losing all your health points (HP) will end this game."),
    (GREY,        " Defeat enemies to re-gain HP depending on their level."),
    (GREY,        " Move into doors (+) to open them (') and walk through."),
    (GREY,        " Once you open a door (+) you can't close it (') again."),
    # Other basics" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (GREY,        " Defeating an enemy removes one point of contamination."),
    (GREEN,       " A level without enemies on it is considered 'safe'."),
    (GREEN,       " When levels become safe, you auto-collect all items."),
    (GREEN,       " When levels become safe, you heal and level up."),

    # Warp board  " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (BROWN,       " The warp system is fragile but useful! Press G to warp."),
    (BROWN,       " Warping [G]: You can only warp from and to safe levels."),

    # Turns, speed" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (BROWN,       " Item pickup doesn't cost a turn. Quaffing potions does!"),
    (BROWN,       " Aborting an alchemy potion will not cost you a turn."),
    (BROWN,       " If you can't use a potion, trying to drink it is free."),

    # Potions     " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (WHITE,       " Drink healing potions with [1] to re-gain some HP."),
    (WHITE,       " Teleport potions move you to random tiles on the level."),
    (WHITE,       " Speed potions [3] make you Fast for 10 turns, but..."),
    (WHITE,       " Speed potions also exhaust (Slow) and contaminate you."),
    (WHITE,       " Phasing potions [4] let you avoid damage for 10 turns."),
    (WHITE,       " If phasing, you still suffer non-damage attack effects!"),
    (WHITE,       " Attacking an enemy while phasing aborts the Phase."),
    (WHITE,       " Drinking a phasing potion slightly contaminates you."),
    (WHITE,       " When contaminated, you can't use speed potions."),
    (WHITE,       " When contaminated, you can't use phasing potions."),

    # Enemies     " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (GREY,        " Enemies whose hp bar shows [r] have ranged attacks."),
    (GREY,        " Enemies whose hp bar shows [f] are twice as fast."),
    (GREY,        " Enemies with ranged attacks may step away from you."),
    (GREY,        " Off-screen enemies can't see you unless you're Marked."),
    (GREY,        " Colored names in the enemy list mean trouble..."),
    (GREY,        " Try approaching a ranged enemy with diagonal moves."),

    # Attack types" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (TEAL,        " (club) attacks deal more damage than usual."),
    (TEAL,        " (summon) attacks will make new enemies appear."),
    (TEAL,        " (orb) attackers will fire fast, deadly magic at you."),
    (TEAL,        " (gnaw) attacks deal more damage than usual."),
    (TEAL,        " (blink) gives attackers a chance to blink on attacks."),
    (TEAL,        " (disto) has a chance to teleport the defender around."),
    (TEAL,        " Attacks with (slow) add 1 turn to your Slow timer."),
    (TEAL,        " (trample) makes you move one tile in attack direction."),
    (TEAL,        " Vampiric attacks (vamp) let the attacker gain health."),
    (TEAL,        " (glow) attacks give you one point of contamination."),
    (TEAL,        " (freeze) attacks have a chance to destroy a potion."),
    (TEAL,        " (mark) attacks add 1 turn to your Mark timer."),
    (TEAL,        " Attacks of ugly things can have all sorts of effects."),
    (TEAL,        " Oklob plants are immobile. They have a ranged attack."),
    (TEAL,        " Merfolk can attack you from one tile distance (reach)."),
    (TEAL,        " Bears rage at low HP: they get faster and hit harder."),
    (TEAL,        " Hydras have multiple heads. More heads = more damage."),
    (TEAL,        " Hydras grow an additional head when you attack them."),

    # Statuses    " 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (YELLOW,      " When you're Fast, your turns take half as long."),
    (YELLOW,      " When you're Slow, your turns take twice as long."),
    (YELLOW,      " When Marked, enemies hunt down your location."),
    (YELLOW,      " The -Tele status means this level bans teleportation."),
    (YELLOW,      " Contam is caused by magic, and blocks using it."),
    (YELLOW,      " Phasing allows you to fly over water."),

    # Cautionwords" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (RED,         " Attack types like (slow) stack! They are very scary!"),
    (RED,         " 'Low HP' means you should try to retreat and heal!"),
    (RED,         " There's no reason to rush. Stay level-headed."),

    # Closing note" 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6 8 # 2 4 6"
    (WHITE,       " This game, fcrawl, is named after its creator, fcrawl."),
]
random.shuffle(HINTS)
HINTS = deque(HINTS)

msg_buf = []
def msg(s, col=GREY, more=False):
    if not s:
        return
    force_more = more or col == MAROON
    msg_buf.append((s[0].capitalize() + s[1 : MSG_WIDTH], col, force_more))

def one_chance_in(x): return random.randrange(x) == 0
def coinflip(): return one_chance_in(2)

# The powerful Point data structure
# ---------------------------------
Point = namedtuple('Point', ['x', 'y'])
Point.__neg__     = lambda p:    Point(-p.x, -p.y)
Point.__abs__     = lambda p:    abs(p.x) + abs(p.y)
Point.__add__     = lambda a, b: Point(a.x + b.x, a.y + b.y)
Point.__sub__     = lambda a, b: Point(a.x - b.x, a.y - b.y)
Point.__rmul__    = lambda p, k: Point(k * p.x, k * p.y)
Point.distance    = lambda a, b: max(abs(a.x - b.x), abs(a.y - b.y))

Point.step_toward = lambda a, b: Point(a.x + cmp(b.x, a.x),
                                       a.y + cmp(b.y, a.y))
Point.step_away   = lambda a, b: Point(a.x - cmp(b.x, a.x),
                                       a.y - cmp(b.y, a.y))

def cheby_edge(r):
    ''' Yields all coords with Chebyshev distance r from (0, 0). '''
    if r <= 0:
        yield Point(0, 0)
    else:
        for i in range(-r, r): yield Point( i, -r)
        for i in range(-r, r): yield Point( r,  i)
        for i in range(-r, r): yield Point(-i,  r)
        for i in range(-r, r): yield Point(-r, -i)

def dirs_near(d):
    ''' Yields d and the two directions 45 degrees adjacent to it. '''
    circle = [
        Point(-1, 0), Point(-1, -1), Point( 0, -1), Point( 1, -1),
        Point( 1, 0), Point( 1,  1), Point( 0,  1), Point(-1,  1),
    ]
    i = circle.index(d)
    return set([circle[(i + j) % 8] for j in [-1, 0, 1]])

DIRS = [Point(-1, -1), Point( 0, -1), Point( 1, -1),
        Point(-1,  0),                Point( 1,  0),
        Point(-1,  1), Point( 0,  1), Point( 1,  1)]

MOVE_KEYS   = [ 'y',           'k',           'u',
                'h',                          'l',
                'b',           'j',           'n']
MOVEMENT = dict(zip(MOVE_KEYS, DIRS))

# Features and Tiles
# ------------------
class Feature(object):
    def __init__(self, char, col, solid, opaque):
        self.char   = char
        self.col    = col
        self.solid  = solid
        self.opaque = opaque

F_WALL          = Feature('#', None,  True,  True)
F_FLOOR         = Feature('.', None,  False, False)
F_OPEN_DOOR     = Feature("'", WHITE, False, False)
F_CLOSED_DOOR   = Feature('+', WHITE, True,  True)
F_STAIRS_DOWN   = Feature('>', WHITE, False, False)
F_STAIRS_UP     = Feature('<', WHITE, False, False)
F_WATER         = Feature('~', NAVY,  True,  False)
F_CHOKO         = Feature('%', GREEN, True,  False)

class Tile(object):
    def __init__(self, feat):
        self.feat    = feat
        self.col     = feat.col
        self.char    = feat.char

        self.visible = False
        self.known   = False

        self.item    = None
        self.monster = None

        # set when adding to a Board
        self.board = None
        self.pos   = None

        # for stairs. set to a Tile in generation
        self.target = None

    def fake_mummy_char(self, top, player):
        no_mystery = self.visible or self.known
        if top in POTIONS and top not in player.forbidden_items and no_mystery:
            return '?'
        return top.char

    def display(self, player):
        top = (((self.visible or self.board.mapped) and self.monster)
           or self.item
           or self)

        if self.visible:
            # Replace some colors for some screen filters.
            # Monsters keep their regular color.
            disp_col = top.col
            if self.item and self.item == ANCIENT_CHOKO:
                disp_col = random.choice(light_colors)
            if not (self.visible and self.monster):
                if player.phase_time:
                    disp_col = PINK if player.speed_time else BLUE
                elif player.speed_time:
                    disp_col = RED
                if player.dead:
                    disp_col = GREY

                # Tint the colors according to darkness.
                if disp_col != top.col:
                    if top.col in dark_colors:
                        tcset = dark_colors
                    else:
                        tcset = light_colors
                    if disp_col in dark_colors:
                        dcset = dark_colors
                    else:
                        dcset = light_colors
                    disp_col = tcset[dcset.index(disp_col)]

            return (disp_col, self.fake_mummy_char(top, player))
        elif self.known:
            # Highlight monster positions
            if self.board.mapped and self.monster:
                return (WHITE, self.fake_mummy_char(top, player))
            return (DARKGREY, self.fake_mummy_char(top, player))
        else:
            return (GREY, ' ')

    @property
    def open(self):
        return self.monster is None and not self.feat.solid

# Items
# -----
class Item(object):
    def __init__(self, name, char, color, terse=''):
        self.name = name
        self.terse = terse or self.name
        self.char = char
        self.color = color

    @property
    def pname(self):
        if not '{}' in self.name:
            return self.name
        if player:
            return self.name.format(player.itname(self))
        else:
            return self.name.format('potion')

    @property
    def col(self):
        return self.color


class Potion(Item):
    def __init__(self, name, col, weight, use):
        Item.__init__(self, 'a {} of %s' % (name,), '!', col, terse=name)
        self.use = use
        self.alchemic = None
        self.alchemic_known = False
        self.weight = weight

class Rune(Item):
    def __init__(self, name, col):
        Item.__init__(self, 'a %s pizza of Zot' % name, '}', col, terse=name)

class SparklyItem(Item):
    ''' Item with multiple colors. '''
    def __init__(self, *args, **kwargs):
        super(SparklyItem, self).__init__(*args, **kwargs)

    @property
    def col(self):
        return random.choice(self.color)

def p_heal_wounds(actor):
    if actor.hp == actor.mhp:
        msg("You feel queasy.", MAROON)
        return False
    actor.hp = min(actor.mhp, int(actor.hp + random.normalvariate(10, 2)
                                           + (actor.mhp * 1) / 4.0))
    msg('You feel healthier.', P_HEAL_WOUNDS.col)
    return True

def p_teleportation(actor):
    t = actor.board.random_floor_tile()
    if not t or actor.board.no_tele:
        msg('Nothing happens.', P_TELEPORTATION.col)
        return False
    actor.move(t.pos)
    msg('You teleport away!', P_TELEPORTATION.col)
    return True

def p_speed(actor):
    if actor.contam:
        msg("You can't haste yourself while contaminated!", MAROON)
        return False
    if actor.speed_time:
        msg("You're too berserk!", MAROON)
        return False
    actor.speed_time = 12
    msg('You feel quick!', P_SPEED.col)
    return True

def p_phasing(actor):
    if actor.contam:
        msg("You can't phase while contaminated!", MAROON)
        return False
    actor.phase_time = 12
    actor.contam += 1
    msg('You phase away momentarily. (Attacking ends phasing.)',
        P_PHASING.col)
    return True

def p_torment(actor):
    affected = []
    for i in actor.board.monsters:
        if actor.can_see(i.pos) and i.name != 'orb':
            affected.append(i)
    if not affected:
        msg('Nobody is around! '
            'You %s.' % ('stop reading' if player.mummy else 'spit out'),
            MAROON)
        return False
    # Yourself
    if actor.mummy:
        msg('You are unaffected.')
    else:
        actor.hp = max(1, (actor.hp * 2) // 3)
        msg('You are wracked with pain!', P_TORMENT.col)
    # Enemies
    for m in affected:
        msg('%s convulses!' % m.the_name)
        m.hp = max(1, m.hp // 2)
    return True

def p_magic_mapping(actor):
    if actor.board.mapped:
        msg("You feel momentarily confused.", MAROON)
        return False
    actor.board.magic_mapping()
    msg('A map coalesces in your mind!')
    return True

def p_alchemy():
    if not player.items[P_ALCHEMY]:
        msg("You don't have %s!" % P_ALCHEMY.pname, MAROON)
        return False
    if sum(player.items[p] for p in POTIONS if p != P_ALCHEMY) < 2:
        M = player.mummy 
        msg("You need two %ss to %s them!" %
                ("item" if M else "potion", "combine" if M else "mix")
            , MAROON)
        return False

    chosen_potions = []
    message = ''
    for nth in ['First', 'Second']:
        key = ask('%s ingredient: %s' % (nth, message[:-2] or '[1-6]'))
        if key not in '123456':
            msg('Never mind.', DARKGREY)
            return False
        p = int(key) - 1
        po = POTIONS[p]
        if player.items[po] <= 0:
            msg("You don't have that %s!" % player.itname(po), MAROON)
            return False
        chosen_potions.append(p)
        if nth == 'First' and po.alchemic_known:
            for (k, candidate) in enumerate(POTIONS, start=1):
                if candidate == P_ALCHEMY:
                    continue
                if player.items[candidate] < 1:
                    continue
                if candidate == po and player.items[candidate] < 2:
                    continue

                new_pot = player.alchemy(po, candidate, dry_run=True)
                if candidate.alchemic_known and new_pot.alchemic_known:
                    result = new_pot.terse
                else:
                    result = '??'
                message += '[%s] %s, ' % (k, result)

    p1, p2 = chosen_potions

    if p1 == p2 and player.items[POTIONS[p2]] < 2:
        msg("You don't have enough of that %s!" % player.itname(p2), MAROON)
        return False

    new_item = player.alchemy(POTIONS[p1], POTIONS[p2])
    plural_name = player.itname(POTIONS[p1], POTIONS[p2])
    msg("You %s the %ss, obtaining %s." %
            ("hex" if player.mummy else "mix", plural_name, new_item.pname))
    return True

P_HEAL_WOUNDS   = Potion('heal wounds',   LIME,    80, p_heal_wounds)
P_TELEPORTATION = Potion('teleportation', AQUA,   100, p_teleportation)
P_SPEED         = Potion('speed',         RED,    100, p_speed)
P_PHASING       = Potion('phasing',       BLUE,   100, p_phasing)
P_TORMENT       = Potion('torment',       PINK,   100, p_torment)
P_MAGIC_MAPPING = Potion('magic mapping', YELLOW,  60, p_magic_mapping)
# alchemy has its own command
P_ALCHEMY       = Potion('alchemy',       WHITE,   60, lambda *_: None)

POTIONS = [
    P_HEAL_WOUNDS,
    P_TELEPORTATION,
    P_SPEED,
    P_PHASING,
    P_TORMENT,
    P_MAGIC_MAPPING,
    P_ALCHEMY,
]

# These potions will not be available if you are a mummy.
MUMMY_POTIONS = [
    P_HEAL_WOUNDS,
    P_SPEED,
]

def random_potion():
    subtotals = []
    total_weight = 0
    for p in POTIONS:
        total_weight += p.weight
        subtotals.append(total_weight)

    index = random.random() * total_weight
    for i, total in enumerate(subtotals):
        if index < total:
            return POTIONS[i]

P_ALCHEMY.alchemic = 0
P_ALCHEMY.alchemic_known = True

alchemics = list(range(1, len(POTIONS)))
random.shuffle(alchemics)
for i, alchemic in enumerate(alchemics):
    POTIONS[i].alchemic = alchemic

ORB_OF_EXPERIENCE = Item('You feel more experienced', '0', TEAL,
    terse='orb of experience')

class WarpBoard(object):
    def __init__(self, wizard):
        self.branches = defaultdict(dict)
        if wizard:
            for br in BRANCHES:
                for lvl in br.levels:
                    self.add(lvl)

    def find(self, target_br, target_depth):
        if not target_br:
            return
        for (br, warps) in self.branches.items():
            if not br.name.startswith(target_br):
                continue
            try:
                depth = int(target_depth)
            except ValueError:
                depth = self.max_depth(br)
            return warps.get(depth, warps[list(warps.keys())[-1]])

    def add(self, board):
        self.branches[board.branch][board.bindex + 1] = board

    def max_depth(self, br):
        return max(self.branches[br].keys()) if br in self.branches else None

# Thanks rwbarton
def in_ellipse(p, center, e_a, e_w, e_h):
    cos_a = math.cos(e_a)
    sin_a = math.sin(e_a)
    dx = float(p.x - center.x)
    dy = float(p.y - center.y)
    v  = (dx * cos_a + dy * sin_a) ** 2 / e_w ** 2
    v += (dx * sin_a - dy * cos_a) ** 2 / e_h ** 2
    return v < 1.0

# Monsters

class Actor(object):
    def __init__(self):
        self.action_points = self.mark_time = self.contam = 0
        self.speed_time = self.slow_time = self.phase_time = 0
        self.board = self.pos = None
        self.last_target = None

    @property
    def mhp(self):
        return self.xl * 5

    @property
    def hp_col(self):
        hp = max(0, self.hp)
        return [j for (i, j) in HP_COLORS if 100 * hp >= i * self.mhp][0]

    @property
    def here(self):
        return self.board.tiles[self.pos]

    def move(self, new_pos, newboard=None):
        self.here.monster = None
        self.pos = new_pos
        if newboard: self.board = newboard
        self.here.monster = self
        self.calculate_los()

    def can_move(self, t):
        is_water = t.feat == F_WATER
        return t.open or (is_water and self.flies)

    def calculate_los(self):
        self.los = {Point(0, 0)}

        # this dict keeps track of where light is going
        # to make sure it doesn't bend more than 45 degrees
        light = defaultdict(set)
        light[Point(0, 0)] = set(DIRS)

        for r in range(LOS_RADIUS):
            for p in cheby_edge(r):
                li = light[p]
                tile = self.board.tiles[self.pos + p]
                if not tile.feat.opaque:
                    for dp in li:
                        light[p + dp] |= li & dirs_near(dp)
                        self.los.add(p + dp)

    def can_see(self, p):
        return p - self.pos in self.los

    def attack(self, target):
        target.lose_hp(self)

    def lose_hp(self, actor, phys=True):
        self.hp -= int(actor.xl * random.lognormvariate(0, .1))

    @property
    def speed(self):
        mod_speed = self.base_speed
        if self.speed_time > 0:
            mod_speed *= 2
        if self.slow_time > 0:
            mod_speed /= 2
        return mod_speed

    def take_turn(self, turnf):
        self.action_points += self.speed
        while self.action_points >= BASE_SPEED:
            turnf(self)
            self.action_points -= BASE_SPEED
            if self.phase_time > 0:
                self.phase_time -= 1
            if self.slow_time > 0:
                self.slow_time -= 1
            if self.mark_time > 0:
                self.mark_time -= 1
            if self.speed_time > 0:
                self.speed_time -= 1
                if self.speed_time == 0:
                    self.contam += 2
                    self.slow_time = min(10, self.slow_time + 3)
            update_status()

    def quaffname(self, it=None):
        if getattr(self, 'mummy', False):
            return 'drink' if it in self.forbidden_items else 'read'
        return 'drink'


class Player(Actor):
    def __init__(self, name, mummy):
        self.name      = name
        self.char      = 'M' if mummy else '@'
        self.wizard    = name == 'wizard'
        self.mummy     = mummy

        self.xl        = BASE_XL + 1
        self.running   = None
        self.dead      = False
        self.win       = False
        self.hp        = self.mhp

        # For HP-bar GUI purposes: your HP before your last action
        self.last_hp   = self.hp
        # Also note the `speed` property which is modified by Fast/Slow
        self.base_speed = BASE_SPEED

        super(Player, self).__init__()
        self.ranged = False
        self.items = defaultdict(lambda: 0)

        if self.wizard:
            for potion in POTIONS:
                self.items[potion] = float('inf')
                potion.alchemic_known = True

        self.forbidden_items = set([])
        if self.mummy:
            self.forbidden_items = set(MUMMY_POTIONS)

        self.monsters_seen = []
        self.yellow_stairs_seen = dict()
        self.warp_board = WarpBoard(self.wizard)
        self.view_hits = False

    @property
    def title(self):
        level = ' [Level %d]'
        if len(self.name) + len(level) > HUD_WIDTH:
            level = ' [XL %d]'
        if len(self.name) + len(level) > HUD_WIDTH:
            level = ' [%d]'
        return level % (self.xl - BASE_XL)

    @property
    def desc(self):
        return self.name + self.title + " "

    @property
    def col(self):
        return self.hp_col

    @property
    def runes(self):
        return sum(self.items.get(rune, 0) for rune in RUNES)

    @property
    def danger_hp(self):
        return self.hp * 3 < self.mhp

    @property
    def flies(self):
        return self.phase_time

    def itname(self, it, it2=None):
        if self.mummy:
            forbid1 = it in self.forbidden_items
            forbid2 = it2 in self.forbidden_items
            if it2 is not None and forbid1 != forbid2:
                return 'item'
            return 'potion' if forbid1 else 'scroll'
        else:
            return 'potion'

    def attack(self, target):
        super(Player, self).attack(target)
        defeated = target.hp <= 0
        verb = 'defeat' if defeated else 'hit'
        dot  = '!'      if defeated else '.'
        col  = TEAL   if defeated else GREY
        msg('You %s %s%s' % (verb, target.the_name, dot), col)

    def choko_blocked(self, direction):
        if abs(direction) != 2:
            return False
        if (self.board.branch.name != 'Chokoban'
            and not self.items[ANCIENT_CHOKO]):
            return False

        if not self.board.tiles[self.pos + direction].feat.solid:
            msg('The choko forces restrict your diagonal movement!')
        return True

    def dir(self, d):
        if self.choko_blocked(d):
            return

        target = self.pos + d
        where = self.board.tiles[target]

        if where.monster:
            target = where.monster

            if target.name == 'orb':
                msg('You feel no overwhelming desire to commit suicide.')
                return False

            if self.phase_time:
                msg('You shift back into the material plane.',
                    P_PHASING.col)
                self.phase_time = 0
                return True
            else:
                self.attack(target)
                return True

        elif self.can_move(where):
            self.move(target)

            stair_dir = {
                F_STAIRS_UP: 'up',
                F_STAIRS_DOWN: 'down',
            }.get(self.here.feat)

            if stair_dir:
                t = self.here.target
                tname = t.board.name if t else \
                        'your win' if self.items[ORB_OF_ZOT] else \
                        'the Surfac'
                msg('There is a staircase %s to %s here.'
                        % (stair_dir, tname), DARKGREY)
            self.get_item(self.here)
            return True
        elif where.feat == F_CLOSED_DOOR:
            msg('You open the door.', DARKGREY)
            self.board.make_tile(target, F_OPEN_DOOR)
            self.calculate_los()
            for m in self.board.monsters:
                if m.can_see(where.pos):
                    m.calculate_los()
            return True
        elif where.feat == F_CHOKO:
            behind = self.pos + 2 * d
            if not self.board.tiles[behind].feat.solid:
                self.board.make_tile(target, F_FLOOR)
                self.board.make_tile(behind, F_CHOKO)
                self.move(target)
        else:
            return False

    def notes(self):
        prompt = curses.newwin(MSG_HEIGHT, MSG_WIDTH, MSG_Y, BOARD_X)
        prompt.clear(); box(prompt)
        prompt.addstr(1, 2, 'Note:', cp[TEAL])
        prompt.refresh()

        entry = curses.newwin(2, MSG_WIDTH - 9, MSG_Y + 1, BOARD_X + 8)
        curses.echo()
        note = entry.getstr().decode(encoding="utf-8")
        curses.noecho()
        msg(':: ' + note)
        if len(note) >= MSG_WIDTH - 3:
            note = note[MSG_WIDTH - 3:]
            msg('   ' + note)
        return False

    def warp(self):
        if not self.board.safe and not self.wizard:
            msg("You can't warp from an unsafe level!", MAROON)
            return False
        warp_x, warp_y = 10, 4
        warp_w = 9
        warp_legend = 'Warp to: '
        prompt = curses.newwin(3, warp_w + 2 + len(warp_legend) + 2,
                               warp_y, warp_x)
        prompt.clear()
        box(prompt)
        prompt.addstr(1, 2, warp_legend, cp[TEAL])
        prompt.refresh()

        accessible = dict()
        yellow_warp = dict()
        for i, br in enumerate(BRANCHES):
            deepest = self.warp_board.max_depth(br)
            b = br.terse
            if deepest is not None and deepest > 0:
                accessible[br.name] = '%s:%-4s' % (b, deepest)
            #elif deepest == 0:
            elif br.name in self.yellow_stairs_seen:
                entrance = self.yellow_stairs_seen[br.name]
                accessible[br.name] = '%s[%s]' % (b, entrance.board.terse)
                yellow_warp[br.terse] = yellow_warp[br.name] = entrance
            else:
                accessible[br.name] = ''

        # | D:10    Sw:3     E[O:2]  |
        BRANCHLIST = '''\
  {Dungeon:<9}{Swamp:<9}{Elf}
  {Lair:<9}{Shoals:<9}{Tomb}
  {Orc:<9}{Snake:<9}{Chokoban}
  {Vaults:<9}{Spider:<9}{Zot}
           {Slime:<9}'''
        bl = curses.newwin(2 + len(BRANCHLIST.split('\n')), warp_w + 19,
                           warp_y + 3, warp_x - 3)
        bl.clear()
        bl.addstr(1, 0, BRANCHLIST.format(**accessible), cp[TEAL])
        box(bl)
        bl.refresh()

        entry = curses.newwin(1, warp_w, warp_y + 1, 2 + warp_x + len(warp_legend))
        curses.echo()
        where = entry.getstr().decode(encoding="utf-8")
        curses.noecho()
        try:
            where = where.strip().replace(' ', ':').lower().capitalize()
            where = re.sub(r'(^[^:\d\$]+)([\$\d]+)$', r'\1:\2', where)
            if ':' in where:
                goal_br, goal_depth = where.split(':')
            else:
                goal_br = where; goal_depth = 27
        except Exception:
            if where:
                msg("You can't warp to %s!" % where, MAROON)
            return False

        can_warp = False
        goal_board = self.warp_board.find(goal_br, goal_depth)
        if goal_board is not None:
            can_warp = True
            stairs = goal_board.stairs_down
        elif goal_br in yellow_warp:
            goal_board = self.yellow_stairs_seen[goal_br].board
            if goal_board.safe:
                can_warp = True
                stairs = yellow_warp[goal_br]

        if not can_warp:
            msg("You can't warp to %s!" % where, MAROON)
            return False

        msg('You warp to %s.' % goal_board.name)
        self.move(stairs.pos, goal_board)
        return True

    def get_item(self, t):
        if not t.item:
            return
        if self.phase_time and not self.board.safe:
            msg("Ghosts can't pick up items!")
            return
        else:
            useless = t.item in player.forbidden_items
            msg(t.item.pname + '.', DARKGREY if useless else t.item.col)
            if t.item == ORB_OF_EXPERIENCE:
                self.gain_level()
            else:
                self.items[t.item] += 1
            if t.item == ORB_OF_ZOT:
                B_ZOT.levels[-1].stairs_up.target = \
                    B_SURFAC.levels[0].stairs_down
            elif t.item in RUNES:
                if player.runes == 3:
                    msg("Three pizza! That's enough to enter the realm of Zot.",
                        WHITE)
        self.running = None
        t.item = None

    def check_item(self, it):
        if self.items[it] == 0:
            msg("You don't have %s!" % (it.pname,), MAROON)
            return False
        if it in self.forbidden_items:
            msg("What a pity, you cannot %s it!" % self.quaffname(it), MAROON)
            return False
        return True

    def use_item(self, o, *args):
        if not self.check_item(o):
            return False
        msg('You %s %s.' % (self.quaffname(), o.pname))
        did_something = o.use(self, *args)
        if did_something and self.items[o] is not True:
            self.items[o] -= 1
        return did_something

    def use_stairs(self, kind):
        tile = self.here

        if tile.feat != kind:
            in_chokoban = self.board.branch.name == 'Chokoban'
            if self.board.safe and not in_chokoban or self.wizard:
                if kind == F_STAIRS_UP and self.board.stairs_up.target:
                    tile = self.board.stairs_up
                elif kind == F_STAIRS_DOWN and self.board.stairs_down.target:
                    tile = self.board.stairs_down
                self.move(tile.pos)

            # check again
            if tile.feat != kind:
                place = 'up' if kind == F_STAIRS_UP else 'down'
                msg("You can't go %s here." % place)
                return False

        # D:1 upstairs
        if not tile.target:
            self.win = self.items[ORB_OF_ZOT]
            if self.win:
                msg('You win!', LIME)
                self.killer = 'retrieved the Orb and escaped'
            else:
                msg('You escape the dungeon.', TEAL)
                self.killer = 'escaped the dungeon'
            self.dead = True
            return True

        # Surfac stairs with Orb
        if self.items[ORB_OF_ZOT]:
            surfac = B_SURFAC.levels[0]
            surfac.no_tele = True
            self.move(surfac.stairs_down.pos, surfac)

        new_board = tile.target.board

        if not self.wizard:
            if new_board == B_VAULTS.levels[0]:
                if not self.runes:
                    msg('You need pizza to enter the Vaults.', MAROON)
                    return False
            if new_board == B_ZOT.levels[0]:
                if self.runes < 3:
                    msg('You need at least 3 pizza to enter the Realm of Zot.',
                        MAROON)
                    return False

        msg('You enter %s.' % new_board.name)
        if (new_board.is_branch_end
            and not new_board.safe
            and new_board.branch == self.board.branch):
            msg('It is the final level of %s.' % self.board.branch.name,
                more=True)
        self.move(tile.target.pos, new_board)
        return True

    def lose_hp(self, actor, phys=True):
        self.running = False
        if self.phase_time > 0: # no damage
            msg("You take no damage.", P_PHASING.col)
            return

        Actor.lose_hp(self, actor, phys)
        if self.hp <= 0:
            msg('You faint...', RED)
            self.dead = True
            self.killer = ('annihilated' if self.hp < -30 else
                           'demolished'  if self.hp < -20 else
                           'mangled'     if self.hp < -10 else
                           'defeated') + ' by ' + actor.a_name

    def gain_level(self):
        if self.xl >= BASE_XL + MAX_XL:
            return
        self.xl += 1
        self.hp = (self.hp / (self.xl - 1.0)) * self.xl

    def lose_level(self):
        if self.xl <= BASE_XL:
            return
        self.xl -= 1
        self.hp = (self.hp / (self.xl + 1.0)) * self.xl

    def alchemy(self, p1, p2, dry_run=False):
        a1 = p1.alchemic
        a2 = p2.alchemic

        if dry_run:
            for potion in POTIONS:
                if potion.alchemic == (a1 + a2) % 7:
                    return potion

        for potion in (p1, p2, P_ALCHEMY):
            if self.items[potion] is not True:
                self.items[potion] -= 1
            potion.alchemic_known = True

        unknown_alchemics = []
        for potion in POTIONS:
            if potion.alchemic == (a1 + a2) % 7:
                new_potion = potion
                if self.items[potion] is not True:
                    self.items[potion] += 1
                potion.alchemic_known = True
            # Can't break from the loop above: collect all unknown potions
            if not potion.alchemic_known:
                unknown_alchemics.append(potion)
        if len(unknown_alchemics) == 1:
            last_pot = unknown_alchemics[0]
            last_pot.alchemic_known = True
        return new_potion


class Monster(Actor):
    def __init__(self, name, char, color, xl, habitat, ranged, flies, fast,
                 atk_msg, attack=Actor.attack):
        self.name       = name
        self.char       = char
        self.color      = color
        self.xl         = xl
        self.habitat    = habitat
        self.ranged     = ranged
        self.flies      = flies
        self.atk_msg    = atk_msg
        self.base_speed = 2 * BASE_SPEED if fast else BASE_SPEED
        self.attack     = attack

        super(Monster, self).__init__()

        self.hp         = self.mhp

        af = self.attack.__name__
        if af in ('attack', 'a_suicide'):
            self.af = ''
        else:
            max_af_len = HUD_WIDTH - 8 - len(self.name)
            self.af = af.split('_')[-1][:max_af_len]

    def walk(self, target):
        if self.can_move(self.board.tiles[target]):
            self.move(target)
        else:
            options = []
            for d in DIRS:
                new_pos = self.pos + d
                if self.can_move(self.board.tiles[new_pos]):
                    options.append(new_pos)
            if options:
                self.move(random.choice(options))

    def act(self, target, reach=False):
        # target is the player monster
        # XXX MEGA^2-HACK for reaching
        aim_pos = self.pos.step_toward(target.pos)
        if reach:
            reach_pos = aim_pos.step_toward(target.pos)
            if not self.can_see(reach_pos):
                reach_pos = aim_pos

        if self.can_see(target.pos):
            self.last_target = target.pos

        if (not self.ranged and target.pos == aim_pos
            or reach and target.pos == reach_pos):
            msg('%s %s!' % (self.the_name, self.atk_msg))
            self.attack(self, target)
        elif self.ranged and self.can_see(target.pos):
            dist = self.pos.distance(target.pos)
            if dist >= LOS_RADIUS or one_chance_in(3):
                msg('%s %s!' % (self.the_name, self.atk_msg))
                self.attack(self, target)
            else:
                self.walk(self.pos.step_away(target.pos))
        elif self.can_see(target.pos) or target.mark_time:
            self.walk(aim_pos)
        else:
            # monsters that can't see you aim for your last position,
            # else drift aimlessly
            if not self.ranged and self.last_target and self.last_target:
                self.walk(self.pos.step_toward(self.last_target))
                if self.pos == self.last_target:
                    self.last_target = None
            elif one_chance_in(3):
                self.walk(self.pos + random.choice(DIRS))

    def lose_hp(self, actor, phys=True):
        Actor.lose_hp(self, actor, phys)
        if self.hp <= 0:
            self.die_to(actor)

    def die_to(self, actor):
        bonushp = int(self.xl * random.uniform(2, 3))
        actor.hp = min(actor.hp + bonushp, actor.mhp)
        actor.contam = max(0, actor.contam - 1)
        self.here.monster = None
        if self in self.board.monsters:
            self.board.monsters.remove(self)

    @property
    def unique(self):
        return self.name in ('Murray', 'Rupert')

    @property
    def a_name(self):
        if self.unique:
            return self.name
        an = (self.name[0].lower() in 'aeiou')
        return ('an' if an else 'a') + ' ' + self.name

    @property
    def the_name(self):
        return ('' if self.unique else 'the ') + self.name

    @property
    def col(self):
        if (self.hp_col == HP_COLORS[-1][1] or player.view_hits):
            return self.hp_col
        return self.color

    @property
    def fast(self):
        return self.base_speed > BASE_SPEED

    @property
    def attack_xl(self):
        return self.xl * (0.5 if self.name == 'shining eye'
                     else 2.0 if self.attack in (a_club, a_gnaw)
                     else 4./3 if self.name == 'bear'
                     else 2./3 if self.name == 'ice beast'
                     else 1.0)


class IceBeast(Monster):
    def __init__(self):
        self.char       = 'Y'
        self.xl         = 9
        self.habitat    = ['D']
        self.ranged     = False
        self.flies      = False
        self.base_speed = BASE_SPEED
        self.attack     = a_freeze

        Actor.__init__(self)

        self.hp         = self.mhp

    @property
    def name(self):
        return ('fire' if player and player.mummy else 'ice') + ' beast'

    @property
    def color(self):
        return (MAROON if player and player.mummy else BLUE)

    @property
    def af(self):
        return ('burn' if player and player.mummy else 'freeze')

    @property
    def atk_msg(self):
        return (self.af) + 's you'


class AzureOoze(IceBeast):
    def __init__(self):
        super(AzureOoze, self).__init__()
        self.char       = 'J'
        self.xl         = 26
        self.habitat    = ['Sl']
        self.base_speed = 2 * BASE_SPEED
        self.hp         = self.mhp

    @property
    def name(self):
        return ('ruby' if player and player.mummy else 'azure') + ' ooze'


class Oklob(Monster):
    def __init__(self):
        self.name       = 'oklob plant'
        self.char       = 'P'
        self.color      = YELLOW
        self.xl         = 18
        self.habitat    = ['L', 'Sl', 'Sh']
        self.ranged     = True
        self.flies      = False
        self.atk_msg    = 'spits acid at you'
        self.base_speed = BASE_SPEED
        self.attack     = Actor.attack

        Actor.__init__(self)

        self.hp         = self.mhp
        self.af         = ''

    def can_move(self, t):
        return False


class Merfolk(Monster):
    def __init__(self):
        self.name       = 'merfolk'
        self.char       = 'm'
        self.color      = AQUA
        self.xl         = 22
        self.habitat    = ['Sh']
        self.ranged     = False
        self.flies      = True
        self.atk_msg    = 'hits you with a polearm'
        self.base_speed = BASE_SPEED
        self.attack     = Actor.attack

        Actor.__init__(self)

        self.hp         = self.mhp
        self.af         = 'reach'

    def act(self, target):
        Monster.act(self, target, reach=True)


class Bear(Monster):
    def __init__(self):
        self.name       = 'bear'
        self.char       = 'B'
        self.xl         = 15
        self.habitat    = ['L']
        self.ranged     = False
        self.flies      = False
        self.atk_msg    = 'claws you'

        Actor.__init__(self)

        self.hp         = self.mhp

        self.berserk = False

    @property
    def color(self):
        return RED if self.berserk else BLUE

    @property
    def base_speed(self):
        return (BASE_SPEED * 3) // 2 if self.berserk else BASE_SPEED

    @property
    def attack(self):
        return a_gnaw if self.berserk else Actor.attack

    @property
    def af(self):
        return 'gnaw+fast' if self.berserk else ''

    def lose_hp(self, actor, phys=True):
        super(Bear, self).lose_hp(actor, phys=phys)
        if max(0, self.hp) * 100 <= self.mhp * 66:
            self.berserk = True


class LairHydra(Monster):
    def __init__(self):
        self.heads      = random.randint(5, 8)
        self.color      = LIME
        self.habitat    = ['L']
        self.ranged     = False
        self.flies      = True
        self.atk_msg    = 'bites you'
        self.base_speed = BASE_SPEED
        self.attack     = Actor.attack

        Actor.__init__(self)

        self.hp         = self.mhp
        self.af         = ''

    @property
    def xl(self):
        return (self.heads * 7) // 3

    @property
    def char(self):
        glyphs = string.digits + string.ascii_uppercase
        return glyphs[min(self.heads, len(glyphs) - 1)]

    @property
    def name(self):
        english = [None, 'one', 'two', 'three', 'four', 'five',
                   'six', 'seven', 'eight', 'nine', 'ten']
        try:
            headcount = english[self.heads]
        except IndexError:
            headcount = str(self.heads)
        return '%s-headed hydra' % headcount

    def lose_hp(self, actor, phys=True):
        Monster.lose_hp(self, actor, phys)
        if self.heads < 27 and phys:
            msg("You hack one of %s's heads off!" % self.the_name)
            self.heads -= 1
            msg('%s grows two more!' % self.the_name)
            self.heads += 2


class SwampHydra(LairHydra):
    def __init__(self):
        LairHydra.__init__(self)
        self.habitat    = ['Sw']
        self.heads      = random.randint(9, 13)
        self.hp         = self.mhp
        self.base_speed = (BASE_SPEED * 3) // 2

    @property
    def xl(self):
        return (self.heads - 1) * 2


def a_summon(mons, qty, haunt=False):
    def helper_summon(self, target):
        c = target.pos if haunt else self.pos
        for _ in range(qty):
            if one_chance_in(3): continue
            t = self.board.random_floor_tile(c)
            self.board.spawn_monster(MONSMAP.get(mons, mons)(), tile=t)
    return helper_summon


class RoyalJelly(Monster):
    def __init__(self, doortiles):
        self.name       = 'royal jelly'
        self.char       = 'J'
        self.color      = YELLOW
        self.xl         = 68
        self.habitat    = []
        self.ranged     = False
        self.flies      = False
        self.atk_msg    = 'slimes you'
        self.base_speed = (BASE_SPEED * 3) // 2
        self.attack     = Actor.attack

        Actor.__init__(self)

        self.hp         = self.mhp
        self.af         = 'split'

        self.doortiles  = doortiles

    def lose_hp(self, actor, phys=True):
        hp_before = self.hp
        super(RoyalJelly, self).lose_hp(actor, phys=phys)
        how_many = max(2, 4 * (hp_before - self.hp) // self.xl)
        a_summon('slime creature', how_many)(self, actor)

    def die_to(self, actor):
        for t in self.doortiles:
            self.board.make_tile(t.pos, F_CLOSED_DOOR)
        super(RoyalJelly, self).die_to(actor)
        self.board.magic_mapping()
        msg("An ancient power vanishes with infernal noise!",
            P_MAGIC_MAPPING.col, more=True)


def a_board_summon(self, target):
    try:
        mons = random.choice(self.board.eligible_mons())
    except IndexError:
        msg('%s' % self.board.diff)
    else:
        return a_summon(mons, 1)(self, target)

def a_orb(how_many):
    def helper_orb(self, target):
        for _ in range(how_many):
            if one_chance_in(3): continue
            t = self.board.random_floor_tile(self.pos)
            self.board.spawn_monster(MONSMAP['orb'](), tile=t)
    return helper_orb

def a_suicide(self, target):
    Actor.attack(self, target)
    self.die_to(self)

def a_club(self, target):
    self.xl *= 2
    Actor.attack(self, target)
    self.xl /= 2

def a_gnaw(self, target):
    a_club(self, target)

def a_blink(self, target):
    Actor.attack(self, target)
    dont_blink_chance = 4 if self.name in ('elec golem', 'frog') else 2
    if one_chance_in(dont_blink_chance): return
    t = self.board.random_floor_tile(self.pos, 3)
    if t: self.move(t.pos)

def a_disto(self, target):
    Actor.attack(self, target)
    if coinflip(): return
    t = self.board.random_floor_tile(target.pos, 3)
    if t: target.move(t.pos)

def a_slow(limit):
    def helper_slow(self, target):
        Actor.attack(self, target)
        if target.slow_time < limit:
            target.slow_time += 1
    return helper_slow

def a_trample(self, target):
    Actor.attack(self, target)
    new_pos = target.pos.step_away(self.pos)
    if self.board.tiles[new_pos].open:
        if self.ranged and one_chance_in(3): return
        blocked = target.choko_blocked(new_pos - target.pos)
        if blocked: return
        old_pos = target.pos
        target.move(new_pos)
        if not self.ranged:
            self.move(old_pos)

def a_vamp(self, target):
    Actor.attack(self, target)
    bonushp = (self.mhp - self.hp) // 4
    self.hp += bonushp

def a_glow(self, target):
    old_xl = self.xl
    self.xl = self.xl // 2
    Actor.attack(self, target)
    self.xl = old_xl

    contam_chance = 0.50 if target.contam else 0.25
    if target.contam < 5 and random.random() < contam_chance:
        target.contam += 1

def a_freeze(self, target):
    shatter_potion = random.random() < 2./3
    if shatter_potion:
        # If we try to shatter potions, deal half damage to make up for it.
        old_xl = self.xl
        self.xl = self.xl // 2
        Actor.attack(self, target)
        self.xl = old_xl

        p = random.choice(POTIONS)
        if 0 < target.items[p] < float('inf'):
            target.items[p] -= 1
            if target.items[p]:
                what = 'One of your %ss of %s' % (target.itname(p), p.terse)
            else:
                what = 'Your %s of %s' % (target.itname(p), p.terse)
            # PROBABLY NOT A HACK
            itname = player.itname(p)
            if player.mummy:
                itemdest = 'crumbles' if itname == 'scroll' else 'boils away'
            else:
                itemdest = 'shatters'
            #/PROBABLY NOT A HACK
            msg('%s %s.' % (what, itemdest))
    else:
        Actor.attack(self, target)

def a_mark(self, target):
    Actor.attack(self, target)
    if target.mark_time < 10:
        target.mark_time += 4

def a_slime(self, target):
    random.choice((a_slow(5), a_trample, a_blink, a_disto))(self, target)

def a_lich_summon(self, target):
    random.choice((Actor.attack, Actor.attack,
        a_summon('orb', 1), a_summon('orb', 2),
        a_summon('beast', 1), a_summon('beast', 2)))(self, target)

def a_mummy_summon(self, target):
    random.choice((Actor.attack, Actor.attack,
        a_summon('ufetubus', 5), a_summon('beast', 2)))(self, target)

def a_guardian_orb(self, target):
    random.choice((Actor.attack, a_orb(2)))(self, target)

def mc(xl, char_name, color, places, atk_msg, flags, atk=Actor.attack):
    char, name = char_name.split(' ', 1)
    habitat = re.findall('[A-Z][a-z]*', places)

    return lambda: Monster(name, char, color, xl, habitat,
        'r' in flags, 's' in flags, 'f' in flags, atk_msg, attack=atk)

no_monster = mc(0, 'B program bug', RED, '', 'bites you', "")

MONSMAP = dict()
monsters = [
  mc( 4, 'r rat', BROWN, 'D', 'bites you', ""),
  mc( 5, 'g goblin', BROWN, 'D', 'hits you with a club', "", a_club),
  mc( 5, '5 ufetubus', AQUA, 'Su', 'hits you', ""),
  mc( 6, 'K kobold', BROWN, 'D', 'hits you', ""),
  mc( 7, 'l iguana', NAVY, 'DL', 'bites you', "s"),
  mc( 7, 'o orc priest', GREEN, 'DO', 'calls upon Beogh', "r"),
  mc( 8, 'y killer bee', BROWN, 'DL', 'stings you', "f"),
  mc( 9, 'O ogre', BROWN, 'DO', 'hits you with a giant spiked club',"", a_club),
  mc(10, 'Y yak', BROWN, 'DL', 'gores you', ""),
  mc(10, 'Y elephant', GREEN, 'DL', 'tramples you', "", a_trample),
  mc(11, 'h orb hound', MAGENTA, 'OE', 'weaves an orb', "r", a_orb(1)),
  mc(11, '@ vault guard', TEAL, '', 'hits you', ""),
  mc(12, 'y wasp', YELLOW, 'DSp', 'stings you', "s", a_slow(5)),
  mc(12, 'h warg', GREY, 'LO', 'bites you', ""),
  mc(13, 'F frog', LIME, 'L', 'hits you', "s", a_blink),
  mc(14, 'u ugly thing', MAGENTA, 'DLV', 'slimes you', "", a_slime),
  mc(14, 'l komodo', MAROON, 'L', 'gnaws away at you', "s", a_gnaw),
  mc(15, 'V vampire', MAROON, 'D', 'drains your life', "", a_vamp),
  mc(15, '2 beast', BROWN, '', 'tramples you', "f", a_trample),
  mc(16, 'c yaktaur', MAROON, 'DV', 'fires a bolt at you', "r"),
  mc(16, 'o orctaur', MAROON, 'O', 'fires an orc at you', "r"),
  mc(17, 'y mosquito', GREEN, 'ShSw', 'draws your blood', "sf", a_vamp),
  mc(18, 'z skeleton', TEAL, 'DV', 'hits you with a dire flail', "", a_club),
  mc(18, 'C stone giant', GREY, 'DVO', 'throws a stone at you', "rs"),
  mc(18, '* orb', WHITE, '', 'hits you', "sf", a_suicide),
  mc(19, 't turtle', GREEN, 'Sh', 'bites you', "s"),
  mc(19, 's jump spider', BLUE, 'Sp', 'ensnares you', "f", a_blink),
  mc(19, 'y hornet', MAROON, 'Sp', 'stings you', "sf", a_slow(10)),
  mc(20, 'G shining eye', PINK, 'DVSl', 'makes you glow', "rs", a_glow),
  mc(20, 'N naga', GREEN, 'LSn', 'spits poison at you', ""),
  mc(22, 'l swamp drake', BROWN, 'LSw', 'breathes gas at you', "rs"),
  mc(22, 'e elf knight', TEAL, 'DEV', 'hits you', ""),
  mc(22, 'S orb snake', MAGENTA, 'Sn', 'weaves an orb', "r", a_orb(1)),
  mc(22, 'e elf mage', MAGENTA, 'DEV', 'blinks you away', "r", a_blink),
  mc(23, 'J acid blob', AQUA, 'Sl', 'splashes you with acid', "rs"),
  mc(24, 'J slime creature', GREEN, 'DVShSl', 'hits you', "s"),
  mc(25, 'p sentinel', BLUE, 'V', 'hits you with a horn', "", a_mark),
  mc(25, 'D fire dragon', GREEN, 'DVESnSwShZ', 'breathes fire at you', "rs"),
  mc(27, 'X abomination', GREEN, 'ESwSn', 'constricts you', ""),
  mc(27, '8 elec golem', AQUA, 'Z', 'zaps you', "rs", a_blink),
  mc(27, 'y ghost moth', MAGENTA, 'SpZ', 'flutters at you', "sf", a_disto),
  mc(27, 'Q Quylthulg', PINK, 'SpZ', 'spawns a bug', "r", a_board_summon),
  mc(27, 's orb spider', MAGENTA, 'Sp', 'weaves some orbs', "r", a_orb(2)),
  mc(28, 's Rupert', GREY, 'Sp', 'hits you with a great mace', "", a_club),
  mc(28, 'H sphinx', GREY, 'T', 'casts a spell at you', "r", a_slow(10)),
  mc(30, '1 Sentinel', BROWN, 'EZ', 'hits you', "s", a_mark),
  mc(30, 'D goldragon', YELLOW, 'Z', 'breathes you away', "rs", a_trample),
  mc(33, 'M guardian mummy', YELLOW, 'T', 'hits you', ""),
  mc(34, 'X Orb Guardian', MAGENTA, 'Z', 'hits you', "", a_guardian_orb),
  mc(36, '* orb of fire', MAROON, 'Z', 'shoots fire at you', "rs"),
  mc(36, 'L lich', PINK, 'Z', 'casts a spell at you', "r", a_lich_summon),
  mc(36, 'M greater mummy', PINK, 'T', 'waves and mumbles',"r", a_mummy_summon),
  mc(36, 'z Murray', AQUA, 'T', 'rattles his jaw', "r", a_board_summon),
  IceBeast,
  Bear,
  SwampHydra, SwampHydra,
  Merfolk, Merfolk,
  LairHydra,
  Oklob,
  AzureOoze,
]
MONSMAP.update((mc().name, mc) for mc in monsters)

## Board generation

class Board(object):
    def __init__(self, branch, bindex, diff, gen):
        self.width  = BOARD_WIDTH
        self.height = 24 - MSG_HEIGHT
        self.coords = []
        for x in range(self.width):
            for y in range(self.height):
                self.coords.append(Point(x, y))

        self.branch = branch
        self.bindex = bindex
        self.diff   = diff
        self.name   = '%s:%d' % (branch.name, bindex + 1)

        self.tiles    = defaultdict(lambda: Tile(F_WALL))
        self.monsters = []
        self.safe     = diff == 0
        self.mapped   = False
        self.no_tele  = False

        # easy lookup, set in level generation
        self.stairs_up   = None
        self.stairs_down = None
        self.yellow_downstairs = []  # (tile, target_branch)

        gen(self)
        if diff > 0:
            self.gen_mons(random.randint(5, 6 + diff // 50))
            if branch.name != 'Slime':
                self.gen_items(random.randint(2, 5 + diff // 40))

        if branch.name == 'Chokoban':
            self.magic_mapping()
            for p in self.coords:
                if p.y > 17:
                    self.tiles[p].known = False

    @property
    def terse(self):
        return '%s:%d' % (self.branch.terse, self.bindex + 1)

    @property
    def is_branch_end(self):
        return self.diff > 0 and self.bindex == self.branch.depth - 1 \
            and self.branch.name != 'Surfac'

    def eligible_mons(self):
        eligible = []
        for k in monsters:
            mon = k()
            limit = 60 if self.branch.name == 'Zot' \
                    else 30 if self.diff > 80 else 10
            mdiff = mon.xl * 10
            if abs(mdiff - self.diff) > limit: continue
            if self.branch.terse not in mon.habitat: continue
            eligible.append(k)
        if eligible:
            return eligible
        else:
            msg('Bugs in %s (diff %s)' % (self.name, self.diff), MAROON)
            return [no_monster]

    def gen_mons(self, count, tile=None):
        living_here = self.eligible_mons()
        for _ in range(count):
            self.spawn_monster(random.choice(living_here)(), tile=tile)

    def gen_items(self, count):
        for _ in range(count):
            self.spawn_item(random_potion())
        if not opts.hard_mode and one_chance_in(3):
            self.spawn_item(ORB_OF_EXPERIENCE)

    def make_tile(self, pos, feat):
        tile = Tile(feat)
        tile.board = self
        tile.pos = pos
        if feat.col is None:
            tile.col = {F_WALL:  self.branch.wallcol,
                        F_FLOOR: self.branch.floorcol}[feat]
        self.tiles[pos] = tile
        return tile

    def rect_tile(self, p, width, height, kind):
        for ix in range(p.x, p.x + width):
            for iy in range(p.y, p.y + height):
                self.make_tile(Point(ix, iy), kind)

    def clear_tile(self, kind):
        self.rect_tile(Point(0, 0), self.width, self.height, kind)

    def bounded_randranges(self, centre, radius):
        r = centre + Point(random.randint(-radius, radius),
                           random.randint(-radius, radius))
        return Point(max(1, min(r.x, self.width  - 1)),
                     max(1, min(r.y, self.height - 1)))

    def random_floor_tile(self, radiate_from=None, radius=1):
        # can return None if it doesn't find a tile!
        for _ in range(500):
            if radiate_from:
                p = self.bounded_randranges(radiate_from, radius)
                radius += 1
            else:
                p = Point(random.randrange(1, self.width  - 1),
                          random.randrange(1, self.height - 1))
            t = self.tiles[p]
            if t.feat == F_FLOOR and not t.monster:
                return t
        return None

    def spawn_feature(self, kind, exclude=None):
        for tries in range(20):
            t = self.random_floor_tile()
            if not t: return None
            if not (exclude and t.pos in exclude): break

        return self.make_tile(t.pos, kind)

    def spawn_monster(self, monster, tile=None):
        self.monsters.append(monster)
        t = tile or self.random_floor_tile()
        if not t: return None
        t.monster = monster
        monster.board = self
        monster.pos   = t.pos
        monster.calculate_los()
        return t

    def spawn_item(self, item):
        while True:
            t = self.random_floor_tile()
            if not t: return None
            if t.feat == F_FLOOR and not t.item: break
        t.item = item
        return t

    def link_branch(self, branch):
        t = self.spawn_feature(F_STAIRS_DOWN)
        t.target = branch.levels[0].stairs_up
        branch.levels[0].stairs_up.target = t
        t.col = YELLOW
        self.yellow_downstairs.append((t, branch))

    def magic_mapping(self):
        self.mapped = True
        for p in self.coords:
            for d in DIRS:
                if not self.tiles[p + d].feat.opaque:
                    self.tiles[p].known = True
                    break
        for stair, target_br in self.yellow_downstairs:
            player.yellow_stairs_seen[target_br.name] = stair
            player.yellow_stairs_seen[target_br.terse] = stair

    def clear_monsters(self):
        for monster in self.monsters:
            monster.here.monster = None
        self.monsters = []

    def parse_layout(self, layout, wallcol, parent_level, mons=None):
        self.clear_monsters()
        special_tiles = defaultdict(list)
        for y, r in enumerate(layout):
            for x, c in enumerate(r):
                p = Point(x, y)
                if c == '#':
                    t = self.make_tile(p, F_WALL)
                    t.col = wallcol
                elif c == '.':
                    self.make_tile(p, F_FLOOR)
                elif c in '0123456':
                    if c in '01234':
                        t = self.make_tile(p, F_FLOOR)
                    elif c in '56':
                        t = self.make_tile(p, F_WALL)
                    special_tiles[c].append(t)
                elif c == '+':
                    self.make_tile(p, F_CLOSED_DOOR)
                elif c == '<':
                    self.stairs_up = self.make_tile(p, F_STAIRS_UP)
                    if parent_level:
                        parent_level.stairs_down.target = self.stairs_up
                        self.stairs_up.target = parent_level.stairs_down
                elif c == '>':
                   self.stairs_down = self.make_tile(p, F_STAIRS_DOWN)
        return special_tiles

def irange(x, y):
    return range(x, y + 1) if x < y else range(x, y - 1, -1)

# Level generation functions.

class Chainable(namedtuple('Chainable', 'f')):
    '''Callable objects you can chain: (f >> g)(x) is f(x); g(x).'''
    __call__ = lambda self, *a, **ka: self.f(*a, **ka)
    def __rshift__(self, g):
        def f_then_g(*a, **ka): self.f(*a, **ka); g(*a, **ka)
        return Chainable(f_then_g)

def Parametrized(func):
    return lambda *a, **ka: Chainable(lambda s: func(s, *a, **ka))

@Parametrized
def g_rooms(self, nrooms, make_vaults=False, min_stair_dist=0):
    # Fill with walls
    self.clear_tile(F_WALL)

    # Draw and connect rooms
    vaults = []
    rcon = []
    for i in range(nrooms):
        for tries in range(200 // nrooms):
            rw  = random.randint(4, 7) | 1
            rh  = random.randint(4, 7) | 1
            rx  = random.randint(1, self.width  - rw - 3) | 1
            ry  = random.randint(1, self.height - rh - 3) | 1
            rp  = Point(rx, ry)

            rcx = random.randrange(rx, rx + rw - 2) | 1
            rcy = random.randrange(ry, ry + rh - 2) | 1
            rc = Point(rcx, rcy)

            rect = product(range(rx, rx+rw), range(ry, ry+rh))
            rect = [Point(x, y) for (x, y) in rect]

            # Prefer non-overlapping rectangles
            if all(self.tiles[p].feat == F_WALL for p in rect):
                if make_vaults and one_chance_in(10):
                    vaults.append(rect[:])
                break

        self.rect_tile(rp, rw, rh, F_FLOOR)
        rcon.append(rc)

        if i >= 1:
            rsx, rsy = rcon[-2].x, rcon[-2].y
            placed_door = False
            if coinflip():
                path  = [Point(i, rsy) for i in irange(rsx, rcx)] \
                        + [Point(rcx, i) for i in irange(rsy, rcy)]
            else:
                path  = [Point(rsx, i) for i in irange(rsy, rcy)] \
                        + [Point(i, rcy) for i in irange(rsx, rcx)]

            for p in path:
                if self.tiles[p].feat == F_WALL \
                        and not placed_door:
                    self.make_tile(p, F_CLOSED_DOOR)
                    placed_door = True
                else:
                    self.make_tile(p, F_FLOOR)

    no_stairs = []
    for rect in vaults:
        # Get points surrounding the rectangle.
        tl = rect[0]  - Point(1, 1)
        br = rect[-1] + Point(1, 1)
        border  = [Point(x, tl.y) for x in range(tl.x, br.x + 1)]
        border += [Point(x, br.y) for x in range(tl.x, br.x + 1)]
        border += [Point(tl.x, y) for y in range(tl.y, br.y + 1)]
        border += [Point(br.x, y) for y in range(tl.y, br.y + 1)]

        vault = random.randint(1, 4)
        if vault == 1:
            # Pillar
            n = random.randint(1, 2)
            self.rect_tile(rp + Point(n, n), rw - 2 * n, rh - 2 * n, F_WALL)
        elif vault == 2:
            # 1/4 grid pattern
            for p in rect:
                if p.x % 2 == 0 and p.y % 2 == 0:
                    self.make_tile(p, F_WALL)
        elif vault == 3:
            # 1/2 grid pattern
            tl, br = rect[0], rect[-1]
            for p in rect:
                if p.x == tl.x or p.y == tl.y: continue
                if p.x == br.x or p.y == br.y: continue
                if p.x % 2 == p.y % 2:
                    self.make_tile(p, F_WALL)
        elif vault == 4:
            # Zoo (loot and monsters)
            living_here = self.eligible_mons()
            c = 8 if self.branch.name == 'Dungeon' else 5
            for p in rect:
                # exclude from stairs generation
                no_stairs.append(p)
                if one_chance_in(c):
                    # this lets no *extra* ranged monsters generate,
                    # but one or two could still end up in there
                    # through random generation
                    mons = random.choice(living_here)()
                    if not mons.ranged:
                        self.spawn_monster(mons, tile=self.tiles[p])
                if one_chance_in(c):
                    it = ORB_OF_EXPERIENCE
                    if opts.hard_mode or not one_chance_in(4):
                        it = random_potion()
                    self.tiles[p].item = it

            # colour walls as a warning
            wall_col = GREY if self.branch.terse in ('D', 'L') else TEAL
            for p in border:
                if self.tiles[p].feat == F_WALL:
                    self.tiles[p].col = wall_col

        # add doored walls as border to vaults, to make sure they're isolated
        for p in border:
            if self.tiles[p].feat == F_FLOOR:
                t = F_CLOSED_DOOR if p.x % 2 != p.y % 2 else F_WALL
                self.make_tile(p, t)

    self.stairs_up = self.spawn_feature(F_STAIRS_UP, exclude=no_stairs)
    self.stairs_down = self.spawn_feature(F_STAIRS_DOWN, exclude=no_stairs)

    d = self.stairs_up.pos.distance(self.stairs_down.pos)
    if d < min_stair_dist:
        g_rooms(nrooms, make_vaults, min_stair_dist)(self)


def g_vaults(self):
    self.clear_tile(F_WALL)
    xw = self.width - 2
    xh = self.height - 2
    self.rect_tile(Point(1, 1), xw, xh, F_FLOOR)
    xdiv = random.randint(4, 6)
    ydiv = random.randint(2, 4)

    for x, y in product(range(xdiv), range(ydiv)):
        rw = max(3, xw // xdiv - random.randint(1, 4))
        rh = max(3, xh // ydiv - random.randint(1, 4))
        rx = (xw * x) // xdiv
        ry = (xh * y) // ydiv
        rx += random.randint(0, xw // xdiv - rw - 1) + 2
        ry += random.randint(0, xh // ydiv - rh - 1) + 2

        self.rect_tile(Point(rx, ry), rw, rh, F_WALL)

    self.rect_tile(Point(1, 1), xw, 1, F_FLOOR)
    self.rect_tile(Point(1, xh), xw, 1, F_FLOOR)
    self.rect_tile(Point(1, 1), 1, xh, F_FLOOR)
    self.rect_tile(Point(xw, 1), 1, xh, F_FLOOR)

    self.stairs_up   = self.spawn_feature(F_STAIRS_UP)
    self.stairs_down = self.spawn_feature(F_STAIRS_DOWN)

@Parametrized
def g_cave(self, size, clear_first=True):
    if clear_first:
        self.clear_tile(F_WALL)
    xw = self.width - 2
    xh = self.height - 2
    x = random.randint(self.width // 4, self.width * 3 // 4)
    y = random.randint(self.height // 3, self.height * 2 // 3)
    p = Point(x, y)
    first = p

    for i in range(size):
        d = random.choice([Point(0, 1), Point(0, -1),
                            Point(1, 0), Point(-1, 0)])
        cx = (x + d.x - 1.0) / xw
        cy = (y + d.y - 1.0) / xh
        if math.hypot(cx - 0.5, cy - 0.5) >= 0.5: continue

        p = Point(max(1, min(xw, p.x + d.x)),
                    max(1, min(xh, p.y + d.y)))
        self.make_tile(p, F_FLOOR)

    self.stairs_up   = self.make_tile(first, F_STAIRS_UP)
    self.stairs_down = self.make_tile(p,     F_STAIRS_DOWN)

@Parametrized
def g_elliptic(self, nrooms, radius, min_axis=2, clear_first=True):
    assert nrooms > 1, 'Need at least two rooms (stairs up/down).'
    assert 2 * radius < self.height - 1, \
            '2 < radius < %s but got %s' % (self.height // 2, radius)
    if clear_first:
        self.clear_tile(F_WALL)
    rooms = []
    for _ in range(2 * nrooms):
        rooms.append(
        Point(random.randrange(radius, self.width  - radius - 1),
                random.randrange(radius, self.height - radius - 1)))
    rooms.sort(key=attrgetter('x'))
    rooms = rooms[::2]
    random.shuffle(rooms)
    up, down = rooms[:2]
    for e_center in rooms:
        e_a = random.random() * 2 * math.pi
        e_w = random.randrange((radius * 2) // 4, (radius * 4) // 4)
        e_w = max(e_w, min_axis)
        e_h = random.randrange((radius * 2) // 4, (radius * 4) // 4)
        e_h = max(e_h, min_axis)
        for p in self.coords:
            if in_ellipse(p, e_center, e_a, e_w, e_h):
                self.make_tile(p, F_FLOOR)

        new = e_center
        self.make_tile(new, F_FLOOR)
        while new != up:
            new = new.step_toward(up)
            self.make_tile(new, F_FLOOR)
            if coinflip():
                d = random.choice(DIRS)
                new = new.step_toward(d)
                self.make_tile(new, F_FLOOR)

    self.stairs_up   = self.make_tile(up,   F_STAIRS_UP)
    self.stairs_down = self.make_tile(down, F_STAIRS_DOWN)

def g_choko(self):
    layout = [
        '########################################################',
        '##################<..................###################',
        '####################################+###################',
        '##################3333333333333333333###################',
        '##################1..................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################...................###################',
        '##################..................2###################',
        '##################3333333333333333333###################',
        '##################+#####################################',
        '##################..................>###################',
        '########################################################',
    ]
    special_tiles = self.parse_layout(layout, self.branch.wallcol,None)
    start = special_tiles['1'][0].pos
    end   = special_tiles['2'][0].pos
    fills = special_tiles['3']

    for p in starmap(Point, product(
            range(start.x, end.x+1), range(start.y, end.y+1))):
        i = random.randint(0, 5) + [0, 1, 2, 7][self.bindex]
        boundary = p.y in (start.y, end.y)
        feat = (F_WALL if i == 6 and not boundary else
                F_FLOOR if i <= 4 else F_CHOKO)
        self.make_tile(p, feat)
    if self.bindex == 3:
        for t in fills:
            self.make_tile(t.pos, F_CHOKO)

def g_shoals(self):
    # These ranges magically guarantee connectedness.
    a = random.randrange(0, 19)
    b = random.randrange(0, 8)
    flip_x = coinflip()
    flip_y = coinflip()

    for p in self.coords:
        px = self.width  - 1 - p.x if flip_x else p.x
        py = self.height - 1 - p.y if flip_y else p.y
        fx, fy = float(p.x) / self.width, float(p.y) / self.height
        k = 5.0 * fx * (1 - fx) * fy * (1 - fy)
        h = ((math.sin(.30 * px + .09 * py + .1 * math.pi * a) + 1) -
             (math.sin(.43 * py - .15 * px + .1 * math.pi * b) - 1)) * k
        feat = F_WATER if h < 0.3 else F_FLOOR if h < 0.5 else F_WALL
        self.make_tile(p, feat)

    self.stairs_up   = self.spawn_feature(F_STAIRS_UP)
    self.stairs_down = self.spawn_feature(F_STAIRS_DOWN)

# Functions that modify generated levels.

def erode(self):
    range_x = range(1, self.width  - 1)
    range_y = range(1, self.height - 1)
    coords = list(product(range_x, range_y))

    for ix, iy in random.sample(coords, 5 * BOARD_WIDTH):
        p = Point(ix, iy)
        for d in DIRS:
            if self.tiles[p + d].feat.solid:
                continue
            if self.tiles[p].feat in (F_WALL, F_CLOSED_DOOR):
                self.make_tile(p, F_FLOOR)
                break
    for p in self.coords:
        if self.tiles[p].feat == F_CLOSED_DOOR:
            self.make_tile(p, F_FLOOR)

def water(self):
    water_area = 0
    while water_area < 50:
        e_w = random.randrange(3, 8)
        e_h = random.randrange(2, 5)
        border = max(e_w, e_h)
        e_a = random.random() * 2 * math.pi

        # Find a center point that is a floor tile.
        # This avoids making pools in the middle of nowhere
        while True:
            min_x = min_y = border + 1
            max_x = self.width  - border - 1
            max_y = self.height - border - 1
            e_x = random.randrange(min_x, max_x)
            e_y = random.randrange(min_y, max_y)

            if not self.tiles[e_x, e_y].feat.solid: break

        center = Point(e_x, e_y)
        for p in self.coords:
            if self.tiles[p].feat != F_WALL:
                continue
            if in_ellipse(p, center, e_a, e_w, e_h):
                self.make_tile(p, F_WATER)
                water_area += 1

def g_dungeon(self):
    ''' Mostly regular D layout (7 rooms), guaranteed and vault-free on D:1/2.
    Sometimes special layout (city, small cave-like, or large circular). '''
    if self.bindex < 2:
        g_rooms(7)(self)
    elif one_chance_in(16):
        g_vaults(self)
    elif one_chance_in(12):
        g_elliptic(12, 4)(self)
    elif one_chance_in(12):
        g_elliptic(5, 7)(self)
    else:
        g_rooms(7, make_vaults=True)(self)

def layout_orbchamber(self):
    # thanks HangedMan
    layout = [
        '########################################################',
        '##############......###############......###############',
        '############..........###########..........#############',
        '###########............##.....##............############',
        '############...........#..222..#...........#############',
        '#############.........2...202...2.........##############',
        '############...........#..222..#...........#############',
        '###########........2...##.....##...2........############',
        '############.........#############.........#############',
        '###############..#####################..################',
        '##############..........#######..........###############',
        '#############.......###....#....###........#############',
        '############.........###.......###..........############',
        '############.........###.......###..........############',
        '############........###.........###.........############',
        '#############......###...##+##...###.......#############',
        '##########################111###########################',
        '##########################1<1###########################',
        '##########################111###########################',#
        '########################################################',
    ]
    special_tiles = self.parse_layout(layout, PINK,
                                      self.branch.levels[-2])
    # Spawn monsters, but not in the entry room
    self.gen_mons(random.randint(15, 19))
    for t in special_tiles['1']:
        if t.monster:
            self.monsters.remove(t.monster)
            t.monster = None
    for t in special_tiles['2']:
        if not t.monster: self.gen_mons(1, tile=t)
    # TODO
    # Spawn a few Qs
    #/TODO
    # Spawn the orb
    special_tiles['0'][0].item = ORB_OF_ZOT

def layout_v5(self):
    layout = [list(l) for l in [
        '########################################################',
        '########################################################',
        '######...........................................#######',
        '######...###############.......###############...#######',
        '######..#A              #.....#A              #..#######',
        '######..#               #.....#               #..#######',
        '######..#               #.....#               #..#######',
        '######..#               #.....#               #..#######',
        '######...###############.......###############...#######',
        '######....................111....................#######',
        '######....................1<1....................#######',
        '######....................111....................#######',
        '######...###############.......###############...#######',
        '######..#A              #.....#A              #..#######',
        '######..#               #.....#               #..#######',
        '######..#               #.....#               #..#######',
        '######..#               #.....#               #..#######',
        '######...###############.......###############...#######',
        '######...........................................#######',
        '########################################################',
    ]]

    subvault_string = '''\
    ..#..2...#.....    ...2...#...2...    ...............    .#..#..#..#..#.
    ..#..#.0.#..#..    ...#..#0#..#...    ..###.202.###..    ...#..#2#..#...
    ..#..#...#..#..    ..###..#..###..    ..#####2#####..    ..#..#202#..#..
    .....#...2..#..    ...#.2...2.#...    ...............    .#..#..#..#..#.

    ...#.......#...    .....+2.2+.....    ..##...0...##..    .......2.......
    ..##..#2#..##..    .....+2.2+.....    ...##.2.2.##...    ...2.1...1.2...
    ..#..##0##..#..    .....+101+.....    ....##.2.##....    ...2...0...2...
    .....#2.2#.....    .....+2.2+.....    .......#.......    ......2.2......'''

    subvaults = []
    for block in subvault_string.split('\n\n'):
        m = [re.findall(r'\S+', line) for line in block.split('\n')]
        subvaults += zip(*m)

    random.shuffle(subvaults)
    start_points = [(x, y) for (y, l) in enumerate(layout)
                           for (x, c) in enumerate(l) if c == 'A']
    for (x, y), v in zip(start_points, subvaults):
        for i, l in enumerate(v[::-1 if coinflip() else 1]):
            layout[y+i][x:x+len(l)] = l

    special_tiles = self.parse_layout(layout, TEAL, self.branch.levels[-2])
    # Spawn monsters
    self.gen_mons(16)
    for t in special_tiles['1']:
        if not t.monster:
            self.spawn_monster(MONSMAP['vault guard'](), tile=t)
    for t in special_tiles['2']:
        if not t.monster: self.gen_mons(1, tile=t)

    # Spawn the rune and other items
    self.gen_items(6)
    random.shuffle(special_tiles['0'])
    special_tiles['0'][0].item = SILVER_RUNE
    for t in special_tiles['0'][1:]:
        t.item = ORB_OF_EXPERIENCE

def layout_slime3(self):
    layout = [
        '########################################################',
        '################..........................##############',
        '###############............................#############',
        '##############........555555..555555........############',
        '#############........5544445.55444455........###########',
        '############........55344445..54444355........##########',
        '###########........5544444455.544444455........#########',
        '##########........5544444445..5444444455........########',
        '#########.........5555555556.56555555555.........#######',
        '#########.<...........5....5.1..5.....5..........#######',
        '#########..........5.....5....5....5.............#######',
        '#########.........55555555565.6555555555.........#######',
        '##########........5544444445..5444444455........########',
        '###########........554444445.5544444455........#########',
        '############........55344445..54444355........##########',
        '#############........55444455.5444455........###########',
        '##############........555555..555555........############',
        '###############............................#############',
        '################..........................##############',
        '########################################################',
    ]
    special_tiles = self.parse_layout(layout, LIME, self.branch.levels[-2])
    trj   = special_tiles['1'][0]
    runes = special_tiles['3']
    loots = special_tiles['4']
    walls = special_tiles['5']
    doors = special_tiles['6']

    for t in walls + doors:
        t.col = GREY

    # Spawn TRJ and crew
    self.gen_mons(random.randint(18, 22))
    self.spawn_monster(RoyalJelly(doors), tile=trj)
    # ... but not in the loot rooms (removed with loot generation)

    # Spawn the rune
    random.shuffle(runes)
    runes[0].item = SLIMY_RUNE
    for t in runes[1:]:
        t.item = ORB_OF_EXPERIENCE

    # Other items (only inside the loot area)
    for t in loots:
        if t.monster:
            self.monsters.remove(t.monster)
            t.monster = None
        if coinflip(): continue
        t.item = random_potion()

def layout_surfac(self):
    # Thanks Sil
    layout = [
        '########################################################',
        '##########22.+....#######.......#######....+.22#########',
        '##########22.#.22.#.......#...#.......#.22.#.22#########',
        '##########22.#.22...#####...0...#####...22.#.22#########',
        '##########22.#....#.#.3.#.#...#.#.3.#.#....#.22#########',
        '###################.+.3.#.......#.3.+.##################',
        '##########...+.22.#.#################.#.22.+...#########',
        '##########.3.#.............................#.3.#########',
        '##########.3.############.#...#.############.3.#########',
        '##########.3.#...#444...+...4...+...444#...#.3.#########',
        '##########.3.#...#44...##.#...#.##...44#...#.3.#########',
        '##########.3.#...#44...##.......##...44#...#.3.#########',
        '###########################+++##########################',
        '##########################......########################',#
        '#########################...1...########################',
        '#######################..........#######################',
        '######################............######################',
        '###################.................####################',
        '##################.....................#.###############',
        '################............<.............##############',
    ]
    special_tiles = self.parse_layout(layout, TEAL, None)
    stair = special_tiles['0'][0]
    self.make_tile(stair, F_STAIRS_DOWN)
    self.stairs_down = stair
    mons = [
        ('1', MONSMAP['Murray']),    # C
        ('2', MONSMAP['ufetubus']),  # o
        ('3', MONSMAP['Quylthulg']), # f
        ('4', MONSMAP['Quylthulg']), # T
    ]
    for (num, monster) in mons:
        for t in special_tiles[num]:
            self.spawn_monster(monster(), tile=t)
    # XXX
    self.safe = False

## Branches and dungeon generation

class Branch(object):
    def __init__(self, name, depth, diff, gen, msgcol, reward):
        self.name     = name
        self.depth    = depth
        self.levels   = []

        self.wallcol, self.floorcol = BRANCH_COLORS[name]

        p('\n' if self.terse == 'Su' else (self.terse + ' ')[:2], msgcol)
        for i in range(depth):
            # last level is harder
            end_bonus = 30 if i == depth - 1 and self.name != 'Slime' else 0
            rel_diff = diff + i * 10 + end_bonus if diff > 0 else 0
            board = Board(self, i, rel_diff, gen)
            if i == depth - 1 and rel_diff > 0:
                board.gen_mons(random.randint(3, 7))
                for j in range(random.randint(3, 5)):
                    board.spawn_item(ORB_OF_EXPERIENCE)

            if i >= 1:
                # link with previous board
                board.stairs_up.target = self.levels[-1].stairs_down
                self.levels[-1].stairs_down.target = board.stairs_up
            self.levels.append(board)

        # color < of arrival...
        self.levels[0].stairs_up.col = BLUE

        # ...and staircase of penultimate level
        if self.depth > 1:
            self.levels[-2].stairs_down.col = BLUE
            self.levels[-1].stairs_up.col   = BLUE

        # remove > of last level
        last_down = self.levels[-1].stairs_down
        reward_tile = self.levels[-1].make_tile(last_down.pos, F_FLOOR)
        if reward is not None:
            reward_tile.item = reward

    @property
    def terse(self):
        return self.name[:2 if self.name.startswith('S') else 1]

    def link_branch(self, other, depth):
        self.levels[depth].link_branch(other)

def link(source, *dests):
   for (branch, (dmin, dmax)) in dests:
       source.link_branch(branch, random.randint(dmin, dmax))

def parse_options():
    global opts
    parser = OptionParser(add_help_option=False)
    o = parser.add_option
    o('-n', dest='name')
    o('-u', dest='name')

    # Now there's no way to disable this on Windows, but hey.
    is_win = platform.system() == "Windows"
    o('-e', action='store_true',  dest='encoding_friend', default=is_win)
    o('-f', action='store_const', dest='name', const="mausric f. nethack")
    o('-h', action='store_true',  dest='display_help',    default=False)
    o('-m', action='store_true',  dest='mummy',           default=False)
    o('-q', action='store_false', dest='show_help',       default=True)
    o('-w', action='store_const', dest='name',            const='wizard')
    o('-x', action='store_true',  dest='hard_mode',       default=False)

    opts, _ = parser.parse_args()
    if opts.display_help:
        print(parser.format_help())
        sys.exit('ok')

parse_options()

def box(curses_obj):
    curses_obj.border(*'||------' if opts.encoding_friend else [])

if not opts.name:
    print('Run as `fcrawl.py -nDelilah` to skip prompt for player name')

p('Generating dungeon... ', '0')

def die():
    print('\nYou abort the game.')
    sys.exit()

try:
    BARNACLED_RUNE  = Rune('four-cheese',  BROWN)
    DECAYING_RUNE   = Rune('mushroom',     DARKGREY)
    GOLDEN_RUNE     = Rune('pineapple',    YELLOW)
    GOSSAMER_RUNE   = Rune('onion-garlic', GREY)
    SILVER_RUNE     = Rune('margherita',   WHITE)
    SLIMY_RUNE      = Rune('pepperoni',    RED)
    SERPENTINE_RUNE = Rune('spinach',      GREEN)
    ORB_OF_ZOT      = Item('the Orb of Zot', '0', PINK)
    ANCIENT_CHOKO   = SparklyItem('the Ancient Choko', '%', light_colors)

    # Order here is important for HUD rune display
    RUNES = [GOLDEN_RUNE, BARNACLED_RUNE, DECAYING_RUNE, SERPENTINE_RUNE,
             GOSSAMER_RUNE, SILVER_RUNE, SLIMY_RUNE]
    UNIQUE_ITEMS = [ORB_OF_ZOT, ANCIENT_CHOKO]

    #                walls        floors
    BRANCH_COLORS = {
        'Dungeon':  (BROWN,     GREY),
        'Orc':      (BROWN,     BROWN),
        'Elf':      (BLUE,      GREY),
        'Lair':     (BROWN,     GREEN),
        'Swamp':    (BROWN,     GREEN),
        'Shoals':   (BROWN,     BROWN),
        'Snake':    (YELLOW,    LIME),
        'Spider':   (BROWN,     BROWN),
        'Slime':    (LIME,      GREEN),
        'Vaults':   (TEAL,      GREY),
        'Chokoban': (NAVY,      BLUE),
        'Tomb':     (GREY,      BROWN),
        'Zot':      (MAGENTA,   MAGENTA),
        'Surfac':   (GREY,      GREY),
    }

    def pick(*fs):
        return Chainable(lambda *a, **ka: random.choice(fs)(*a, **ka))

    g_orc    = pick(g_cave(800), g_elliptic(12, 4) >> erode)
    g_lair   = pick(g_cave(800), g_cave(1200), g_rooms(5)) >> erode
    g_swamp  = g_elliptic(20, 1, min_axis=1) >> water >> erode >> water
    g_spider = pick(g_cave(1000), g_elliptic(11, 5)) >> erode >> erode >> water
    g_slime  = g_elliptic(12, 6, min_axis=3)
    g_elf    = g_rooms(15, min_stair_dist=30)
    g_tomb   = g_rooms(30, min_stair_dist=20)
    g_zot    = g_rooms(8, min_stair_dist=30)

    #                  name    depth  diff  layoutgen         reward
    B_DUNGEON = Branch('Dungeon', 10,  50, g_dungeon,   '33', None)
    B_LAIR    = Branch('Lair',     5,  90, g_lair,      '32', None)
    B_SHOALS  = Branch('Shoals',   3, 190, g_shoals,  '1;34', BARNACLED_RUNE)
    B_SNAKE   = Branch('Snake',    3, 190, g_rooms(8),'1;33', SERPENTINE_RUNE)
    B_SWAMP   = Branch('Swamp',    3, 200, g_swamp,   '1;30', DECAYING_RUNE)
    B_SPIDER  = Branch('Spider',   3, 200, g_spider,    '37', GOSSAMER_RUNE)
    B_SLIME   = Branch('Slime',    3, 210, g_slime,   '1;32', SLIMY_RUNE)
    B_ORC     = Branch('Orc',      3, 100, g_orc,     '1;31', None)
    B_ELF     = Branch('Elf',      3, 200, g_rooms(15), '31', None)
    B_VAULTS  = Branch('Vaults',   5, 190, g_vaults,    '36', SILVER_RUNE)
    B_CHOKO   = Branch('Chokoban', 4,   0, g_choko,   '1;37', ANCIENT_CHOKO)
    B_TOMB    = Branch('Tomb',     3, 300, g_tomb,    '1;35', GOLDEN_RUNE)
    B_ZOT     = Branch('Zot',      3, 300, g_zot,       '35', ORB_OF_ZOT)
    B_SURFAC  = Branch('Surfac',   1,  20, g_rooms(1),    '', None)

    BRANCHES = [B_DUNGEON, B_LAIR, B_SHOALS, B_SNAKE, B_SWAMP, B_SPIDER,
        B_SLIME, B_ORC, B_ELF, B_VAULTS, B_CHOKO, B_TOMB, B_ZOT, B_SURFAC]

    # The only vault in the game!
    layout_orbchamber(B_ZOT.levels[-1])
    # Except not any more!
    layout_v5(B_VAULTS.levels[-1])
    layout_slime3(B_SLIME.levels[-1])
    layout_surfac(B_SURFAC.levels[0])

    # Give Elf:3 extra loot and enemies; it's optional and difficult
    for _ in range(3): B_ELF.levels[-1].spawn_monster(MONSMAP['goldragon']())
    B_ELF.levels[-1].spawn_monster(MONSMAP['sphinx']())
    B_ELF.levels[-1].gen_items(15)

    # Make Tomb:3 extra hard.
    B_TOMB.levels[-1].gen_mons(14)

    # startscumming??
    start_potions = [P_ALCHEMY] + random.sample(POTIONS, 3)
    for p in start_potions:
        B_DUNGEON.levels[0].spawn_item(p)

    if not opts.hard_mode:
        B_DUNGEON.levels[0].spawn_item(ORB_OF_EXPERIENCE)

    if opts.hard_mode:
        # This intentionally skips D:1
        for i in random.sample(range(2, len(B_DUNGEON.levels)), 5):
            hard_mode_potions = random.sample(POTIONS, 2)
            B_DUNGEON.levels[i-1].spawn_item(p)

    lair_branches = [B_SWAMP, B_SHOALS, B_SNAKE, B_SPIDER, B_SLIME]

    link(B_DUNGEON, (B_LAIR,   (2, 5)),
                    (B_ORC,    (3, 6)),
                    (B_VAULTS, (6, 8)),
                    (B_ZOT,    (B_DUNGEON.depth - 1, B_DUNGEON.depth - 1)))
    link(B_ORC,     (B_ELF,    (1, 2)))
    link(B_LAIR,    *[(b, (1, 4)) for b in lair_branches])
    link(B_VAULTS,  (B_TOMB,   (2, 4)),
                    (B_CHOKO,  (1, 3)))
except KeyboardInterrupt as e:
    die()

## Dungeon linked, start game

def ask(msg):
    msgbox.scroll(1)
    msgbox.refresh()
    msgbox.addstr(MSG_HEIGHT-1, 0, msg)
    msgbox.refresh()
    return stdscr.getkey()

def color_pairs():
    # Initialize colors
    curses.init_pair(1, curses.COLOR_BLUE,    curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN,   curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED,     curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_YELLOW,  curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE,   curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_BLACK,   curses.COLOR_BLACK)

    return {
        NAVY         : curses.color_pair(1),
        GREEN        : curses.color_pair(2),
        TEAL         : curses.color_pair(3),
        MAROON       : curses.color_pair(4),
        MAGENTA      : curses.color_pair(5),
        BROWN        : curses.color_pair(6),
        GREY         : curses.color_pair(7),
        DARKGREY     : curses.color_pair(8) | curses.A_BOLD,
        BLUE         : curses.color_pair(1) | curses.A_BOLD,
        LIME         : curses.color_pair(2) | curses.A_BOLD,
        AQUA         : curses.color_pair(3) | curses.A_BOLD,
        RED          : curses.color_pair(4) | curses.A_BOLD,
        PINK         : curses.color_pair(5) | curses.A_BOLD,
        YELLOW       : curses.color_pair(6) | curses.A_BOLD,
        WHITE        : curses.color_pair(7) | curses.A_BOLD,
    }

def create_char():
    name = opts.name
    show_help = opts.show_help
    mummy = opts.mummy

    if not name:
        prompt = curses.newwin(3, 34, 5, 22)
        prompt.clear()
        box(prompt)
        prompt.addstr(1, 2, "What's your name? ", cp[TEAL])
        prompt.refresh()

        entry = curses.newwin(1, 13, 6, 42)
        curses.echo()
        name = entry.getstr().decode(encoding="utf-8") or os.getlogin()
        curses.noecho()

    player = Player(name[:18], mummy=mummy)
    player.show_help = show_help
    player.board = B_DUNGEON.levels[0]
    player.board.stairs_up.monster = player
    player.pos = player.board.stairs_up.pos
    player.calculate_los()
    return player

def update_status():
    raw_pr = lambda *stuff: stdscr.addstr(yoff, xoff, *stuff)
    pr = lambda text, col=GREY, reverse=False: \
            raw_pr(text, cp[col] | (curses.A_REVERSE if reverse else 0))

    xoff = HUD_START
    yoff = 0

    # Character name
    pr('%s' % player.desc[:HUD_WIDTH], PINK if opts.hard_mode else YELLOW)

    xoff = HUD_START
    yoff += 1
    # HP bar
    disp_hp = max(0, player.hp)
    last_hp = max(0, player.last_hp)
    bar_width = 22
    bars = int(bar_width * disp_hp // player.mhp)
    last = int(bar_width * last_hp // player.mhp)
    pr('-' * bar_width, DARKGREY)
    pr('=' * last, DARKGREY)
    pr('=' * bars, player.hp_col)

    # HP and Place
    xoff = HUD_START
    yoff += 1

    pr('HP:', BROWN)
    xoff += 3
    pr('%4d' % math.ceil(disp_hp), player.hp_col)
    xoff += 4
    pr(':%-4d' % player.mhp, GREY)
    xoff += 5
    pr('%10s'% player.board.name, GREEN if player.board.safe else BROWN)

    # Status line
    # (has_digits, when_to_display, displayname, text_color, textcol_as_bg)
    status_line = [
    [
        (True,  player.speed_time,    'Fast',  P_SPEED.col,   False),
        (True,  player.slow_time,     'Slow',  MAGENTA,     False),
        (True,  player.mark_time,     'Mark',  MAGENTA,     True),
        (True,  player.phase_time,    'Phase', P_PHASING.col, False),
    ],
    [
        (False, player.win,           '**WIN**',  YELLOW, True),
        (False, player.danger_hp,     ' Low HP ', MAROON,    True),
        (False, player.board.no_tele, '-Tele', P_TELEPORTATION.col, True),
        (True,  player.contam,        'Contam',YELLOW,    False),
        (False, player.flies,         'Fly', P_PHASING.col, False),
    ],
    ]
    for things in status_line:
        xoff = HUD_START
        yoff += 1
        pr(' ' * HUD_WIDTH)
        for (digits, status, name, color, reverse) in things:
            if not status:
                continue
            if digits:
                name = name + '%2d' % status
            if xoff + len(name) > HUD_WIDTH + HUD_START:
                continue
            pr(name, color, reverse=reverse)
            xoff += len(name) + 1 # uh oh

    # Inventory: [6 magic mapping x99 (5) ]
    for i, p in enumerate(POTIONS, start=1):
        xoff = HUD_START
        yoff += 1
        amount = player.items[p]
        useless = any((
            player.phase_time > 0,
            p in player.forbidden_items,
            p == P_SPEED and (player.speed_time or player.contam),
            p == P_PHASING and player.contam,
            p == P_TELEPORTATION and player.board.no_tele,
            p == P_MAGIC_MAPPING and player.board.mapped,
        ))

        TIMES = 'x%-2s' if opts.encoding_friend else u'\u00d7%-2s'
        potion_count = TIMES % amount

        name_col   = GREY if amount and not useless else DARKGREY
        amount_col = p.col  if amount else DARKGREY

        pr(str(0 if p == P_ALCHEMY else i), amount_col)
        xoff += 2
        pr('%-13s' % p.terse, name_col)
        xoff += 14
        pr(potion_count.encode(code), amount_col)
        xoff += 3

        if p.alchemic_known:
            pr('(%s)' % p.alchemic, DARKGREY)

    # Monster list
    yoff += 1
    sorted_monlist = sorted(player.monsters_seen, key=attrgetter('xl'),
                    reverse=True)[:LEN_MONSTER_LIST]
    for i in range(LEN_MONSTER_LIST):
        xoff = HUD_START
        yoff += 1
        pr(' ' * HUD_WIDTH)
        if i >= len(sorted_monlist):
            continue

        m = sorted_monlist[i]
        warnings = [(m.fast, 'f'), (m.ranged, 'r')]
        marker = next((ch for (cond, ch) in warnings if cond), ' ')
        pr(marker, m.hp_col, reverse=True)

        bad = (m.attack != Actor.attack and
               (m.ranged or m.attack not in (a_blink, a_trample)))
        mons_difficulty = 2 * (1 + m.xl
                                   * (2.2 if m.fast else 1.3)
                                   * (1.4 if m.ranged else 1)
                                   * (1.5 if bad else 1))
        if   mons_difficulty > 3 * player.xl:
            danger_col = RED
        elif mons_difficulty > 2 * player.xl:
            danger_col = YELLOW
        elif mons_difficulty > 1 * player.xl:
            danger_col = GREY
        else:
            danger_col = DARKGREY

        xoff += 2
        pr(m.char, m.color); xoff += 2
        if player.view_hits:
            a_min = math.ceil(m.hp / (player.xl * math.exp(0.1)))
            a_max = math.ceil(m.hp / (player.xl * math.exp(-0.1)))
            d_min = math.ceil(player.hp / (m.attack_xl * math.exp(0.1)))
            d_max = math.ceil(player.hp / (m.attack_xl * math.exp(-0.1)))
            a_str = '%d-%d ' % (a_min, a_max)
            pr(a_str, BLUE); xoff += len(a_str)
            d_str = '%d-%d' % (d_min, d_max)
            pr(d_str, RED); xoff += len(d_str)

        else:
            pr(m.name, danger_col)
            xoff += len(m.name)

            if m.af:
                namelen = len(m.af) + 2
                if xoff + namelen < HUD_WIDTH + HUD_START:
                    xoff += 1
                pr('(%s)' % m.af, danger_col)
                xoff += namelen + 1

    xoff = HUD_START
    yoff += 2
    if player.runes:
        rune_legend = "Pizza: %d " % player.runes
        pr(rune_legend, BROWN)
        xoff += len(rune_legend) + 2

        for item in RUNES:
            name = item.terse
            if not player.items.get(item):
                name = ' ' * len(name)
            pr(name, item.col)
            xoff += len(name) + 1
            if xoff - HUD_START > 16:
                xoff = HUD_START
                yoff += 1

    xoff = HUD_START
    for item in UNIQUE_ITEMS:
        name = item.pname
        if not player.items.get(item):
            name = ' ' * len(name)
        pr(name, item.col)
        yoff += 1

    stdscr.move(player.pos.y, player.pos.x)

def player_cmd():
    while True:
        if player.running:
            stdscr.refresh()
            cmd = player.running
            for monster in player.board.monsters:
                tile = monster.here
                if player.can_see(tile.pos):
                    player.running = None
                    break

        if not player.running:
            cmd = stdscr.getkey()

        if cmd in MOVEMENT:
            return player.dir(MOVEMENT[cmd])
        elif cmd.lower() in MOVEMENT:
            player.running = cmd.lower()

        if cmd in 's.':
            player.get_item(player.here)
            return True

        if cmd == '>': return player.use_stairs(F_STAIRS_DOWN)
        if cmd == '<': return player.use_stairs(F_STAIRS_UP)
        if cmd in 'gG': return player.warp()
        if cmd in '_:': return player.notes()

        if cmd in '1234560' and player.phase_time:
            potion = POTIONS[int(cmd) - 1]
            msg("Ghosts can't %s!" % player.quaffname(potion), MAROON)
            return False

        if cmd in '123456':
            potion = POTIONS[int(cmd) - 1]
            return player.use_item(potion)

        if cmd == '0':
            if player.check_item(P_ALCHEMY):
                return p_alchemy()
            else:
                return False

        if cmd in 'xv':
            player.view_hits = not player.view_hits
            return False

        if cmd == '!':
            if player.wizard:
                for i in player.board.monsters[:]:
                    i.die_to(player)
                return True
            else:
                show_hints()
                return False

        if player.wizard:
            if cmd == '+':
                player.gain_level()
                player.last_hp = player.hp
                return False
            if cmd == '-':
                player.lose_level()
                player.last_hp = player.hp
                return False

        if cmd == '?':
            show_help()
            return False
        if cmd == ' ':
            return False

def show_help():
    msg(    'There is no resting. Defeat dudes to heal. Go deeper!', WHITE)
    msg(    ' [hjklyubn] move  [s.] wait  [<>] stairs  [gG] warp')
    msg(    ' [HJKLYUBN] run   [1234560] quaff potion  [?!] help')
    if player.wizard:
        msg(' [!] defeat dudes [+-] gain / lose level', MAGENTA)
    else:
        msg(' [!] show hints   [ ] read more messages  [:_] chat')
def show_hints():
    msg(    'Press [!] again to see different hints about the game.', WHITE)
    for i in range(3):
        color, hint = HINTS.popleft()
        msg(hint, col=color)
        HINTS.append((color, hint))

def mons_turn(self):
    if not player.dead:
        self.act(player)

def player_turn(self):
    turn_spent = False

    while not turn_spent:
        # Set if the player's turn is completed by an action
        turn_spent = player_cmd()

        if turn_spent:
            xwalls = defaultdict(int)
            ywalls = defaultdict(int)
            # Stopping at open doors is intentional.
            if player.here.feat != F_FLOOR:
                player.running = None
            elif player.running:
                for (move, d) in MOVEMENT.iteritems():
                    cand = self.board.tiles[player.pos + d]
                    if cand.feat in (F_FLOOR, F_OPEN_DOOR):
                        continue
                    # Keep track of adjacent walls to find corridor stops.
                    if cand.feat == F_WALL:
                        xwalls[d.x] += 1
                        ywalls[d.y] += 1
                        continue
                    # If the next move into the same direction would get
                    # us on top of the feature in question, keep running.
                    # (But closed doors you might want to keep closed.)
                    if move == player.running and \
                            cand.feat != F_CLOSED_DOOR:
                        continue
                    # We are fleeeeing from the feature, but walking away
                    # moves us "next to" the very same feature again. Do
                    # not artificially stop in this case (feels awkward).
                    if d == -MOVEMENT.get(player.running, 0):
                        continue
                    player.running = None

                in_corridor = (
                        sum(am >= 2 for x,am in xwalls.items()) == 2
                    and sum(am >= 2 for y,am in ywalls.items()) == 2
                    and sum(am == 3 for x,am in xwalls.items()) <= 1
                    and sum(am == 3 for y,am in ywalls.items()) <= 1
                )
                lone_corridors = ({-1: 2}, {1: 2})
                near_x_corr = (len(ywalls) == 2 and sum(ywalls) == 0
                               and xwalls in lone_corridors)
                near_y_corr = (len(xwalls) == 2 and sum(xwalls) == 0
                               and ywalls in lone_corridors)
                near_corridor = near_x_corr or near_y_corr
                # Note: != does the XOR job
                if in_corridor != near_corridor:
                    player.running = None
        elif player.running:
            player.running = None

        # A level is considered "safe" if all enemies have been defeated.
        if not player.board.monsters and not player.board.safe:
            safe = 'You feel safe.'
            more = False
            # Tell players how they can proceed. Additionally, if
            # the next level is much harder than this one, print a
            # warning message and force player confirmation.
            if self.board.stairs_down.target:
                if self.board.stairs_down.target.board.is_branch_end:
                    safe += ' (Branch end ahead!)'
                    more = True
                else:
                    safe += ' (Press > to go down.)'
            msg(safe, GREEN, more=more)
            # One free potion of wounds quaff if you could use it.
            # (To not print a confusing "You feel queasy." message.)
            if player.hp != player.mhp:
                p_heal_wounds(player)
            # One experience level for this achievement!
            player.gain_level()
            msg('%s.' % ORB_OF_EXPERIENCE.name, TEAL)
            # You can now warp from and to this level.
            player.board.safe = True
            player.board.no_tele = False
            player.warp_board.add(player.board)

            for ix, iy in player.board.coords:
                player.get_item(player.board.tiles[ix, iy])
            player.board.magic_mapping()

        update_screen()
        if turn_spent:
            player.last_hp = player.hp

def print_messages():
    yoff = MSG_HEIGHT - 1
    more = '-More-'
    xoff_more = MSG_WIDTH - len(more)
    msg_i = 0
    for text, color, force_more in msg_buf:
        msgbox.scroll(1)
        msgbox.refresh()
        msgbox.addstr(yoff, 0, text, cp[color])
        msgbox.refresh()
        msg_i += 1
        if (msg_i % MSG_HEIGHT == 0 and len(msg_buf) != msg_i
                or force_more):
            msgbox.addstr(yoff, xoff_more, more, curses.A_STANDOUT)
            msgbox.refresh()
            while stdscr.getch() not in (ord(' '), 27): pass
            msgbox.addstr(yoff, xoff_more, ' ' * len(more))
            msgbox.refresh()
            msg_i = 0

    del msg_buf[:]

def update_screen():
    if player.dead:
        msg('Press space to quit.', DARKGREY)

    print_messages()

    # Update LOS
    player.monsters_seen = []
    for p in player.board.coords:
        t = player.board.tiles[p]
        t.visible = False
        if not player.can_see(p):
            continue
        t.visible = True
        t.known   = True
        if p == player.pos:
            continue
        if t.monster:
            player.monsters_seen.append(t.monster)

    # Draw board
    for p in player.board.coords:
        co, ch = player.board.tiles[p].display(player)
        co, ch = cp[co], ord(ch)
        stdscr.addch(BOARD_Y + p.y, BOARD_X + p.x, ch, co)

    update_status()

def main(screen):
    try:
        global stdscr, msgbox, cp, player
        stdscr = screen
        curses.curs_set(0)

        msgbox = curses.newwin(MSG_HEIGHT, MSG_WIDTH+1, MSG_Y, BOARD_X)
        msgbox.clear()
        msgbox.scrollok(True)

        cp = color_pairs()
        player = create_char()
        update_screen()
        if player.show_help:
            show_help()
            stdscr.refresh()
            print_messages()
    except KeyboardInterrupt:
        die()
    while True:
        try:
            player.take_turn(player_turn)
            for m in player.board.monsters:
                m.take_turn(mons_turn)
        except KeyboardInterrupt:
            msg('You quit the game.', RED)
            player.dead = True
            if player.runes:
                player.killer = 'quit in peace'
            else:
                player.killer = 'quit in disgust'

        update_screen()
        if player.dead:
            while stdscr.getch() != ord(' '): pass
            return

curses.wrapper(main)

score_test = '''\
%4d %s[L%2d, %1d pizza] %s on %s''' % (
    27,
    (player.name + ' ')[:16], # lets hope this works
    player.xl,
    player.runes,
    #'' if player.runes == 1 else 's',
    player.killer,
    player.board.name,
)
goodbye = '''\
%s%s%s
    ... %s on %s (%s pizza)%s%s''' % (
    player.desc,
    '***WINNER***' if player.win else '',
    '' if not player.items.get(ANCIENT_CHOKO) else '''
    ... aided by the ancient forces of choko''',
    player.killer,
    player.board.name,
    player.runes,
    #'' if player.runes == 1 else 's',
    '' if not opts.hard_mode else '''
    ... in HARD mode''',
    '' if not opts.mummy else '''
    ... wrapped in bandages and carrying a bladder''',
)
print(goodbye)
if player.xl >= BASE_XL + SCORING_XL and not player.wizard:
    with open('my-fcrawl-games.txt', 'a') as f:
        now = datetime.now().strftime('%Y-%m-%d[%H:%M:%S]\n')
        f.write(now + goodbye + '\n')
