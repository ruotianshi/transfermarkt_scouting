"""
Generates a small SVG football formation diagram.
Returns an SVG string suitable for embedding in HTML.
"""

FORMATIONS = {
    "4-4-2":   [[1], [2, 5, 6, 3], [7, 8, 4, 11], [9, 10]],
    "4-3-3":   [[1], [2, 5, 6, 3], [8, 4, 10], [7, 9, 11]],
    "4-2-3-1": [[1], [2, 5, 6, 3], [4, 8], [7, 10, 11], [9]],
    "4-1-4-1": [[1], [2, 5, 6, 3], [4], [7, 8, 10, 11], [9]],
    "3-5-2":   [[1], [5, 6, 4], [2, 8, 10, 11, 3], [9, 7]],
    "3-4-3":   [[1], [5, 6, 4], [2, 8, 10, 3], [7, 9, 11]],
    "5-3-2":   [[1], [2, 5, 6, 4, 3], [8, 10, 11], [9, 7]],
    "4-5-1":   [[1], [2, 5, 6, 3], [7, 8, 4, 10, 11], [9]],
}

FIELD_COLOR   = "#1a5c2a"
LINE_COLOR    = "#ffffff"
DOT_COLOR     = "#ffffff"
DOT_RADIUS    = 4


def formation_svg(formation_str: str, width: int = 80, height: int = 110) -> str:
    """
    Returns a standalone SVG string for the given formation (e.g. '4-2-3-1').
    Width/height are the SVG canvas dimensions in px.
    """
    rows = FORMATIONS.get(formation_str)
    if rows is None:
        # Fallback: parse formation string dynamically
        rows = _parse_formation(formation_str)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',

        # Background pitch
        f'<rect width="{width}" height="{height}" fill="{FIELD_COLOR}" rx="3"/>',

        # Centre line
        f'<line x1="4" y1="{height//2}" x2="{width-4}" y2="{height//2}" '
        f'stroke="{LINE_COLOR}" stroke-width="0.8" stroke-opacity="0.5"/>',

        # Centre circle (simplified)
        f'<circle cx="{width//2}" cy="{height//2}" r="8" fill="none" '
        f'stroke="{LINE_COLOR}" stroke-width="0.8" stroke-opacity="0.5"/>',

        # Penalty boxes
        _penalty_box(width, height, top=True),
        _penalty_box(width, height, top=False),
    ]

    # Player dots — GK at bottom, attack at top
    # FORMATIONS rows are ordered [GK, defenders, ..., attackers]
    # row_idx=0 (GK) → largest y (bottom); last row (attackers) → smallest y (top)
    n_rows = len(rows)
    for row_idx, row in enumerate(rows):
        y_frac = (n_rows - row_idx) / (n_rows + 1)
        y = int(y_frac * height)

        n_players = len(row)
        for col_idx in range(n_players):
            x_frac = (col_idx + 1) / (n_players + 1)
            x = int(x_frac * width)
            svg_parts.append(
                f'<circle cx="{x}" cy="{y}" r="{DOT_RADIUS}" '
                f'fill="{DOT_COLOR}" stroke="{FIELD_COLOR}" stroke-width="0.5"/>'
            )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def formation_svg_base64(formation_str: str, width: int = 80, height: int = 110) -> str:
    """Returns a data URI (base64-encoded SVG) for use in <img src='...'>."""
    import base64
    svg = formation_svg(formation_str, width, height)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _penalty_box(width: int, height: int, top: bool) -> str:
    bw = int(width * 0.55)
    bh = int(height * 0.12)
    bx = (width - bw) // 2
    by = 2 if top else height - bh - 2
    return (
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" '
        f'fill="none" stroke="{LINE_COLOR}" stroke-width="0.8" stroke-opacity="0.5"/>'
    )


def _parse_formation(formation_str: str) -> list:
    """
    Dynamically build rows from a string like '4-3-3'.
    Returns rows ordered [GK, defenders, ..., attackers] — GK renders at bottom.
    """
    try:
        parts = [int(x) for x in formation_str.split("-")]
    except ValueError:
        return [[1], [2, 3, 4, 5], [6, 7, 8, 9], [10, 11]]

    rows = [[1]]  # GK first → rendered at bottom
    for n in parts:
        rows.append([i + 1 for i in range(n)])
    return rows
