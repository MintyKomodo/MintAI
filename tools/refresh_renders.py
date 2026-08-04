"""Rebuild the site's product images from the Blender render set.

Sources are the pure-black Cycles stills out of design-3d/case_hero.py
(`--bg black`, and `--bg alpha` for the one cutout the light theme needs).
The renders are 2600-3200 px with a lot of empty backdrop; the site images are
tight crops at fixed sizes the HTML declares. This trims each render to its
subject, pads it back out to the target aspect with the render's own background
colour, and writes at the size the markup expects.

Two modes:
  crop  trim to the subject, then pad to the target aspect. For card images.
  raw   no trimming at all, just a resize. For the full-bleed page backdrop,
        where the render was already framed for the frame and cropping to the
        subject would throw away the composition.

Sources with an alpha channel stay RGBA the whole way through, so the light
theme backdrop is a real cutout rather than a keyed one.

  python tools/refresh_renders.py            # write
  python tools/refresh_renders.py --dry      # report only
"""
import os
import shutil
import sys

from PIL import Image

CASE = r'C:\MintWatch\design-3d\board\out'
BOARD = r'C:\MintWatch\design-3d\board\out'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(HERE, 'img', '_pre_refresh')

# target file, source render, size the HTML declares, padding around subject, mode
JOBS = [
    # Full-viewport fixed backdrop, dark theme and light theme. Rendered 16:9 at
    # 3200x1800 and framed for it, so both go through untouched.
    ('img/view-side.webp',          f'{CASE}/case_flank_wide_black.png', (2400, 1350), 0.00, 'raw'),
    ('img/view-side-cut.webp',      f'{CASE}/case_flank_wide_alpha.png', (2400, 1350), 0.00, 'raw'),
    # Card images beside body copy. view-side-card is the same flank render as the
    # backdrop, but trimmed to the watch: the backdrop is framed for a full screen
    # and reads as a small watch in a lot of black when it is dropped into a card.
    ('img/view-side-card.webp',     f'{CASE}/case_flank_wide_black.png', (1600, 1067), 0.06, 'crop'),
    ('img/render-angle.webp',       f'{CASE}/case_quarter_black.png',    (1600, 1200), 0.06, 'crop'),
    # a hair of padding, not zero: subject_box subsamples, so a flush crop
    # shaves a few pixels off the bezel
    ('img/render-face.webp',        f'{CASE}/case_dial_black.png',       (1600, 1067), 0.02, 'crop'),
    ('img/render-charge.webp',      f'{CASE}/case_dock_black.png',       (1600, 1067), 0.05, 'crop'),
    ('img/view-three-quarter.webp', f'{CASE}/case_hero_black.png',       (1100, 1100), 0.08, 'crop'),
]


def subject_box(im, tol=14):
    """Bounding box of everything that is not the flat backdrop.

    On an RGBA source the alpha channel already is the subject mask, and using
    it avoids the tolerance guesswork entirely.
    """
    if im.mode == 'RGBA':
        box = im.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
        return (box or (0, 0, im.width, im.height)), (0, 0, 0, 0)
    rgb = im.convert('RGB')
    bg = rgb.getpixel((2, 2))
    w, h = rgb.size
    px = rgb.load()
    step = max(1, min(w, h) // 600)
    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > tol:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
                if y < y0:
                    y0 = y
                if y > y1:
                    y1 = y
    if x1 <= x0 or y1 <= y0:
        return (0, 0, w, h), bg
    return (x0, y0, x1, y1), bg


def load(src):
    """RGBA if the source carries transparency of any kind, else RGB.

    A palette PNG reports bands ('P',) even when its tRNS chunk makes it
    transparent, so the check is on info, not on the band list.
    """
    im = Image.open(src)
    alpha = im.mode in ('RGBA', 'LA', 'PA') or 'transparency' in im.info
    if not alpha:
        return im.convert('RGB')
    im = im.convert('RGBA')
    # Blender writes RGBA even when film_transparent is off, so a black-backdrop
    # render arrives with a channel that is 255 everywhere. Keeping it would make
    # subject_box treat the whole frame as subject and skip the crop entirely.
    if im.getchannel('A').getextrema()[0] == 255:
        return im.convert('RGB')
    return im


def build(src, size, pad, mode):
    im = load(src)
    if mode == 'raw':
        # raw resizes without trimming, so a source whose aspect does not match
        # the target would be stretched. Fail loudly instead: silently squashing
        # the full-viewport backdrop is not something anyone would spot in a diff.
        want, have = size[0] / size[1], im.width / im.height
        if abs(want - have) > 0.01:
            raise SystemExit('%s is %dx%d (%.3f) but target %dx%d is %.3f; '
                             're-render at the target aspect or use crop mode'
                             % (os.path.basename(src), im.width, im.height, have,
                                size[0], size[1], want))
        return im.resize(size, Image.LANCZOS)

    (x0, y0, x1, y1), bg = subject_box(im)
    sw, sh = x1 - x0, y1 - y0
    px = int(max(sw, sh) * pad)
    x0, y0 = max(0, x0 - px), max(0, y0 - px)
    x1, y1 = min(im.width, x1 + px), min(im.height, y1 + px)
    crop = im.crop((x0, y0, x1, y1))

    # pad (never stretch) to the target aspect
    tw, th = size
    want = tw / th
    have = crop.width / crop.height
    if have > want:
        nh = int(crop.width / want)
        canvas = Image.new(im.mode, (crop.width, nh), bg)
        canvas.paste(crop, (0, (nh - crop.height) // 2))
    else:
        nw = int(crop.height * want)
        canvas = Image.new(im.mode, (nw, crop.height), bg)
        canvas.paste(crop, ((nw - crop.width) // 2, 0))
    return canvas.resize(size, Image.LANCZOS)


def main():
    dry = '--dry' in sys.argv
    os.makedirs(BACKUP, exist_ok=True)
    for rel, src, size, pad, mode in JOBS:
        dst = os.path.join(HERE, rel)
        if not os.path.isfile(src):
            print('SKIP %-30s source missing: %s' % (rel, src))
            continue
        out = build(src, size, pad, mode)
        before = os.path.getsize(dst) / 1024 if os.path.isfile(dst) else 0
        if dry:
            print('would write %-30s %dx%d %s  (was %.0f KB)'
                  % (rel, size[0], size[1], out.mode, before))
            continue
        if os.path.isfile(dst):
            keep = os.path.join(BACKUP, os.path.basename(dst))
            if not os.path.isfile(keep):
                shutil.copy2(dst, keep)
        if dst.lower().endswith('.webp'):
            out.save(dst, 'WEBP', quality=90, method=6)
        else:
            out.save(dst, 'JPEG', quality=86, optimize=True, progressive=True)
        after = os.path.getsize(dst) / 1024
        print('%-30s %4dx%-4d %-4s %6.0f KB -> %6.0f KB   <- %s'
              % (rel, size[0], size[1], out.mode, before, after, os.path.basename(src)))
    if not dry:
        print('\noriginals kept in img/_pre_refresh/')


if __name__ == '__main__':
    main()
