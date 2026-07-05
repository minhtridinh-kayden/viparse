"""Vietnamese character-frequency model for content-based encoding detection.

A wrong legacy-encoding guess produces text full of characters that never occur in
Vietnamese; a right guess produces ordinary Vietnamese. Scoring a trial conversion by
the average log-probability of its characters under a Vietnamese model thus tells the
two apart — even breaking ties between legacy tables that both yield *some* Vietnamese
letters, and catching text that is only sparsely legacy (SPEC-3 T3.2.1 / T3.2.3).

A **unigram** model is used deliberately: it is well-estimated from a modest corpus,
whereas a bigram model over Vietnamese's large character set is too sparse to be
reliable at this corpus size. The model is derived at import from an embedded sample of
clean NFC Vietnamese prose (public-domain Wikipedia text); the exact wording does not
matter, only the character distribution, so minor corpus edits are harmless.
"""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from functools import cache

# ~1.5k characters of running Vietnamese prose (NFC). Statistical use only.
_CORPUS = (
    "Tiếng Việt hay tiếng Kinh là một ngôn ngữ thuộc ngữ hệ Nam Á, được công nhận là "
    "ngôn ngữ chính thức tại Việt Nam. Đây là tiếng mẹ đẻ của khoảng 85% dân cư Việt Nam "
    "và một bộ phận đáng kể 5 triệu Việt kiều ở ngoại quốc, đồng thời là ngôn ngữ thứ hai "
    "của các dân tộc thiểu số tại Việt Nam. Trên thế giới, tiếng Việt được công nhận là "
    "một trong những ngôn ngữ chính thức của Thành phố San Francisco tại Hoa Kỳ, và là "
    "ngôn ngữ chính thức của một dân tộc thiểu số được công nhận tại Séc và Slovakia. "
    "Dựa trên vốn từ vựng cơ bản, tiếng Việt đã được giới ngôn ngữ học phân loại là một "
    "ngôn ngữ Nam Á, có quan hệ di truyền với những ngôn ngữ như Mường, Khmer, Môn. Đây "
    "cũng là ngôn ngữ Nam Á được sử dụng bởi nhiều người nhất, hơn hẳn tổng số người nói "
    "tất cả các ngôn ngữ khác cùng trong ngữ hệ cộng lại."
)


@cache
def _model() -> tuple[dict[str, float], float]:
    """The (per-character log-probability, floor) unigram model, built once."""
    counts = Counter(unicodedata.normalize("NFC", _CORPUS).lower())
    total = sum(counts.values())
    vocab = len(counts)
    # Add-one smoothing; the floor (for characters absent from the corpus) heavily
    # penalizes the foreign glyphs a wrong decoding leaves behind.
    floor = math.log(1 / (total + vocab))
    logp = {ch: math.log((n + 1) / (total + vocab)) for ch, n in counts.items()}
    return logp, floor


def vietnamese_score(text: str) -> float:
    """Mean per-character log-probability of ``text`` under the Vietnamese model.

    Higher (closer to zero) is more Vietnamese-like. Empty text scores the floor.
    """
    logp, floor = _model()
    normalized = unicodedata.normalize("NFC", text).lower()
    if not normalized:
        return floor
    return sum(logp.get(ch, floor) for ch in normalized) / len(normalized)
