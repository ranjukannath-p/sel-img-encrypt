from PIL import Image, ImageDraw

def redact_with_boxes(img: Image.Image, boxes: list[list[list[int]]]) -> Image.Image:
    # boxes: list of polygons (here rect as 4 points [[x,y],...])
    out = img.copy()
    draw = ImageDraw.Draw(out)
    for poly in boxes:
        # assume rectangle with 4 points
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        draw.rectangle(bbox, fill=(0,0,0))
    return out
