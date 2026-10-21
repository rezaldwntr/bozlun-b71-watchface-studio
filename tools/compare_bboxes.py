import numpy as np
from PIL import Image

ref = Image.open(r'C:\Users\ACER\.gemini\antigravity\brain\ab96e856-a382-4f93-83cd-76cf4114ce96\khnst02_ref_466.png').convert('L')
proto = Image.open(r'C:\Users\ACER\.gemini\antigravity\brain\ab96e856-a382-4f93-83cd-76cf4114ce96\test_v4_prototype.png').convert('L')

ref_arr = np.array(ref) > 100
proto_arr = np.array(proto) > 100

def get_bbox(mask, y1, y2, x1, x2):
    sub = mask[y1:y2, x1:x2]
    ys, xs = np.where(sub)
    if len(ys) == 0: return None
    return (int(xs.min() + x1), int(ys.min() + y1), int(xs.max() + x1), int(ys.max() + y1))

elements = [
    ('Time 1', 150, 235, 70, 115),
    ('Time 0', 150, 235, 115, 180),
    ('Colon Top', 170, 195, 180, 202),
    ('Colon Bot', 200, 225, 180, 202),
    ('Time 4', 150, 235, 200, 260),
    ('Time 5', 150, 235, 255, 315),
    ('Date SUN', 120, 155, 80, 160),
    ('Date 23', 120, 155, 175, 225),
    ('Date Dot', 140, 155, 224, 234),
    ('Date 09', 120, 155, 233, 280),
    ('Fit STEP', 235, 260, 80, 155),
    ('Fit Val 90', 235, 260, 270, 320),
    ('Fit HR', 260, 285, 80, 240),
    ('Fit Val 068', 260, 285, 270, 335),
    ('Fit KCAL', 285, 310, 80, 155),
    ('Fit Val 2200', 285, 310, 270, 345),
    ('Fit DIST', 310, 338, 80, 215),
    ('Fit Val 4.65', 310, 338, 270, 340),
    ('Battery Caps', 50, 72, 180, 280),
    ('Battery 90%', 72, 98, 195, 255)
]

print(f"{'Element':<15} | {'Reference BBox':<18} | {'Prototype BBox':<18} | Delta (dx, dy)")
print('-' * 70)
for name, y1, y2, x1, x2 in elements:
    rb = get_bbox(ref_arr, y1, y2, x1, x2)
    pb = get_bbox(proto_arr, y1, y2, x1, x2)
    if rb and pb:
        dx = pb[0] - rb[0]
        dy = pb[1] - rb[1]
        print(f"{name:<15} | [{rb[0]},{rb[1]}..{rb[2]},{rb[3]}] | [{pb[0]},{pb[1]}..{pb[2]},{pb[3]}] | dx={dx:+2d}, dy={dy:+2d}")
    else:
        print(f"{name:<15} | Ref: {rb} | Proto: {pb}")
