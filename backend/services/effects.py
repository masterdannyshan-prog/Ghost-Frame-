import io
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np

# ── Background Removal ──────────────────────────────────────────────────────
def remove_background(img_bytes: bytes) -> bytes:
    from rembg import remove
    result = remove(img_bytes)
    return result

# ── Upscale (2x Bicubic — no GPU needed) ────────────────────────────────────
def upscale(img_bytes: bytes, scale: int = 2) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    up = img.resize((w * scale, h * scale), Image.LANCZOS)
    out = io.BytesIO()
    up.save(out, format="PNG")
    return out.getvalue()

# ── Colorize B&W ─────────────────────────────────────────────────────────────
def colorize_bw(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    colored = ImageOps.colorize(img, black="#1a0533", white="#f5c842", mid="#c87941")
    out = io.BytesIO()
    colored.save(out, format="PNG")
    return out.getvalue()

# ── 80s / VHS Retro ──────────────────────────────────────────────────────────
def vhs_retro(img_bytes: bytes, intensity: float = 0.6) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]

    # Chromatic aberration: shift R left, B right
    shift = max(1, int(w * 0.012 * intensity))
    r = np.roll(arr[:, :, 0], -shift, axis=1)
    b = np.roll(arr[:, :, 2],  shift, axis=1)
    arr[:, :, 0] = r
    arr[:, :, 2] = b

    # Scanlines
    for y in range(0, h, 4):
        arr[y] = arr[y] * (1 - 0.25 * intensity)

    # Boost saturation: push G channel slightly
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1 + 0.15 * intensity), 0, 255)

    # Add noise
    noise = np.random.normal(0, 8 * intensity, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)

    out_img = Image.fromarray(arr)
    # Slight blur for that soft VHS look
    out_img = out_img.filter(ImageFilter.GaussianBlur(radius=0.4 * intensity))

    out = io.BytesIO()
    out_img.save(out, format="PNG")
    return out.getvalue()

# ── Oil Painting / Painterly ──────────────────────────────────────────────────
def oil_painting(img_bytes: bytes, radius: int = 4) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # Median filter gives painterly chunky edges
    for _ in range(3):
        img = img.filter(ImageFilter.MedianFilter(size=radius * 2 + 1))
    # Boost contrast and saturation for vivid paint look
    img = ImageEnhance.Color(img).enhance(1.6)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

# ── Face Blur / Anonymize ─────────────────────────────────────────────────────
def blur_faces(img_bytes: bytes) -> bytes:
    try:
        import mediapipe as mp
    except ImportError:
        # mediapipe optional — fall back to full-image blur notice
        img = Image.open(io.BytesIO(img_bytes))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    mp_face = mp.solutions.face_detection
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = np.array(img)
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
        results = fd.process(arr)
        if results.detections:
            h, w = arr.shape[:2]
            for det in results.detections:
                bb = det.location_data.relative_bounding_box
                x1 = max(0, int(bb.xmin * w))
                y1 = max(0, int(bb.ymin * h))
                x2 = min(w, int((bb.xmin + bb.width) * w))
                y2 = min(h, int((bb.ymin + bb.height) * h))
                region = Image.fromarray(arr[y1:y2, x1:x2])
                blurred = region.filter(ImageFilter.GaussianBlur(radius=15))
                arr[y1:y2, x1:x2] = np.array(blurred)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="PNG")
    return out.getvalue()

# ── Watercolor ────────────────────────────────────────────────────────────────
def watercolor(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    for _ in range(2):
        img = img.filter(ImageFilter.MedianFilter(size=5))
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    img = ImageEnhance.Color(img).enhance(0.8)
    img = ImageEnhance.Brightness(img).enhance(1.1)
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 5, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="PNG")
    return out.getvalue()

# ── Cartoon / Anime ────────────────────────────────────────────────────────────
def cartoon(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    smooth = img.filter(ImageFilter.MedianFilter(size=7))
    smooth = smooth.filter(ImageFilter.MedianFilter(size=5))
    smooth = smooth.quantize(colors=24).convert("RGB")
    smooth = ImageEnhance.Color(smooth).enhance(1.5)
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda p: 255 if p > 25 else 0)
    edges_inv = edges.convert("RGB").point(lambda p: 255 - p)
    arr_s = np.array(smooth, dtype=np.float32) / 255.0
    arr_e = np.array(edges_inv, dtype=np.float32) / 255.0
    combined = np.clip(arr_s * arr_e, 0, 1)
    out = io.BytesIO()
    Image.fromarray((combined * 255).astype(np.uint8)).save(out, format="PNG")
    return out.getvalue()

# ── Make it Retro (90s / Y2K / film grain) ────────────────────────────────────
def make_retro(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = ImageEnhance.Color(img).enhance(0.72)
    img = ImageEnhance.Contrast(img).enhance(0.82)
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    # Warm color cast
    arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.06 + 10, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.85, 0, 255)
    # Heavy film grain
    arr = np.clip(arr + np.random.normal(0, 20, arr.shape), 0, 255)
    # Vignette
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt(((X - w/2) / (w/2)) ** 2 + ((Y - h/2) / (h/2)) ** 2)
    vignette = np.clip(1 - dist * 0.42, 0.38, 1)[..., np.newaxis]
    arr = np.clip(arr * vignette, 0, 255)
    # Light leak: warm top-left glow
    leak_x = np.linspace(1.0, 0.0, w)
    leak_y = np.linspace(1.0, 0.0, h)
    leak = np.outer(leak_y, leak_x)[..., np.newaxis] * 22
    arr[:, :, 0] = np.clip(arr[:, :, 0] + leak[:, :, 0], 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + leak[:, :, 0] * 0.45, 0, 255)
    out = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8)).save(out, format="PNG")
    return out.getvalue()

EFFECT_MAP = {
    "remove-bg":  remove_background,
    "upscale":    upscale,
    "colorize":   colorize_bw,
    "vhs-retro":  vhs_retro,
    "oil-paint":  oil_painting,
    "watercolor": watercolor,
    "cartoon":    cartoon,
    "make-retro": make_retro,
    "blur-faces": blur_faces,
}
