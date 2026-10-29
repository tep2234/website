"""Chibi 'AI engineer Alvin' sprite sheet generator.

    python3 tools/make-chibi-sprite.py --site   # rebuild assets/img/alvin-sprite.webp used by assets/js/chibi.js
    python3 tools/make-chibi-sprite.py          # stand-alone 8x5 sheets + GIF previews in tools/out/


Draws every frame as SVG (so the character stays identical frame to frame), renders the
frames with Chromium, and writes:
  out/alvin-sprite.png      8 columns x 5 rows, 256 px cells, transparent
  out/alvin-sprite@2x.png   same at 512 px cells
  out/alvin-<anim>.gif      one preview per animation
Rows: 0 idle, 1 wave, 2 typing, 3 idea, 4 celebrate.
"""
import math, asyncio, pathlib, io
from playwright.async_api import async_playwright
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "out"   # previews and the stand-alone sheets (not published)
OUT.mkdir(exist_ok=True)
N = 8
CELL = 256
ANIMS = ["idle", "wave", "typing", "idea", "celebrate"]
# site sheet: 9 columns; the 'look' row has 9 frames (a 3x3 grid of gaze directions)
LOOKS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
SITE_ROWS = ["idle", "wave", "typing", "idea", "celebrate", "point", "thumbs", "worried", "resume", "confused", "look"]

SKIN, SKIN_SH, SKIN_HI = "#EDC3A0", "#D9A07D", "#F6D6BA"
HAIR, HAIR_HI, FADE = "#16131A", "#3A3440", "#5E5250"
SUIT, SUIT_SH, SUIT_HI = "#1C1C22", "#121216", "#2E2E37"
SHIRT = "#26262D"
RED = "#C8202B"
LIP = "#C98479"
INK = "#1A1214"
BOT, BOT_SH = "#F2A516", "#C98410"
GLOW = "#5BE3FF"

def ease(x):  # smooth 0..1..0 loop helper
    return 0.5 - 0.5 * math.cos(2 * math.pi * x)

def arm(sx, sy, ang, sleeve=SUIT, w=19, L=40, front=True, thumb=False, finger=False):
    """Arm hanging from (sx,sy) rotated by ang degrees (0 = straight down)."""
    return (f'<g transform="translate({sx:.1f},{sy:.1f}) rotate({ang:.1f})">'
            f'<rect x="{-w/2}" y="-6" width="{w}" height="{L}" rx="{w/2}" fill="{sleeve}"/>'
            f'<rect x="{-w/2+3}" y="{L-12}" width="{w-6}" height="6" rx="3" fill="{SHIRT}"/>'
            f'<circle cx="0" cy="{L+3}" r="9.5" fill="{SKIN}"/>'
            f'<circle cx="-3" cy="{L+1}" r="3" fill="{SKIN_HI}" opacity=".6"/>'
            + (f'<rect x="-3.6" y="{L+5}" width="7.2" height="13" rx="3.6" fill="{SKIN}"/>' if thumb else '')
            + (f'<rect x="-2.8" y="{L+6}" width="5.6" height="15" rx="2.8" fill="{SKIN}"/>' if finger else '')
            + '</g>')

def eyes(hx, hy, mode="open", look=(0, 0)):
    lx, ly = look
    out = []
    for s in (-1, 1):
        ex, ey = hx + s * 23, hy + 12
        if mode == "blink":
            out.append(f'<path d="M{ex-10},{ey+1} Q{ex},{ey+5} {ex+10},{ey+1}" stroke="{INK}" stroke-width="3.2" fill="none" stroke-linecap="round"/>')
        elif mode == "happy":
            out.append(f'<path d="M{ex-9},{ey+3} Q{ex},{ey-8} {ex+9},{ey+3}" stroke="{INK}" stroke-width="3.6" fill="none" stroke-linecap="round"/>')
        else:
            # almond eye: slightly narrow, outer corner lifted (from the photo), big chibi pupil
            tilt = -2 * s
            out.append(f'<g transform="rotate({tilt} {ex} {ey})">'
                       f'<ellipse cx="{ex}" cy="{ey}" rx="10.5" ry="8.6" fill="#FFFFFF"/>'
                       f'<ellipse cx="{ex+lx}" cy="{ey+ly}" rx="7.4" ry="8.2" fill="#3B2620"/>'
                       f'<ellipse cx="{ex+lx}" cy="{ey+ly+.5}" rx="4.6" ry="5.4" fill="{INK}"/>'
                       f'<circle cx="{ex+lx+2.6}" cy="{ey+ly-3}" r="2.6" fill="#fff"/>'
                       f'<circle cx="{ex+lx-2.4}" cy="{ey+ly+3}" r="1.2" fill="#fff" opacity=".9"/>'
                       # upper lid line (gives the almond, slightly hooded look)
                       f'<path d="M{ex-11.5},{ey+1} Q{ex-2},{ey-11.5} {ex+11.5},{ey-2.5}" stroke="{INK}" stroke-width="3" fill="none" stroke-linecap="round"/>'
                       f'</g>')
    return "".join(out)

def mouth(hx, hy, mode="smile"):
    my = hy + 34
    stache = (f'<path d="M{hx-9},{my-5} Q{hx},{my-8.5} {hx+9},{my-5}" stroke="{HAIR}" stroke-width="2" '
              f'fill="none" stroke-linecap="round" opacity=".35"/>')
    if mode == "open":
        return stache + (f'<path d="M{hx-9},{my-1} Q{hx},{my-1.5} {hx+9},{my-1} Q{hx+7},{my+11} {hx},{my+11} Q{hx-7},{my+11} {hx-9},{my-1}Z" fill="#7A2E33"/>'
                         f'<ellipse cx="{hx}" cy="{my+7.5}" rx="5" ry="3" fill="#E77A80"/>'
                         f'<rect x="{hx-6}" y="{my-1}" width="12" height="3" rx="1.5" fill="#fff"/>')
    if mode == "o":
        return stache + f'<ellipse cx="{hx}" cy="{my+2}" rx="4" ry="4.6" fill="#7A2E33"/>'
    if mode == "side":
        return stache + f'<path d="M{hx-7},{my+3} Q{hx+1},{my+1} {hx+8},{my-2}" stroke="{LIP}" stroke-width="3.2" fill="none" stroke-linecap="round"/>'
    if mode == "wobble":
        return stache + f'<path d="M{hx-8},{my+2} q2.7,-3 5.3,0 t5.3,0 t5.3,0" stroke="{LIP}" stroke-width="3" fill="none" stroke-linecap="round"/>'
    if mode == "focus":
        return stache + f'<path d="M{hx-6},{my+1} Q{hx},{my+3} {hx+6},{my+1}" stroke="{LIP}" stroke-width="3.2" fill="none" stroke-linecap="round"/>'
    # soft closed smile with full lower lip
    return stache + (f'<path d="M{hx-9},{my} Q{hx},{my+7} {hx+9},{my}" stroke="{LIP}" stroke-width="3.4" fill="none" stroke-linecap="round"/>'
                     f'<path d="M{hx-4},{my+5.5} Q{hx},{my+7.5} {hx+4},{my+5.5}" stroke="{SKIN_SH}" stroke-width="2" fill="none" stroke-linecap="round" opacity=".7"/>')

def head(hx, hy, eye="open", mth="smile", look=(0, 0), brow=0, tuft=0, glow=False, btilt=0, sweat=None):
    p = []
    # ears
    for s in (-1, 1):
        p.append(f'<ellipse cx="{hx+s*58}" cy="{hy+10}" rx="10" ry="13" fill="{SKIN}"/>'
                 f'<ellipse cx="{hx+s*59}" cy="{hy+10}" rx="5" ry="7.5" fill="{SKIN_SH}" opacity=".7"/>')
    # face: round chibi cheeks, slightly squared jaw
    p.append(f'<path d="M{hx-56},{hy-6} C{hx-58},{hy+30} {hx-40},{hy+52} {hx},{hy+56} C{hx+40},{hy+52} {hx+58},{hy+30} {hx+56},{hy-6} '
             f'C{hx+54},{hy-44} {hx-54},{hy-44} {hx-56},{hy-6}Z" fill="{SKIN}"/>')
    p.append(f'<ellipse cx="{hx-20}" cy="{hy-14}" rx="16" ry="8" fill="{SKIN_HI}" opacity=".45"/>')
    # faded undercut on the sides
    for s in (-1, 1):
        p.append(f'<path d="M{hx+s*57},{hy-4} C{hx+s*58},{hy-20} {hx+s*55},{hy-30} {hx+s*48},{hy-36} L{hx+s*44},{hy-12} C{hx+s*48},{hy-8} {hx+s*52},{hy-4} {hx+s*55},{hy+4}Z" fill="{FADE}" opacity=".55"/>')
    # textured, voluminous top swept to his right (viewer's left)
    top = (f'M{hx-52},{hy-20} C{hx-60},{hy-50} {hx-44},{hy-74} {hx-14},{hy-78} '
           f'C{hx+6},{hy-90} {hx+40},{hy-84} {hx+50},{hy-62} C{hx+60},{hy-50} {hx+56},{hy-30} {hx+48},{hy-18} '
           f'C{hx+40},{hy-30} {hx+30},{hy-30} {hx+22},{hy-26} C{hx+14},{hy-36} {hx},{hy-34} {hx-8},{hy-28} '
           f'C{hx-18},{hy-34} {hx-34},{hy-32} {hx-40},{hy-24} C{hx-44},{hy-28} {hx-50},{hy-26} {hx-52},{hy-20}Z')
    p.append(f'<path d="{top}" fill="{HAIR}"/>')
    # curl clumps for texture (wavy, like the photo)
    for cx, cy, r in [(-34, -62, 13), (-14, -72, 14), (8, -76, 14), (30, -68, 13), (44, -52, 11), (-44, -44, 11), (-24, -46, 10), (16, -52, 10)]:
        p.append(f'<circle cx="{hx+cx}" cy="{hy+cy}" r="{r}" fill="{HAIR}"/>')
    for cx, cy in [(-28, -64), (-6, -74), (18, -72), (36, -58), (-38, -46), (4, -56)]:
        p.append(f'<path d="M{hx+cx-6},{hy+cy+3} q6,-7 12,0" stroke="{HAIR_HI}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    # bouncy cowlick
    p.append(f'<path transform="rotate({tuft} {hx+6} {hy-82})" d="M{hx+2},{hy-80} C{hx},{hy-96} {hx+16},{hy-102} {hx+22},{hy-96} C{hx+12},{hy-96} {hx+10},{hy-88} {hx+12},{hy-80}Z" fill="{HAIR}"/>')
    # thick straight brows
    for s in (-1, 1):
        p.append(f'<rect x="{hx+s*23-11}" y="{hy-6-brow}" width="22" height="5.5" rx="2.75" fill="{HAIR}" transform="rotate({-3*s+btilt*s} {hx+s*23} {hy-4})"/>')
    p.append(eyes(hx, hy, eye, look))
    # nose and blush
    p.append(f'<path d="M{hx-4},{hy+24} Q{hx},{hy+27} {hx+4},{hy+24}" stroke="{SKIN_SH}" stroke-width="2.6" fill="none" stroke-linecap="round"/>')
    for s in (-1, 1):
        p.append(f'<ellipse cx="{hx+s*36}" cy="{hy+28}" rx="9" ry="5" fill="#F2847C" opacity=".38"/>')
    p.append(mouth(hx, hy, mth))
    if sweat is not None:
        sy = hy - 20 + sweat
        p.append(f'<path d="M{hx+50},{sy} q6,9 0,13 q-6,-4 0,-13Z" fill="#9FDFFF" stroke="#5BB8E6" stroke-width="1.2"/>')
    if glow:
        p.append(f'<path d="M{hx-56},{hy-6} C{hx-58},{hy+30} {hx-40},{hy+52} {hx},{hy+56} C{hx+40},{hy+52} {hx+58},{hy+30} {hx+56},{hy-6}Z" fill="{GLOW}" opacity=".12"/>')
    return "".join(p)

def body(bx, by, squash=0):
    """Torso: black suit, black shirt, red pocket square. (bx,by) = neck point."""
    w = 42 + squash
    t = []
    t.append(f'<path d="M{bx-w},{by+12} C{bx-w},{by} {bx-w+12},{by-4} {bx},{by-4} C{bx+w-12},{by-4} {bx+w},{by} {bx+w},{by+12} '
             f'L{bx+w-2},{by+58} Q{bx+w-2},{by+66} {bx+w-10},{by+66} L{bx-w+10},{by+66} Q{bx-w+2},{by+66} {bx-w+2},{by+58}Z" fill="{SUIT}"/>')
    # shirt V and collar
    t.append(f'<path d="M{bx-15},{by-3} L{bx},{by+34} L{bx+15},{by-3}Z" fill="{SHIRT}"/>')
    t.append(f'<path d="M{bx-15},{by-3} L{bx-2},{by+10} L{bx-9},{by+15}Z M{bx+15},{by-3} L{bx+2},{by+10} L{bx+9},{by+15}Z" fill="#33333B"/>')
    # lapels
    t.append(f'<path d="M{bx-16},{by-3} L{bx-1},{by+36} L{bx-12},{by+28} L{bx-24},{by+8}Z" fill="{SUIT_HI}"/>'
             f'<path d="M{bx+16},{by-3} L{bx+1},{by+36} L{bx+12},{by+28} L{bx+24},{by+8}Z" fill="{SUIT_HI}"/>')
    # button, pocket, red pocket square
    t.append(f'<circle cx="{bx}" cy="{by+46}" r="2.6" fill="#3E3E48"/>')
    t.append(f'<rect x="{bx+18}" y="{by+22}" width="16" height="3" rx="1.5" fill="{SUIT_SH}"/>'
             f'<path d="M{bx+20},{by+22} l3,-6 l3,4 l3,-5 l3,7Z" fill="{RED}"/>')
    # tiny 'AI' pin on the left lapel
    t.append(f'<circle cx="{bx-19}" cy="{by+16}" r="5" fill="{BOT}"/><text x="{bx-19}" y="{by+18.4}" text-anchor="middle" font-family="Arial" font-weight="900" font-size="6" fill="{INK}">AI</text>')
    return "".join(t)

def legs(bx, base, lift=(0, 0)):
    l = []
    for s, lf in ((-1, lift[0]), (1, lift[1])):
        x = bx + s * 15
        l.append(f'<rect x="{x-9}" y="{base-34-lf}" width="18" height="28" rx="6" fill="{SUIT_SH}"/>'
                 f'<ellipse cx="{x+s*2}" cy="{base-5-lf}" rx="13" ry="7" fill="#0C0C0F"/>'
                 f'<ellipse cx="{x+s*2-3}" cy="{base-8-lf}" rx="5" ry="2" fill="#3A3A44"/>')
    return "".join(l)

def bot(x, y, t, mood="calm"):
    """Little amber AI robot sidekick."""
    eye = (f'<rect x="{x-7}" y="{y-2}" width="4" height="5" rx="2" fill="{GLOW}"/><rect x="{x+3}" y="{y-2}" width="4" height="5" rx="2" fill="{GLOW}"/>'
           if mood != "happy" else
           f'<path d="M{x-8},{y+2} q3,-5 6,0 M{x+2},{y+2} q3,-5 6,0" stroke="{GLOW}" stroke-width="2" fill="none" stroke-linecap="round"/>')
    blink = (t % 1) > .82
    if blink and mood != "happy":
        eye = f'<rect x="{x-7}" y="{y}" width="4" height="1.6" rx=".8" fill="{GLOW}"/><rect x="{x+3}" y="{y}" width="4" height="1.6" rx=".8" fill="{GLOW}"/>'
    return (f'<ellipse cx="{x}" cy="{y+30}" rx="9" ry="2.5" fill="#000" opacity=".12"/>'
            f'<line x1="{x}" y1="{y-16}" x2="{x}" y2="{y-23}" stroke="{BOT_SH}" stroke-width="2.4"/>'
            f'<circle cx="{x}" cy="{y-24}" r="3.2" fill="{GLOW if (t*2)%1<.5 else "#FFE08A"}"/>'
            f'<rect x="{x-16}" y="{y-16}" width="32" height="28" rx="10" fill="{BOT}"/>'
            f'<rect x="{x-12}" y="{y-10}" width="24" height="16" rx="6" fill="#1D1A24"/>'
            + eye +
            f'<rect x="{x-20}" y="{y-5}" width="5" height="9" rx="2.5" fill="{BOT_SH}"/><rect x="{x+15}" y="{y-5}" width="5" height="9" rx="2.5" fill="{BOT_SH}"/>'
            f'<path d="M{x-8},{y+12} q8,8 16,0" fill="{BOT_SH}"/>')

def sparkle(x, y, s, col="#FFD24A", rot=0):
    if s <= 0:
        return ""
    return (f'<g transform="translate({x},{y}) rotate({rot}) scale({s})">'
            f'<path d="M0,-10 Q1.5,-1.5 10,0 Q1.5,1.5 0,10 Q-1.5,1.5 -10,0 Q-1.5,-1.5 0,-10Z" fill="{col}"/></g>')

def frame(anim, i):
    t = i / N
    cx = 118          # character centre x (room on the right for the bot)
    base = 242        # floor line
    g = []
    eye, mth, look, brow, glow = "open", "smile", (0, 0), 0, False
    la, ra = 12, -12  # arm angles
    raised = None
    lift = (0, 0)
    dy = 0
    squash = 0
    shadow_s = 1
    extras_back, extras_front = [], []
    btilt, sweat, shake, tilt, hshift = 0, None, 0, 0, (0, 0)
    bx_, by_ = cx + 92, 96

    if anim == "idle":
        dy = 2.5 * ease(t)
        la, ra = 10 + 3 * ease(t), -10 - 3 * ease(t)
        eye = "blink" if i == 5 else "open"
        by_ = 92 + 5 * math.sin(2 * math.pi * t)
    elif anim == "wave":
        dy = 1.5 * ease(t * 2)
        raised = ("r", -150 + 28 * math.sin(2 * math.pi * t * 2))
        eye = "happy" if i in (2, 3, 6, 7) else "open"
        mth = "open"
        by_ = 92 + 4 * math.sin(2 * math.pi * t)
        extras_front.append(sparkle(cx + 64, 74, .6 + .4 * ease(t * 2), "#FFD24A", 30 * t))
    elif anim == "typing":
        dy = 1.2 * abs(math.sin(2 * math.pi * t * 2))
        la, ra = -38, 38
        look, mth, glow, brow = (0, 2.5), "focus", False, 1
        eye = "blink" if i == 6 else "open"
        by_ = 108 + 2 * math.sin(2 * math.pi * t)
        bx_ = cx + 98
    elif anim == "idea":
        k = min(1, i / 3)
        dy = -2 * k
        look, brow = (2.5, -3.5), 3 * k
        mth = "o" if i < 4 else "open"
        eye = "open" if i < 6 else "happy"
        raised = ("l", -150 + 20 * (1 - k))  # hand to chin -> finger up
        by_ = 88 + 3 * math.sin(2 * math.pi * t)
    elif anim == "celebrate":
        ph = t
        jump = max(0, math.sin(2 * math.pi * ph))  # up for first half
        dy = -26 * jump
        squash = 6 if i in (0, 7) else (0 if jump > .1 else 3)
        shadow_s = 1 - .45 * jump
        la, ra = 150 + 10 * math.sin(2 * math.pi * t * 2), -150 - 10 * math.sin(2 * math.pi * t * 2)
        lift = (6 * jump, 6 * jump)
        eye, mth = "happy", "open"
        by_ = 84 - 10 * jump
        for k2, (sx, sy, col) in enumerate([(40, 70, "#FFD24A"), (196, 60, GLOW), (60, 150, RED), (190, 160, "#FFD24A"), (128, 22, GLOW)]):
            s = ease((t + k2 * .2) % 1)
            extras_back.append(sparkle(sx, sy - 6 * s, .4 + .7 * s, col, 90 * t + k2 * 20))

    elif anim == "point":
        k = min(1, i / 2)
        raised = ("l", 60 + 75 * k + (5 * math.sin(2 * math.pi * t * 2) if i >= 2 else 0))
        look, mth, brow = (-3.5, -2.5), "open", 2
        eye = "happy" if i in (5, 6) else "open"
        dy = 1.2 * ease(t)
        by_ = 90 + 4 * math.sin(2 * math.pi * t)
    elif anim == "thumbs":
        k = min(1, i / 2)
        raised = ("r", -40 - 120 * k + (6 * math.sin(2 * math.pi * t * 2) if i >= 2 else 0))
        eye = "happy" if i >= 3 else "open"
        mth = "open"
        dy = -2 * ease(t)
        by_ = 90 + 4 * math.sin(2 * math.pi * t)
        extras_front.append(sparkle(cx + 70, 58, .5 + .5 * ease(t * 2), "#FFD24A", 40 * t))
    elif anim == "worried":
        jit = 1.6 * math.sin(2 * math.pi * t * 4)
        dy = 0
        look, mth, btilt = (-1, 1), "wobble", 14
        eye = "blink" if i == 5 else "open"
        la, ra = 24, -24
        by_ = 98 + 2 * math.sin(2 * math.pi * t)
        shake = jit
    elif anim == "resume":
        dy = -3 * ease(t)
        mth = "open" if i in (2, 3, 4) else "smile"
        eye = "happy" if i in (3, 4) else "open"
        by_ = 90 + 4 * math.sin(2 * math.pi * t)
    elif anim == "confused":
        tilt = 8 * math.sin(2 * math.pi * t)
        look = (-3 + 6 * ease(t), -3)
        mth, btilt = "side", 6
        by_ = 92 + 4 * math.sin(2 * math.pi * t)
    elif anim == "look":
        d = LOOKS[i] if i < len(LOOKS) else (0, 0)
        look = (4 * d[0], 3.4 * d[1])
        hshift = (3.5 * d[0], 2 * d[1])
        tilt = 4 * d[0]
        by_ = 92

    # shadow
    g.append(f'<ellipse cx="{cx}" cy="{base-3}" rx="{44*shadow_s:.1f}" ry="{7*shadow_s:.1f}" fill="#000" opacity="{.16*shadow_s+.04:.2f}"/>')
    g.extend(extras_back)
    neck_y = 150 + dy
    g.append(legs(cx, base + dy * (1 if anim == "celebrate" else 0), lift))
    # arms behind body when raised high (celebrate) so the suit overlaps the shoulder joint
    if anim == "celebrate":
        g.append(arm(cx - 36, neck_y + 10, la))
        g.append(arm(cx + 36, neck_y + 10, ra))
    g.append(body(cx, neck_y, squash))
    if anim not in ("celebrate", "typing", "resume"):
        if not (raised and raised[0] == "l"):
            g.append(arm(cx - 38, neck_y + 10, la))
        if not (raised and raised[0] == "r"):
            g.append(arm(cx + 38, neck_y + 10, ra))
    hx, hy = cx + shake + hshift[0], 92 + dy + hshift[1]
    if anim == "worried":
        sweat = 10 * t
    hd = head(hx, hy, eye, mth, look, brow, tuft=(0 if anim == "look" else 8 * math.sin(2 * math.pi * t * (2 if anim != "idle" else 1))), glow=glow, btilt=btilt, sweat=sweat)
    g.append(f'<g transform="rotate({tilt:.2f} {hx} {hy+50})">{hd}</g>' if tilt else hd)
    if raised:
        side, ang = raised
        sx = cx + (38 if side == "r" else -38)
        g.append(arm(sx, neck_y + 10, ang, thumb=(anim == "thumbs"), finger=(anim in ("point", "idea") and (anim != "idea" or i >= 4))))
    if anim == "resume":
        lift_p = 3 * ease(t)
        py = 166 - lift_p
        g.append(f'<g transform="rotate(-4 {cx} {py+34})">'
                 f'<rect x="{cx-30}" y="{py}" width="60" height="74" rx="3" fill="#FFFFFF" stroke="#C9CED8" stroke-width="1.5"/>'
                 f'<rect x="{cx-30}" y="{py}" width="60" height="15" rx="3" fill="{BOT}"/>'
                 f'<text x="{cx}" y="{py+11.5}" text-anchor="middle" font-family="Arial" font-weight="900" font-size="10" fill="{INK}">CV</text>'
                 + "".join(f'<rect x="{cx-22}" y="{py+22+k*9}" width="{44 if k%2==0 else 32}" height="3.4" rx="1.7" fill="#C9CED8"/>' for k in range(5))
                 + f'<circle cx="{cx+16}" cy="{py+60}" r="6" fill="none" stroke="{RED}" stroke-width="1.8"/></g>')
        for s2 in (-1, 1):
            g.append(f'<circle cx="{cx+s2*31}" cy="{py+30}" r="9.5" fill="{SKIN}"/><circle cx="{cx+s2*31-3}" cy="{py+28}" r="3" fill="{SKIN_HI}" opacity=".6"/>')
    if anim == "confused":
        for k2, (qx, qy) in enumerate([(cx + 62, 40), (cx + 80, 18), (cx - 66, 30)]):
            ph = (t + k2 * .33) % 1
            g.append(f'<text x="{qx}" y="{qy - 6*ph:.1f}" font-family="Arial" font-weight="900" font-size="{18+4*k2%8}" fill="{BOT if k2!=1 else GLOW}" opacity="{math.sin(math.pi*ph):.2f}">?</text>')
    if anim == "typing":
        # laptop seen from behind (lid faces the viewer), hands on the keys
        tap = [(0, 3), (3, 0), (0, 3), (3, 0), (0, 3), (3, 0), (1, 1), (0, 0)][i]
        g.append(f'<g>'
                 f'<rect x="{cx-50}" y="{176}" width="100" height="62" rx="7" fill="#C9CED8"/>'
                 f'<rect x="{cx-50}" y="{176}" width="100" height="6" rx="3" fill="#E2E6EE"/>'
                 f'<rect x="{cx-58}" y="{236}" width="116" height="7" rx="3.5" fill="#9AA2B1"/>'
                 f'<circle cx="{cx}" cy="{207}" r="10" fill="{BOT}"/>'
                 f'<text x="{cx}" y="{211.5}" text-anchor="middle" font-family="Arial" font-weight="900" font-size="11" fill="{INK}">AM</text></g>')
        for s, tp in ((-1, tap[0]), (1, tap[1])):
            g.append(f'<circle cx="{cx+s*30}" cy="{176-tp}" r="9.5" fill="{SKIN}"/><circle cx="{cx+s*30-3}" cy="{174-tp}" r="3" fill="{SKIN_HI}" opacity=".6"/>')
        # code glyphs floating up from the screen
        glyphs = [("&lt;/&gt;", -78), ("{ }", 76), ("AI", -66), ("01", 66)]
        for k2, (gl, ox) in enumerate(glyphs):
            ph = (t + k2 / len(glyphs)) % 1
            x = cx + ox + 4 * math.sin(2 * math.pi * (ph + k2 * .3))
            y = 196 - 64 * ph
            op = math.sin(math.pi * ph)
            g.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Consolas,Menlo,monospace" font-weight="700" font-size="13" fill="{GLOW if k2%2 else BOT}" opacity="{op:.2f}">{gl}</text>')
    if anim == "idea":
        # light bulb pops in over the head, then glows
        k = max(0, min(1, (i - 2) / 2))
        if k > 0:
            sc = .4 + .6 * k + (.08 * math.sin(math.pi * (i - 4)) if i >= 4 else 0)
            gx, gy = cx + 46, 26
            rays = "".join(f'<line x1="{gx+19*math.cos(a)}" y1="{gy+19*math.sin(a)}" x2="{gx+27*math.cos(a)}" y2="{gy+27*math.sin(a)}" stroke="#FFD24A" stroke-width="3" stroke-linecap="round"/>'
                           for a in [math.radians(d) for d in (-150, -110, -70, -30, 10, 190)]) if i >= 4 else ""
            g.append(f'<g transform="translate({gx},{gy}) scale({sc:.2f}) translate({-gx},{-gy})">{rays}'
                     f'<circle cx="{gx}" cy="{gy}" r="13" fill="#FFE27A"/><circle cx="{gx-4}" cy="{gy-4}" r="4" fill="#FFF6CC"/>'
                     f'<rect x="{gx-6}" y="{gy+11}" width="12" height="8" rx="2" fill="#8E95A3"/></g>')
    g.extend(extras_front)
    mood = "happy" if anim in ("wave", "celebrate", "thumbs", "resume") or (anim == "idea" and i >= 5) else "calm"
    g.append(bot(bx_, by_ + (dy if anim == "celebrate" else 0) * .5, t, mood))
    S = 0.82  # scale the whole scene about the floor so hair and jumps stay inside the cell
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="CELL" height="CELL">'
            f'<g transform="translate({128*(1-S)+6:.2f},{250*(1-S):.2f}) scale({S})">{"".join(g)}</g></svg>')

async def render(scale):
    cell = CELL * scale
    html = ['<html><body style="margin:0;background:transparent">'
            f'<div id="sheet" style="display:grid;grid-template-columns:repeat({N},{cell}px);width:{cell*N}px">']
    for a in ANIMS:
        for i in range(N):
            html.append(frame(a, i).replace('CELL', str(cell)))
    html.append('</div></body></html>')
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': cell * N, 'height': cell * len(ANIMS)})
        await pg.set_content("".join(html))
        png = await pg.locator('#sheet').screenshot(omit_background=True)
        await b.close()
    return Image.open(io.BytesIO(png)).convert("RGBA")

async def render_site(cell=384):
    cols = 9
    html = ['<html><body style="margin:0;background:transparent">'
            f'<div id="sheet" style="display:grid;grid-template-columns:repeat({cols},{cell}px);width:{cell*cols}px">']
    for a in SITE_ROWS:
        n = 9 if a == "look" else 8
        for i in range(cols):
            html.append(frame(a, i).replace('CELL', str(cell)) if i < n else f'<div style="width:{cell}px;height:{cell}px"></div>')
    html.append('</div></body></html>')
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': cell * cols, 'height': cell * len(SITE_ROWS)})
        await pg.set_content("".join(html))
        png = await pg.locator('#sheet').screenshot(omit_background=True)
        await b.close()
    return Image.open(io.BytesIO(png)).convert("RGBA")

def main_site():
    im = asyncio.run(render_site())
    dest = ROOT / "assets" / "img" / "alvin-sprite.webp"
    im.save(dest, "WEBP", quality=82, method=6)
    print("site sheet", im.size, dest.stat().st_size // 1024, "KB ->", dest)

def main():
    sheet = asyncio.run(render(1))
    sheet.save(OUT / "alvin-sprite.png", optimize=True)
    big = asyncio.run(render(2))
    big.save(OUT / "alvin-sprite@2x.png", optimize=True)
    # GIF previews on a soft background (GIF has no real alpha)
    for r, a in enumerate(ANIMS):
        frames = []
        for i in range(N):
            f = big.crop((i * 512, r * 512, (i + 1) * 512, (r + 1) * 512)).resize((320, 320), Image.LANCZOS)
            bg = Image.new("RGBA", f.size, (236, 239, 243, 255))
            bg.alpha_composite(f)
            frames.append(bg.convert("P", palette=Image.ADAPTIVE, colors=128))
        dur = {"idle": 140, "wave": 100, "typing": 90, "idea": 160, "celebrate": 95}[a]
        frames[0].save(OUT / f"alvin-{a}.gif", save_all=True, append_images=frames[1:], duration=dur, loop=0, disposal=2)
    print("done", sheet.size, big.size)

if __name__ == "__main__":
    import sys
    main_site() if "--site" in sys.argv else main()
