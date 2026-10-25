from pathlib import Path
from PIL import Image, ImageDraw


def create_app_icon(output_path: Path):
    """Generates a professional multi-resolution ICO file for QuickConvert."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for w, h in sizes:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Outer rounded squircle background with pastel lavender/indigo
        pad = max(1, w // 16)
        radius = max(2, w // 4)
        draw.rounded_rectangle(
            [pad, pad, w - pad, h - pad],
            radius=radius,
            fill=(124, 58, 237, 255),        # Deep purple/lavender
            outline=(167, 139, 250, 230),     # Delicate lighter border
            width=max(1, w // 32),
        )

        # Lightning bolt / convert arrow accent
        cx, cy = w / 2, h / 2
        scale = w / 256.0

        # Draw convert lightning bolt
        points = [
            (cx + 8 * scale, cy - 80 * scale),
            (cx - 52 * scale, cy + 10 * scale),
            (cx - 4 * scale, cy + 10 * scale),
            (cx - 16 * scale, cy + 80 * scale),
            (cx + 56 * scale, cy - 10 * scale),
            (cx + 4 * scale, cy - 10 * scale),
        ]
        draw.polygon(points, fill=(255, 255, 255, 255))

        images.append(img)

    # Save as multi-resolution ICO
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(im.width, im.height) for im in images],
        append_images=images[1:],
    )
    print(f"Generated multi-size icon: {output_path}")


if __name__ == "__main__":
    create_app_icon(Path("assets/icon.ico"))
