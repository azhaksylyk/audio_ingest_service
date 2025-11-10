from typing import Tuple
def parse_content_range(h: str) -> Tuple[int,int,int]:
    if not h.startswith("bytes "):
        raise ValueError("invalid")
    rng, total = h[6:].split("/")
    s, e = rng.split("-")
    return int(s), int(e), int(total)