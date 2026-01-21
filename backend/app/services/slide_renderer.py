import textwrap
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings

IMAGE_DIR = settings.image_dir
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = settings.video_width, settings.video_height
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
        (WIDTH / 2, HEIGHT / 2),
        wrapped_text,
        fill="black",
        font=font,
        spacing=10,
        align="center",
        anchor="mm",
    )

    path = IMAGE_DIR / f"{uuid.uuid4()}.png"
    img.save(path)

    return str(path)
