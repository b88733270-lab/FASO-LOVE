#!/usr/bin/env python3
"""Génère les avatars génériques FASO LOVE (silhouettes neutres).

Ces placeholders remplacent les photos de personnes réelles présentes dans
le projet d'origine (supprimées pour des raisons juridiques et éthiques).
Ils sont volontairement abstraits : dégradé pastel + silhouette blanche,
sans aucun visage identifiable. Aucune dépendance externe (stdlib only).

Usage : python3 tools/generate_placeholders.py
Sortie : assets/placeholders/avatar_1.png … avatar_6.png
"""
import os
import struct
import zlib

WIDTH, HEIGHT = 600, 800
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "placeholders")

# Palette FASO LOVE : couples (haut, bas) pour le dégradé vertical.
PALETTES = [
    ((217, 108, 71), (232, 168, 124)),    # terracotta
    ((212, 160, 23), (240, 199, 94)),     # doré savane
    ((27, 122, 67), (82, 183, 136)),      # vert Burkina
    ((62, 92, 118), (116, 140, 171)),     # bleu ardoise
    ((123, 67, 151), (177, 133, 219)),    # prune
    ((14, 124, 123), (78, 205, 196)),     # sarcelle
]


def pixel(x, y, top, bottom):
    t = y / HEIGHT
    r = top[0] + (bottom[0] - top[0]) * t
    g = top[1] + (bottom[1] - top[1]) * t
    b = top[2] + (bottom[2] - top[2]) * t
    # Silhouette blanche : tête (cercle) + épaules (cercle bas)
    head = (x - WIDTH / 2) ** 2 + (y - 350) ** 2 <= 120 ** 2
    shoulders = (x - WIDTH / 2) ** 2 + (y - 780) ** 2 <= 190 ** 2
    if head or shoulders:
        a = 0.92
        r, g, b = r * (1 - a) + 255 * a, g * (1 - a) + 255 * a, b * (1 - a) + 255 * a
    return int(r), int(g), int(b)


def write_png(path, width, height, top, bottom):
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filtre PNG « None »
        for x in range(width):
            raw.extend(pixel(x, y, top, bottom))

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for i, (top, bottom) in enumerate(PALETTES, start=1):
        path = os.path.join(OUT_DIR, f"avatar_{i}.png")
        write_png(path, WIDTH, HEIGHT, top, bottom)
        print(f"généré : {path}")


if __name__ == "__main__":
    main()
