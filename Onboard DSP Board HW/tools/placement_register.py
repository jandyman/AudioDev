"""
Generate the placement register for the onboard DSP board from the KiCad PCB.

Reads a .kicad_pcb, extracts every placed footprint, and writes a markdown
register describing where things physically sit. The register is generated so
it cannot drift from the layout: re-run after any placement change.

Deliberately keyed by part value and function, never by reference designator --
designators change on re-annotation, so a document built on them rots. Passives
are aggregated by value within each zone; distinct parts are listed individually.

Zone boundaries and the distance pairs of interest are named variables at the
bottom of the file.
"""

import math
import re
from pathlib import Path

# A value is treated as a passive (aggregated, not listed individually) when it
# looks like a bare component value rather than a part name.
PASSIVE_VALUE = re.compile(
    r"^\s*[\d.]+\s*(pF|nF|uF|µF|mF|H|uH|µH|nH|mH|R|k|K|M|Ω|ohm)?\s*$", re.I)


def read_footprints(pcb_path):
    """Parse footprints out of a .kicad_pcb.

    Returns a list of dicts with value, footprint library id, board position,
    rotation, layer, and global pad positions keyed by pad number.
    """
    text = Path(pcb_path).read_text()
    footprints = []
    for match in re.finditer(r'\(footprint "', text):
        block = _balanced_block(text, match.start())
        value = _property(block, "Value")
        placement = re.search(
            r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
        if value is None or placement is None:
            continue
        origin_x = float(placement.group(1))
        origin_y = float(placement.group(2))
        rotation = float(placement.group(3) or 0.0)
        layer = re.search(r'\(layer "([^"]+)"', block)
        footprints.append({
            "value": value,
            "library": re.match(r'\(footprint "([^"]+)"', block).group(1),
            "x": origin_x,
            "y": origin_y,
            "rotation": rotation,
            "layer": layer.group(1) if layer else "?",
            "pads": _pad_positions(block, origin_x, origin_y, rotation),
        })
    return footprints


def _balanced_block(text, start):
    """Return the parenthesis-balanced s-expression beginning at start."""
    depth = 0
    index = start
    while index < len(text):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
        index += 1
    return text[start:]


def _property(block, name):
    found = re.search(r'\(property "%s" "([^"]*)"' % name, block)
    return found.group(1) if found else None


def _pad_positions(block, origin_x, origin_y, rotation):
    """Map pad number -> global (x, y), applying the footprint rotation."""
    angle = math.radians(rotation)
    pads = {}
    for pad in re.finditer(r'\(pad "([^"]+)" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)',
                           block):
        local_x = float(pad.group(2))
        local_y = float(pad.group(3))
        pads[pad.group(1)] = (
            origin_x + local_x * math.cos(angle) + local_y * math.sin(angle),
            origin_y - local_x * math.sin(angle) + local_y * math.cos(angle),
        )
    return pads


def assign_zones(footprints, zone_bounds):
    """Bucket footprints into named zones by position along the long axis."""
    zones = {name: [] for name, _ in zone_bounds}
    for footprint in footprints:
        for name, upper_x in zone_bounds:
            if footprint["x"] < upper_x:
                zones[name].append(footprint)
                break
    return zones


def find_part(footprints, value):
    """Return the first footprint whose value matches, else None."""
    for footprint in footprints:
        if footprint["value"] == value:
            return footprint
    return None


def nearest_distance(footprints, value_a, value_b):
    """Smallest centre-to-centre distance between any part of each value.

    Values often appear more than once (two ADC codecs, many identical
    passives). Reporting the first match found would silently describe the
    wrong part, so every pairing is measured and the closest returned.
    """
    group_a = [f for f in footprints if f["value"] == value_a]
    group_b = [f for f in footprints if f["value"] == value_b]
    if not group_a or not group_b:
        return None
    return min(distance((a["x"], a["y"]), (b["x"], b["y"]))
               for a in group_a for b in group_b)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def format_register(footprints, zone_bounds, distance_pairs, pin_groups,
                    pcb_name):
    """Build the whole markdown document as a single string."""
    lines = []
    xs = [f["x"] for f in footprints]
    ys = [f["y"] for f in footprints]
    back_side = [f for f in footprints if f["layer"] != "F.Cu"]

    lines.append("# Placement Register — Onboard DSP Board")
    lines.append("")
    lines.append("**Generated file — do not hand-edit.** Produced by "
                 "`tools/placement_register.py` from `%s`. Re-run after any "
                 "placement change." % pcb_name)
    lines.append("")
    lines.append("Parts are keyed by **value and function, not reference "
                 "designator** — designators change on re-annotation. Passives "
                 "are aggregated by value within each zone; distinct parts are "
                 "listed individually.")
    lines.append("")
    lines.append("## Board extents")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append("| Placed footprints | %d |" % len(footprints))
    lines.append("| Long axis (x) span | %.1f mm (%.1f … %.1f) |"
                 % (max(xs) - min(xs), min(xs), max(xs)))
    lines.append("| Short axis (y) span | %.1f mm (%.1f … %.1f) |"
                 % (max(ys) - min(ys), min(ys), max(ys)))
    lines.append("| Back-side parts | %s |"
                 % ("none — single-sided" if not back_side
                    else "%d" % len(back_side)))
    lines.append("")

    zones = assign_zones(footprints, zone_bounds)
    for name, _ in zone_bounds:
        members = sorted(zones[name], key=lambda f: f["x"])
        if not members:
            continue
        zone_xs = [f["x"] for f in members]
        lines.append("## Zone — %s" % name)
        lines.append("")
        lines.append("Spans x = %.1f … %.1f mm, %d parts."
                     % (min(zone_xs), max(zone_xs), len(members)))
        lines.append("")
        lines.append("| Part | x (mm) | y (mm) | Package |")
        lines.append("|---|---|---|---|")
        for footprint in members:
            if PASSIVE_VALUE.match(footprint["value"]):
                continue
            lines.append("| %s | %.2f | %.2f | %s |"
                         % (footprint["value"], footprint["x"], footprint["y"],
                            footprint["library"].split(":")[-1]))
        passives = _aggregate_passives(members)
        for value, (count, low, high) in sorted(passives.items()):
            span = "%.1f" % low if count == 1 else "%.1f … %.1f" % (low, high)
            lines.append("| %s (×%d) | %s | — | passive |" % (value, count, span))
        lines.append("")

    lines.append("## Key distances")
    lines.append("")
    lines.append("Centre-to-centre unless a pin is named. These are the "
                 "separations the layout rationale depends on.")
    lines.append("")
    lines.append("| From | To | Distance |")
    lines.append("|---|---|---|")
    for label_a, label_b, value_a, value_b in distance_pairs:
        span = nearest_distance(footprints, value_a, value_b)
        if span is None:
            lines.append("| %s | %s | *not placed* |" % (label_a, label_b))
            continue
        lines.append("| %s | %s | %.2f mm |" % (label_a, label_b, span))
    lines.append("")

    for group in pin_groups:
        host = find_part(footprints, group["part_value"])
        if host is None:
            continue
        lines.append("## Pin geometry — %s" % group["title"])
        lines.append("")
        lines.append(group["note"])
        lines.append("")
        lines.append("| Pin | Function | x (mm) | y (mm) |")
        lines.append("|---|---|---|---|")
        for pin, function in group["pins"]:
            if pin not in host["pads"]:
                continue
            x, y = host["pads"][pin]
            lines.append("| %s | %s | %.2f | %.2f |" % (pin, function, x, y))
        lines.append("")
        if group.get("pin_distances"):
            lines.append("| From | To | Distance |")
            lines.append("|---|---|---|")
            for pin_a, pin_b, label in group["pin_distances"]:
                if pin_a in host["pads"] and pin_b in host["pads"]:
                    lines.append("| %s | | %.2f mm |"
                                 % (label,
                                    distance(host["pads"][pin_a],
                                             host["pads"][pin_b])))
            lines.append("")

    return "\n".join(lines) + "\n"


def _aggregate_passives(members):
    """Collapse passive values into value -> (count, min_x, max_x)."""
    aggregated = {}
    for footprint in members:
        if not PASSIVE_VALUE.match(footprint["value"]):
            continue
        count, low, high = aggregated.get(
            footprint["value"], (0, footprint["x"], footprint["x"]))
        aggregated[footprint["value"]] = (count + 1,
                                          min(low, footprint["x"]),
                                          max(high, footprint["x"]))
    return aggregated


def generate(pcb_path, output_path, zone_bounds, distance_pairs, pin_groups):
    footprints = read_footprints(pcb_path)
    document = format_register(footprints, zone_bounds, distance_pairs,
                               pin_groups, Path(pcb_path).name)
    Path(output_path).write_text(document)
    print("wrote %s (%d footprints)" % (output_path, len(footprints)))


# Configuration -------------------------------------------------------------
# Zone boundaries are upper x limits along the board's long axis, in order.
# The floor plan is [ANALOG FRONT END] - [MCU] - [POWER]; see layout-notes.md §1.

pcb_path = ("/Users/andy/Dropbox/Developer/AudioDev/Onboard DSP Board HW/"
            "Main Board/Main Board.kicad_pcb")
output_path = ("/Users/andy/Dropbox/Developer/AudioDev/Onboard DSP Board HW/"
               "placement-register.md")

zone_bounds = [
    ("Analog front end", 137.0),
    ("MCU", 158.0),
    ("Power / charger", 1e9),
]

distance_pairs = [
    ("MCU", "nearer ADC codec", "STM32H725RGVx", "XLV320ADC5140IRTWR"),
    ("MCU", "core SMPS inductor", "STM32H725RGVx", "2.2uH"),
    ("MCU", "buck-boost", "STM32H725RGVx", "TPS63020DSJR"),
    ("MCU", "charger", "STM32H725RGVx", "TP4054"),
    ("Buck-boost", "nearer ADC codec", "TPS63020DSJR", "XLV320ADC5140IRTWR"),
    ("Buck-boost inductor", "nearer ADC codec", "1.5uH", "XLV320ADC5140IRTWR"),
    ("Analog LDO", "nearer ADC codec", "TPS7A2033PDBVR", "XLV320ADC5140IRTWR"),
    ("Analog LDO", "DAC", "TPS7A2033PDBVR", "PCM5102"),
    ("HSE crystal", "MCU", "24.576", "STM32H725RGVx"),
    ("HSE crystal", "core SMPS inductor", "24.576", "2.2uH"),
    ("HSE crystal", "its load caps", "24.576", "15pF"),
]

# The HSE pair and the core-SMPS hot loop share one package edge; this table
# exists so that adjacency stays visible in the record rather than being
# rediscovered from the PCB each time.
pin_groups = [
    {
        "title": "MCU east face — core SMPS and HSE share an edge",
        "part_value": "STM32H725RGVx",
        "note": ("ST placed the core-SMPS hot loop (pads 4–7) and the HSE "
                 "crystal pair (pads 10–11) on the same package edge, two pads "
                 "apart. The HSE oscillator therefore sits within a few mm of "
                 "the buck switch node no matter how it is placed — this is a "
                 "pinout constraint, not a layout choice."),
        "pins": [
            ("4", "VSSSMPS"),
            ("5", "VLXSMPS — switch node"),
            ("6", "VDDSMPS"),
            ("7", "VFBSMPS"),
            ("10", "PH0 / HSE_IN"),
            ("11", "PH1 / HSE_OUT"),
        ],
        "pin_distances": [
            ("5", "10", "VLXSMPS (switch node) → HSE_IN"),
            ("7", "10", "VFBSMPS → HSE_IN"),
            ("10", "11", "HSE pair pitch"),
        ],
    },
]

generate(pcb_path, output_path, zone_bounds, distance_pairs, pin_groups)
