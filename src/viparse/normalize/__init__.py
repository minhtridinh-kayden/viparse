"""The Vietnamese normalization layer (the moat).

Detects a legacy encoding (TCVN3, VNI, …) from extraction signals, converts the
text to Unicode via a static :class:`~viparse.normalize.tables.Charmap`, and
enforces NFC. This package holds the conversion framework and the per-encoding
tables; the encoding detector and the concrete Normalizer build on it.
"""
