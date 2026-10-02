"""Build the China Room Brief banner from the CSIS comms banner.

Keeps the CSIS logo lockup and navy exactly as CSIS made them
(csis_rtw_banner_source.png, the "Released This Week" banner from the Pardot
file host) and replaces only the outlined label box.

    python assets/make_banner.py "CHINA ROOM BRIEF"
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
NAVY = (0, 31, 89)          # sampled from the source banner
BORDER = (0, 125, 173)      # sampled: 3px box outline
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def build(label: str, out: Path) -> None:
    im = Image.open(HERE / "csis_rtw_banner_source.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([100, 112, 500, 190], fill=NAVY)        # clear the old box
    font = ImageFont.truetype(FONT, 27)
    l, t, r, b = d.textbbox((0, 0), label, font=font)
    tw, th = r - l, b - t
    pad_x, pad_y = 18, 15                                # source text-to-border padding
    bw, bh = tw + 2 * pad_x, 49                          # source box height
    x0 = (im.width - bw) // 2
    y0 = 123
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh - 1], radius=7, outline=BORDER, width=3)
    d.text((x0 + pad_x - l, y0 + (bh - th) // 2 - t), label, font=font, fill=(255, 255, 255))
    im.save(out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "CHINA ROOM BRIEF", HERE / "banner_china_room.png")
