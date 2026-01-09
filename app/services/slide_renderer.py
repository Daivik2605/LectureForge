from PIL import Image, ImageDraw, ImageFont
import uuid
from pathlib import Path
import textwrap

IMAGE_DIR = Path("data/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1280, 720
MARGIN_X, MARGIN_Y = 80, 80
MAX_CHARS_PER_LINE = 60

def render_slide_image(text: str) -> str:
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("Arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=MAX_CHARS_PER_LINE)

    draw.multiline_text(
        (MARGIN_X, MARGIN_Y),
        wrapped_text,
        fill="black",
        font=font,
        spacing=10
    )

    path = IMAGE_DIR / f"{uuid.uuid4()}.png"
    img.save(path)

    return str(path)
