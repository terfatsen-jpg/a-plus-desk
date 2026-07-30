import json
import re
import sys
from pathlib import Path

from fetch_real import build_snapshot

HERE = Path(__file__).parent
DESK_HTML = HERE / "index.html"


def obj_line(o, indent="    "):
    parts = []
    for k, v in o.items():
        if isinstance(v, str):
            parts.append(f'"{k}": "{v}"')
        elif v is None:
            parts.append(f'"{k}": null')
        else:
            parts.append(f'"{k}": {json.dumps(v)}')
    return indent + "{ " + ", ".join(parts) + " },"


def render_block(snapshot):
    lines = ["  var REAL_SNAPSHOT = {"]
    lines.append(f'  "fetched_utc": "{snapshot["fetched_utc"]}",')
    lines.append('  "watchlist": [')
    wl = [obj_line(x) for x in snapshot["watchlist"]]
    wl[-1] = wl[-1].rstrip(",")
    lines.extend(wl)
    lines.append("  ],")
    lines.append('  "indices": [')
    idx = [obj_line(x) for x in snapshot["indices"]]
    idx[-1] = idx[-1].rstrip(",")
    lines.extend(idx)
    lines.append("  ]")
    lines.append("  };")
    return "\n".join(lines)


def main():
    snapshot = build_snapshot()

    errors = [x for x in snapshot["watchlist"] if "error" in x] + [x for x in snapshot["indices"] if "error" in x]
    if errors:
        print("WARNING: some symbols failed to fetch:", errors, file=sys.stderr)

    html = DESK_HTML.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(// SNAPSHOT_START.*?\n)(.*?)(\n  // SNAPSHOT_END)",
        re.DOTALL,
    )
    if not pattern.search(html):
        print("ERROR: SNAPSHOT_START/SNAPSHOT_END markers not found in index.html", file=sys.stderr)
        sys.exit(1)

    new_block = render_block(snapshot)
    html = pattern.sub(lambda m: m.group(1) + new_block + m.group(3), html, count=1)
    DESK_HTML.write_text(html, encoding="utf-8")
    print(f"Updated {DESK_HTML} with snapshot fetched at {snapshot['fetched_utc']}")


if __name__ == "__main__":
    main()
