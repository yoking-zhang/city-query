"""生成 Docker Hub 图标 logo (256x256)"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

SIZE = 256
W, H = SIZE, SIZE

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── 背景圆角矩形 ──
bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
bg_draw = ImageDraw.Draw(bg)

# 渐变底色（外层深蓝，内层偏紫蓝）
r1, g1, b1 = 30, 58, 95    # #1E3A5F
r2, g2, b2 = 18, 33, 55    # #122137

for y in range(SIZE):
    t = y / SIZE
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    for x in range(SIZE):
        # 圆角裁剪
        cx, cy = x - SIZE // 2, y - SIZE // 2
        dist = math.sqrt(max(0, abs(cx) - SIZE // 2 + 30)**2 + max(0, abs(cy) - SIZE // 2 + 30)**2)
        if dist <= 30:
            continue
        bg.putpixel((x, y), (r, g, b, 255))

# 软边缘
bg = bg.filter(ImageFilter.GaussianBlur(radius=2))

# ── 城市天际线 ──
buildings = [
    # (x_center, width, height, color_lightness)
    (48,  22,  50,  (160, 190, 220)),
    (72,  18,  70,  (140, 175, 215)),
    (92,  24,  45,  (170, 200, 230)),
    (115, 16,  80,  (130, 165, 210)),
    (132, 20,  55,  (155, 185, 220)),
    (152, 26,  38,  (175, 205, 235)),
    (178, 14,  90,  (120, 155, 205)),
    (193, 20,  65,  (145, 180, 215)),
    (213, 18,  48,  (165, 195, 225)),
    (232, 22,  35,  (180, 210, 235)),
    (30,  16,  28,  (170, 195, 225)),
    (210, 12,  105, (110, 148, 200)),
]

base_y = 200
for cx, w, h, clr in buildings:
    by = base_y
    x1, y1 = cx - w // 2, by - h
    x2, y2 = cx + w // 2, by
    draw.rectangle([x1, y1, x2, y2], fill=(*clr, 200))

    # 窗户
    win_color = (255, 255, 255, 80)
    for wx in range(x1 + 3, x2 - 2, 5):
        for wy in range(y1 + 3, y2 - 4, 5):
            draw.rectangle([wx, wy, wx + 2, wy + 2], fill=win_color)

# 地平面光晕
for i in range(3):
    glow_y = base_y + 2 + i * 3
    draw.ellipse(
        [40, glow_y, SIZE - 40, glow_y + 4],
        fill=(100, 180, 255, 20 - i * 5),
    )

# ── 放大镜 ──
cx, cy = 128, 118
circle_r = 42

# 镜框外发光
for r in range(8, 0, -1):
    draw.ellipse(
        [cx - circle_r - r, cy - circle_r - r,
         cx + circle_r + r, cy + circle_r + r],
        outline=(100, 200, 255, 12 - r),
        width=1,
    )

# 镜框
draw.ellipse(
    [cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
    outline=(180, 220, 255, 220),
    width=4,
)

# 镜面（半透明）
draw.ellipse(
    [cx - circle_r + 6, cy - circle_r + 6,
     cx + circle_r - 6, cy + circle_r - 6],
    fill=(200, 230, 255, 30),
)

# 镜面高光 (左上角反光)
draw.ellipse(
    [cx - circle_r + 10, cy - circle_r + 10,
     cx - circle_r // 2, cy - circle_r // 2],
    fill=(220, 240, 255, 60),
)

# 镜柄
handle_length = 34
handle_width = 6
angle = math.radians(45)
hx = cx + int(circle_r * math.cos(angle))
hy = cy + int(circle_r * math.sin(angle))
hex = hx + int(handle_length * math.cos(angle))
hey = hy + int(handle_length * math.sin(angle))

draw.line([(hx, hy), (hex, hey)], fill=(180, 220, 255, 220), width=handle_width)

# 底部的 CQ 文字
try:
    # macOS 常用中文字体
    font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 28)
except (IOError, OSError):
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", 28)
    except (IOError, OSError):
        font = ImageFont.load_default()

text = "CQ"
text_color = (180, 215, 255, 200)
# 文字阴影
draw.text((128 - 28 + 2, 222 + 2), text, font=font, fill=(0, 0, 0, 60))
draw.text((128 - 28, 222), text, font=font, fill=text_color)

# ── 合并背景 ──
final = Image.alpha_composite(bg, img)

# ── 裁剪圆角 ──
mask = Image.new("L", (SIZE, SIZE), 0)
mask_draw = ImageDraw.Draw(mask)
mask_draw.rounded_rectangle([(0, 0), (SIZE-1, SIZE-1)], radius=28, fill=255)
final = Image.alpha_composite(
    Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)),
    final,
)
final.putalpha(mask)

final.save("docker_logo.png")
print("✅ 已生成 docker_logo.png (256x256)")
final.show()
