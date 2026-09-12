#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每款便利店调酒生成一张可下载的分享卡片（1080 宽 PNG）。

流程：
  node scripts/extract-drinks.mjs        # 从 index.html 抽取配方 → scripts/drinks.json
  python3 scripts/build-cards.py         # 渲染全部卡片 → assets/cards/card-NN.png
  python3 scripts/build-cards.py 自由古巴 简易莫吉托   # 只渲染指定几杯（调样式用）

依赖 Pillow；字体用 macOS 自带 Hiragino Sans GB（W3 正文 / W6 标题）。
"""

import json
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITE_PATH = os.path.join(ROOT, 'assets', 'cocktails-sprite.webp')
DATA_PATH = os.path.join(ROOT, 'scripts', 'drinks.json')
OUT_DIR = os.path.join(ROOT, 'assets', 'cards')

FONT_PATH = '/System/Library/Fonts/Hiragino Sans GB.ttc'
FONT_W3, FONT_W6 = 0, 2
SITE_URL = 'www.200jin.cn/cocotail'
BRAND = '便利店调酒 · 微醺指南'

# ---------- 尺寸 ----------
W = 1080
M = 28           # 画布边 → 内层卡面
PAD = 56         # 内层卡面 → 内容
CX = M + PAD     # 内容左边界 = 84
CW = W - 2 * CX  # 内容宽度 = 912
HERO_H = 600
HERO_R = 40

# ---------- 颜色 ----------
BG_TOP = (9, 10, 18)
BG_BOTTOM = (5, 6, 11)
TX = (243, 244, 249)
TX2 = (168, 174, 192)
TX3 = (124, 131, 150)
TX4 = (96, 102, 122)
HAIR = (255, 255, 255, 16)
HAIR2 = (255, 255, 255, 34)

_fonts = {}


def font(size, weight='w3'):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_PATH, size, index=FONT_W6 if weight == 'w6' else FONT_W3)
    return _fonts[key]


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(c, a):
    return (c[0], c[1], c[2], int(a))


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


# ---------- 文本工具 ----------
def tlen(d, s, f):
    return d.textlength(s, font=f)


NO_START = '，。、！？：；）】》」』%、·.,!?:;)]}'
NO_END = '（【《「『([{'


def wrap(d, text, f, maxw):
    """按宽度折行，并做简单的中文避头尾处理。"""
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur)
            cur = ''
            continue
        if cur and (tlen(d, cur + ch, f) > maxw):
            if ch in NO_START:
                cur += ch            # 标点悬挂在行尾，不另起一行
                continue
            if cur[-1] in NO_END:
                lines.append(cur[:-1])  # 开引号/括号跟着下一行走
                cur = cur[-1]
            else:
                lines.append(cur)
                cur = ''
        cur += ch
    lines.append(cur)
    return lines


def spaced(d, xy, text, f, fill, ls=0.0):
    """带字距的文本（PIL 无 tracking，逐字推进）。返回结束 x。"""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += tlen(d, ch, f) + ls
    return x - ls if text else x


def spaced_len(d, text, f, ls=0.0):
    return sum(tlen(d, c, f) for c in text) + ls * max(0, len(text) - 1)


# ---------- 结构积木 ----------
def cup_image(sprite, idx, size):
    """从雪碧图裁一格，做径向羽化，去掉方形底。"""
    cell = sprite.width // 6
    sx, sy = (idx % 6) * cell, (idx // 6) * cell
    im = sprite.crop((sx, sy, sx + cell, sy + cell)).convert('RGB')
    im = im.resize((size, size), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), radial_mask(size))
    return out


def radial_mask(size, inner=0.86, outer=1.04):
    n = 160
    m = Image.new('L', (n, n), 0)
    px = m.load()
    for j in range(n):
        for i in range(n):
            u = (i + 0.5 - n / 2) / (n / 2)
            v = (j + 0.5 - n / 2) / (n / 2)
            r = math.hypot(u, v)
            if r <= inner:
                a = 255
            elif r >= outer:
                a = 0
            else:
                t = (r - inner) / (outer - inner)
                a = int(255 * (1 - t) ** 1.3)
            px[i, j] = a
    return m.resize((size, size), Image.BICUBIC)


def pill(d, box, fill, outline=None, r=None):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=r if r is not None else (y1 - y0) / 2, fill=fill, outline=outline, width=1)


def gradient_bg(w, h):
    img = Image.new('RGB', (1, h))
    px = img.load()
    for y in range(h):
        px[0, y] = mix(BG_TOP, BG_BOTTOM, y / max(1, h - 1))
    return img.resize((w, h), Image.BILINEAR)


def orbs(w, h, color):
    """卡面四周的彩色光晕。"""
    layer = Image.new('RGBA', (w // 4, h // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for cx, cy, rx, ry, a in ((0.80, 0.09, 0.40, 0.18, 74), (0.09, 0.66, 0.36, 0.18, 44), (0.74, 0.95, 0.38, 0.15, 32)):
        x, y = cx * w / 4, cy * h / 4
        d.ellipse([x - rx * w / 4, y - ry * h / 4, x + rx * w / 4, y + ry * h / 4], fill=rgba(color, a))
    layer = layer.filter(ImageFilter.GaussianBlur(46)).resize((w, h), Image.LANCZOS)
    return layer


# ---------- 主渲染 ----------
def render(drink, sprite, out_path):
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    cat = hexrgb(drink['color'])
    lv = drink['level']
    lv_text = {0: '无酒精', 1: '酒感很轻', 2: '中等酒劲', 3: '后劲较足'}[lv]
    tag = '热门' if drink['hot'] else ('无酒精' if lv == 0 else ('新手友好' if lv == 1 else ('上头预警' if lv == 3 else '')))

    H_LIMIT = 4000
    shapes = Image.new('RGBA', (W, H_LIMIT), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shapes)
    texts = []   # (text, xy, font, fill, ls)
    hero_glow = None

    def para(y, text, f, fill, maxw, line_h, x=CX, ls=0.0):
        """折行并登记文本（文字统一在形状合成后再画），返回结束 y。"""
        for line in wrap(d, text, f, maxw):
            texts.append((line, (x, y), f, fill, ls))
            y += line_h
        return y

    y = M + 48

    # ── 眉标 + 分类胶囊 ──
    eb_f = font(23)
    sd.ellipse([CX, y + 16, CX + 11, y + 27], fill=rgba(cat, 235))
    spaced(sd, (CX + 22, y + 6), '便利店调酒 · 微醺指南', eb_f, rgba(TX2, 235), 1.2)
    cat_f = font(23)
    cw_ = spaced_len(d, drink['catName'], cat_f, 1.2)
    pill(sd, (W - CX - (cw_ + 40), y, W - CX, y + 42), rgba(cat, 40), rgba(cat, 120))
    spaced(sd, (W - CX - (cw_ + 40) + 20, y + 9), drink['catName'], cat_f, mix(cat, (255, 255, 255), 0.35), 1.2)
    y += 46 + 36

    # ── 主视觉 ──
    hero_y = y
    sd.rounded_rectangle([CX, hero_y, CX + CW, hero_y + HERO_H], radius=HERO_R,
                         fill=(255, 255, 255, 13), outline=(255, 255, 255, 20), width=2)
    # 主视觉：光晕裁在卡面内，避免溢出到眉标与标题
    glow = Image.new('RGBA', (W // 3, HERO_H // 3), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy = (CX + CW / 2) / 3, (HERO_H / 2) / 3
    gd.ellipse([gx - 112, gy - 104, gx + 112, gy + 104], fill=rgba(cat, 132))
    glow = glow.filter(ImageFilter.GaussianBlur(50)).resize((W, HERO_H), Image.LANCZOS)
    clip = Image.new('L', (W, HERO_H), 0)
    ImageDraw.Draw(clip).rounded_rectangle([CX, 0, CX + CW, HERO_H], radius=HERO_R, fill=255)
    glow.putalpha(ImageChops.multiply(glow.getchannel('A'), clip))
    hero_glow = (glow, hero_y)

    cup_size = 520
    cup = cup_image(sprite, drink['sprite'], cup_size)
    y = hero_y + HERO_H + 46

    # ── 名称 / 配比 / 点评 ──
    name_f = font(74, 'w6')
    while tlen(d, drink['name'], name_f) > CW and name_f.size > 50:
        name_f = font(name_f.size - 4, 'w6')
    texts.append((drink['name'], (CX, y - 8), name_f, TX, -1.5))
    y += int(name_f.size * 1.24)

    rt_f = font(34, 'w6')
    for line in wrap(d, drink['ratio'], rt_f, CW):
        texts.append((line, (CX, y), rt_f, cat, 0))
        y += 50
    y += 12

    tt_f = font(29)
    for line in wrap(d, drink['taste'], tt_f, CW):
        texts.append((line, (CX, y), tt_f, TX2, 0))
        y += 46
    y += 44

    # ── 分区标题 ──
    def section(title, y):
        f = font(24, 'w6')
        end = spaced(sd, (CX, y), title, f, rgba(TX3, 255), 6)
        sd.line([end + 18, y + 15, CX + CW, y + 15], fill=HAIR, width=2)
        return y + 44

    # ── 材料 ──
    y = section('材料', y)
    ing_f = font(29)
    for item in drink['ingredients']:
        sd.rounded_rectangle([CX + 1, y + 17, CX + 9, y + 25], radius=2.5, fill=rgba(cat, 210))
        y = para(y, item, ing_f, mix(TX, TX2, 0.35), CW - 30, 46, x=CX + 30)
        y += 14
    y += 26

    # ── 做法 ──
    y = section('做法', y)
    st_f = font(29)
    for i, step in enumerate(drink['steps'], 1):
        sd.ellipse([CX, y + 3, CX + 38, y + 41], fill=rgba(cat, 46), outline=rgba(cat, 120), width=1)
        num_f = font(20, 'w6')
        nw = tlen(d, str(i), num_f)
        texts.append((str(i), (CX + 19 - nw / 2, y + 10), num_f, mix(cat, (255, 255, 255), 0.45), 0))
        y = para(y + 2, step, st_f, mix(TX, TX2, 0.18), CW - 58, 46, x=CX + 58)
        y += 18
    y += 30

    # ── 底部胶囊 ──
    pill_h = 46
    px_ = CX
    lv_f = font(23)
    lv_w = spaced_len(d, lv_text, lv_f, 0.6) + 36
    if lv:                                  # 无酒精不画强度条
        lv_w += 41
    pill(sd, (px_, y, px_ + lv_w, y + pill_h), (255, 255, 255, 0), HAIR2)
    if lv:
        for i in range(3):
            bx = px_ + 18 + i * 9
            sd.rounded_rectangle([bx, y + 14, bx + 6, y + 32], radius=3,
                                 fill=rgba(cat, 235) if i < lv else (255, 255, 255, 34))
        spaced(sd, (px_ + 18 + 27 + 16, y + 11), lv_text, lv_f, TX2, 0.6)
    else:
        spaced(sd, (px_ + 18, y + 11), lv_text, lv_f, TX2, 0.6)
    px_ += lv_w + 10

    price_txt = '单杯约 ' + drink['price']
    pw = spaced_len(d, price_txt, lv_f, 0.6) + 36
    pill(sd, (px_, y, px_ + pw, y + pill_h), (255, 255, 255, 0), HAIR2)
    spaced(sd, (px_ + 18, y + 11), price_txt, lv_f, TX2, 0.6)
    px_ += pw + 10

    if tag and tag != lv_text:              # 避免「无酒精」重复出现
        tw = spaced_len(d, tag, lv_f, 0.6) + 36
        pill(sd, (px_, y, px_ + tw, y + pill_h), rgba(cat, 46), rgba(cat, 130))
        spaced(sd, (px_ + 18, y + 11), tag, lv_f, mix(cat, (255, 255, 255), 0.45), 0.6)
    y += pill_h + 34

    sd.line([CX, y, CX + CW, y], fill=HAIR, width=2)
    y += 26

    brand_f = font(23, 'w6')
    texts.append((BRAND, (CX, y), brand_f, TX3, 0.6))
    url_w = spaced_len(d, SITE_URL, font(23), 0.6)
    texts.append((SITE_URL, (CX + CW - url_w, y), font(23), TX3, 0.6))
    y += 40
    note_f = font(20)
    texts.append(('AI 饮品示意图 · 口味因人而异 · 饮酒适量，未成年人禁止饮酒', (CX, y), note_f, TX4, 0.4))
    y += 24

    H = y + PAD + M

    # ---------- 合成 ----------
    img = gradient_bg(W, H).convert('RGBA')
    img = Image.alpha_composite(img, orbs(W, H, cat))
    img = Image.alpha_composite(img, shapes.crop((0, 0, W, H)))
    img = _paste_glow(img, hero_glow[0], hero_glow[1], H)

    # 内层卡面边框
    panel = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([M, M, W - M, H - M], radius=44, outline=(255, 255, 255, 22), width=2)
    img = Image.alpha_composite(img, panel)

    cup_bottom = hero_y + HERO_H - 34
    img.paste(cup, (int(CX + CW / 2 - cup_size / 2), int(cup_bottom - cup_size)), cup)

    out = ImageDraw.Draw(img)
    for text, xy, f, fill, ls in texts:
        if ls:
            spaced(out, xy, text, f, fill, ls)
        else:
            out.text(xy, text, font=f, fill=fill)

    img.convert('RGB').save(out_path, 'PNG', optimize=True)
    return H


def _paste_glow(img, glow, top, H):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    layer.paste(glow, (0, top))
    return Image.alpha_composite(img, layer)


def main():
    data = json.load(open(DATA_PATH, encoding='utf-8'))
    drinks = data['drinks']
    want = sys.argv[1:]
    if want:
        drinks = [x for x in drinks if x['name'] in want]
        if not drinks:
            sys.exit('没有匹配的配方：' + '、'.join(want))
    os.makedirs(OUT_DIR, exist_ok=True)
    sprite = Image.open(SPRITE_PATH).convert('RGB')
    for x in drinks:
        path = os.path.join(OUT_DIR, 'card-%02d.png' % x['index'])
        h = render(x, sprite, path)
        print('%-16s %s  %dx%d  %.0f KB' % (x['name'], os.path.relpath(path, ROOT), W, h,
                                            os.path.getsize(path) / 1024))


if __name__ == '__main__':
    main()
