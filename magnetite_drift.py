#!/usr/bin/env python3
"""Magnetite Drift — neon polarity-snatch arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "MAGNETITE DRIFT"
HANDLE = "x.com/ElbowOS"
VOID = (8, 7, 12)
IRON = (22, 18, 26)
RUST = (255, 110, 52)
COPPER = (255, 176, 86)
NORTH = (48, 230, 255)
SOUTH = (255, 58, 148)
STEEL = (196, 206, 224)
GOLD = (255, 214, 96)
SLAG = (255, 70, 64)
MINT = (90, 255, 186)
ICE = (236, 240, 255)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=6):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Shard:
    __slots__ = ("x", "y", "vx", "vy", "pol", "kind", "r", "spin")

    def __init__(self, x, y, vx, vy, pol, kind, r):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.pol, self.kind, self.r, self.spin = pol, kind, r, random.random() * 6.28


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 62)
        self.font_md = pygame.font.Font(None, 42)
        self.font_sm = pygame.font.Font(None, 30)
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.lives = 3
        self.pulse = 0.0
        self.over = False
        self.cool = 0.0
        self.px = W / 2
        self.py = H - 340
        self.pvx = 0.0
        self.pol = 1  # +1 North, -1 South
        self.aim = 0.0
        self.flip_cd = 0.0
        self.sparks: list[Spark] = []
        self.shards: list[Shard] = []
        self.stars = [(random.randrange(W), random.randrange(H), random.uniform(0.4, 2.4)) for _ in range(110)]
        self.spawn_t = 0.0
        for _ in range(7):
            self._spawn(True)

    def _spawn(self, start: bool = False) -> None:
        kind = "slag" if random.random() < 0.22 else "ore"
        pol = random.choice((-1, 1))
        x = random.randint(90, W - 90)
        y = random.randint(-80, 420) if start else random.randint(-140, -40)
        vx = random.uniform(-70, 70)
        vy = random.uniform(90, 210) if kind == "ore" else random.uniform(130, 260)
        r = random.randint(18, 28) if kind == "ore" else random.randint(16, 24)
        self.shards.append(Shard(x, y, vx, vy, pol, kind, r))

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.random() * 6.2832
            s = random.uniform(80, 420)
            self.sparks.append(Spark(x, y, s * math.cos(a), s * math.sin(a),
                                     random.uniform(0.2, 0.5), col, random.randint(3, 9)))

    def autoplay(self) -> None:
        if self.over:
            if self.cool <= 0:
                self.reset()
            return
        ores = [s for s in self.shards if s.kind == "ore" and s.y < self.py + 80]
        slags = [s for s in self.shards if s.kind == "slag"]
        target = None
        if ores:
            target = min(ores, key=lambda s: abs(s.x - self.px) + max(0, self.py - s.y) * 0.35)
            if target.pol == self.pol and self.flip_cd <= 0:
                self.pol *= -1
                self.flip_cd = 0.28
                self.burst(self.px, self.py, NORTH if self.pol > 0 else SOUTH, 10)
        threat = None
        for s in slags:
            if abs(s.x - self.px) < 90 and 0 < self.py - s.y < 220:
                threat = s
                break
        if threat:
            self.aim = -1.0 if threat.x > self.px else 1.0
        elif target:
            self.aim = max(-1.0, min(1.0, (target.x - self.px) / 140))
        else:
            self.aim = math.sin(self.pulse * 1.4) * 0.4

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.cool = max(0.0, self.cool - dt)
        self.flip_cd = max(0.0, self.flip_cd - dt)
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            self.aim = float((keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]))
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            alive.append(sp)
        self.sparks = alive
        if self.over:
            return
        self.pvx += self.aim * 2400 * dt
        self.pvx *= 0.86
        self.px = max(90, min(W - 90, self.px + self.pvx * dt))
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self._spawn()
            self.spawn_t = max(0.28, 0.72 - self.score * 0.0004)
        kept = []
        for s in self.shards:
            s.spin += dt * 3.2
            dx, dy = self.px - s.x, self.py - s.y
            dist = math.hypot(dx, dy) or 1
            if s.kind == "ore":
                sign = -1 if s.pol == self.pol else 1  # same repels, opposite attracts
                pull = 520000 * sign / (dist * dist + 18000)
                s.vx += (dx / dist) * pull * dt
                s.vy += (dy / dist) * pull * dt * 0.55
            s.vx *= 0.995
            s.x += s.vx * dt
            s.y += s.vy * dt
            if s.x < 40 or s.x > W - 40:
                s.vx *= -0.7
                s.x = max(40, min(W - 40, s.x))
            if dist < 52 + s.r:
                if s.kind == "slag":
                    self.lives -= 1
                    self.combo = 0
                    self.burst(s.x, s.y, SLAG, 22)
                    if self.lives <= 0:
                        self.over = True
                        self.cool = 1.6
                    continue
                if s.pol != self.pol:
                    self.combo += 1
                    self.score += 20 + self.combo * 5
                    self.burst(s.x, s.y, NORTH if s.pol > 0 else SOUTH, 16)
                    continue
                # same pole bump
                nx, ny = dx / dist, dy / dist
                s.vx -= nx * 280
                s.vy -= ny * 180
                self.score += 2
                self.burst(s.x, s.y, COPPER, 6)
            if s.y < H + 60:
                kept.append(s)
        self.shards = kept

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_r:
                self.reset()
            elif ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP) and self.flip_cd <= 0:
                self.pol *= -1
                self.flip_cd = 0.18
                self.burst(self.px, self.py, NORTH if self.pol > 0 else SOUTH, 12)

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, sc in self.stars:
            yy = int((sy + self.pulse * 28 * sc) % H)
            pygame.draw.circle(s, (28 + int(10 * sc), 24, 36), (sx, yy), 1 if sc < 1.2 else 2)
        # rust canyon walls
        pygame.draw.rect(s, IRON, (0, 250, 56, H))
        pygame.draw.rect(s, IRON, (W - 56, 250, 56, H))
        pygame.draw.rect(s, RUST, (0, 250, 56, H), 3)
        pygame.draw.rect(s, RUST, (W - 56, 250, 56, H), 3)
        pol_col = NORTH if self.pol > 0 else SOUTH
        # field lines
        for i in range(10):
            ang = self.pulse * 1.1 + i * 0.628
            rad = 70 + 18 * math.sin(self.pulse * 3 + i)
            x2 = int(self.px + math.cos(ang) * (210 + rad))
            y2 = int(self.py + math.sin(ang) * (150 + rad * 0.6))
            pygame.draw.aaline(s, pol_col, (int(self.px), int(self.py)), (x2, y2))
        for sh in self.shards:
            col = SLAG if sh.kind == "slag" else (NORTH if sh.pol > 0 else SOUTH)
            pygame.draw.circle(s, col, (int(sh.x), int(sh.y)), sh.r + 5)
            pygame.draw.circle(s, STEEL if sh.kind == "ore" else (40, 10, 12), (int(sh.x), int(sh.y)), sh.r)
            mark = "N" if sh.pol > 0 else "S"
            if sh.kind == "ore":
                lab = self.font_sm.render(mark, True, col)
                s.blit(lab, lab.get_rect(center=(int(sh.x), int(sh.y))))
            else:
                pygame.draw.circle(s, SLAG, (int(sh.x), int(sh.y)), max(4, sh.r - 8), 2)
        mx, my = int(self.px), int(self.py)
        pygame.draw.circle(s, pol_col, (mx, my), 54)
        pygame.draw.circle(s, (18, 16, 22), (mx, my), 42)
        pygame.draw.circle(s, pol_col, (mx, my), 28)
        pygame.draw.circle(s, ICE, (mx - 10, my - 12), 8)
        pole = self.font_md.render("N" if self.pol > 0 else "S", True, ICE)
        s.blit(pole, pole.get_rect(center=(mx, my + 2)))
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, ICE)
        s.blit(title, title.get_rect(center=(W // 2, 68)))
        handle = self.font_sm.render(HANDLE, True, NORTH)
        s.blit(handle, handle.get_rect(center=(W // 2, 116)))
        meta = self.font_md.render(f"SCORE  {self.score}    COMBO  {self.combo}    HP  {self.lives}", True, GOLD)
        s.blit(meta, meta.get_rect(center=(W // 2, 174)))
        pole_txt = self.font_sm.render("POLE  NORTH" if self.pol > 0 else "POLE  SOUTH", True, pol_col)
        s.blit(pole_txt, pole_txt.get_rect(center=(W // 2, 220)))
        hint = self.font_sm.render("A/D move   SPACE flip polarity   R reset", True, COPPER)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 42)))
        if self.over:
            over = self.font_md.render("CORE DEMAGNETISED", True, SLAG)
            s.blit(over, over.get_rect(center=(W // 2, 268)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/MAGNETITE_DRIFT_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
