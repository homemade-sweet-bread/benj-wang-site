#!/usr/bin/env python3
"""生成《小机器人吃果子》的 128 关（8 章 × 16 关）并做合法性校验。

用法：python3 tools/generate-levels.py
输出：levels.json（与 index.html 内嵌的 LEVELS 数据同源）
注意：随机种子固定，改动算法会改变全部关卡。
"""

import json, random

N = 5
DIRS = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
OPP = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}
WORD = {'U': '向上', 'D': '向下', 'L': '向左', 'R': '向右'}

CHAPTERS = [
    {"name": "出发",     "length": (2, 5),  "turns": (0, 1), "walls": 0, "fruits": 1, "fruit": "apple"},
    {"name": "拐个弯",   "length": (4, 7),  "turns": (1, 2), "walls": 1, "fruits": 1, "fruit": "apple"},
    {"name": "石头路",   "length": (5, 9),  "turns": (1, 3), "walls": 4, "fruits": 1, "fruit": "apple"},
    {"name": "双份果子", "length": (6, 10), "turns": (2, 3), "walls": 1, "fruits": 2, "fruit": "apple"},
    {"name": "小小迷宫", "length": (7, 12), "turns": (2, 4), "walls": 5, "fruits": 2, "fruit": "apple"},
    {"name": "星星雨",   "length": (8, 13), "turns": (2, 4), "walls": 3, "fruits": 3, "fruit": "star"},
    {"name": "绕远路",   "length": (10, 16),"turns": (3, 5), "walls": 4, "fruits": 2, "fruit": "apple"},
    {"name": "终章挑战", "length": (12, 20),"turns": (4, 6), "walls": 6, "fruits": 3, "fruit": "star"},
]

BORDERS = ([(0, c) for c in range(N)] + [(4, c) for c in range(N)] +
           [(r, 0) for r in range(1, 4)] + [(r, 4) for r in range(1, 4)])

def inb(r, c):
    return 0 <= r < N and 0 <= c < N

def gen_path(rng, target, min_turns, max_turns):
    for _ in range(600):
        start = rng.choice(BORDERS)
        path = [start]
        vis = {start}
        d = None
        turns = 0
        while len(path) - 1 < target:
            cur = path[-1]
            cands = []
            for nd, (dr, dc) in DIRS.items():
                if d and nd == OPP[d]:
                    continue
                nr, nc = cur[0] + dr, cur[1] + dc
                if inb(nr, nc) and (nr, nc) not in vis:
                    cands.append((nd, (nr, nc)))
            if not cands:
                break
            straight = [x for x in cands if x[0] == d]
            # 偏好直行，路径更像"路线"而不是随机乱走
            if straight and rng.random() < 0.66:
                nd, nxt = straight[0]
            else:
                nd, nxt = rng.choice(cands)
                if d and nd != d:
                    turns += 1
            path.append(nxt)
            vis.add(nxt)
            d = nd
        if len(path) - 1 == target and min_turns <= turns <= max_turns:
            return path, turns
    return None, None

def segments(path):
    segs = []
    for i in range(1, len(path)):
        dr = path[i][0] - path[i - 1][0]
        dc = path[i][1] - path[i - 1][1]
        d = 'U' if dr == -1 else 'D' if dr == 1 else 'L' if dc == -1 else 'R'
        if segs and segs[-1][0] == d:
            segs[-1][1] += 1
        else:
            segs.append([d, 1])
    return segs

def fruit_indices(n, k):
    if k == 1:
        return [n]
    pts = [max(2, min(n, round(n * (i + 1) / k))) for i in range(k)]
    out = []
    for p in pts:
        if p not in out:
            out.append(p)
    while len(out) < k and out[-1] > 2:
        out.append(out[-1] - 1)
    return out

def place_walls(rng, path, fruit_cells, k):
    occupied = set(path) | set(fruit_cells)
    cands = [(r, c) for r in range(N) for c in range(N) if (r, c) not in occupied]
    adj = [cell for cell in cands
           if any((cell[0] + dr, cell[1] + dc) in set(path) for dr, dc in DIRS.values())]
    walls = []
    while len(walls) < k and cands:
        pool = adj if (adj and rng.random() < 0.75) else cands
        cell = rng.choice(pool)
        walls.append(cell)
        if cell in adj: adj.remove(cell)
        cands.remove(cell)
    return walls

def make_tip(path, n):
    segs = segments(path)[:2]
    parts = ["%s %d 步" % (WORD[d], c) for d, c in segs]
    if n <= 4:
        if len(parts) == 1:
            return parts[0] + "，果子就在那里，出发吧！"
        return parts[0] + "，再" + parts[1] + "，果子就在那里，出发吧！"
    return "这一关要走 %d 步：先%s。" % (n, "，再".join(parts))

def build(seed):
    rng = random.Random(seed)
    levels = []
    for ci, ch in enumerate(CHAPTERS):
        lo, hi = ch["length"]
        for i in range(16):
            t = i / 15.0
            target = int(round(lo + (hi - lo) * t)) + rng.choice([-1, 0, 0, 1])
            target = max(lo if lo > 2 else 2, min(hi, target))
            min_turns = ch["turns"][0] + (1 if t >= 0.55 else 0)
            max_turns = ch["turns"][1] + 2
            walls_n = ch["walls"] + (1 if (ch["walls"] and t >= 0.7) else 0)
            path = turns = None
            for _ in range(60):
                path, turns = gen_path(rng, target, min_turns, max_turns)
                if path:
                    break
                target = max(2, target - 1)
            if not path:
                raise RuntimeError("fail ch%d lvl%d" % (ci, i))
            n = len(path) - 1
            fi = fruit_indices(n, ch["fruits"])
            fruits = [list(path[j]) for j in fi]
            walls = place_walls(rng, path, [tuple(f) for f in fruits], walls_n)
            sol = []
            for a, b in zip(path, path[1:]):
                dr, dc = b[0] - a[0], b[1] - a[1]
                sol.append('U' if dr == -1 else 'D' if dr == 1 else 'L' if dc == -1 else 'R')
            levels.append({
                "start": list(path[0]),
                "fruits": fruits,
                "walls": [list(w) for w in walls],
                "solution": sol,
                "tip": make_tip(path, n),
                "chapter": ci,
                "fruit": ch["fruit"],
            })
    return levels

levels = build(20261023)

# 校验
for idx, lv in enumerate(levels):
    r, c = lv["start"]
    walls = set(map(tuple, lv["walls"]))
    fruits = [tuple(f) for f in lv["fruits"]]
    assert (r, c) not in walls, idx
    assert (r, c) not in fruits, idx
    for s in lv["solution"]:
        dr, dc = DIRS[s]
        r, c = r + dr, c + dc
        assert inb(r, c), (idx, "oob")
        assert (r, c) not in walls, (idx, "wall")
    assert (r, c) == fruits[-1], (idx, "end")
    for f in fruits:
        assert inb(*f), (idx, "fruit oob")
    assert len(lv["solution"]) <= 24, idx

print("levels:", len(levels))
from collections import Counter
print("steps:", Counter(len(l["solution"]) for l in levels))
print("by chapter:", [(c, sum(1 for l in levels if l["chapter"] == c)) for c in range(8)])
print("max steps:", max(len(l["solution"]) for l in levels))
json.dump(levels, open("levels.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for l in levels[:3] + levels[64:66] + levels[-2:]:
    print(l)
