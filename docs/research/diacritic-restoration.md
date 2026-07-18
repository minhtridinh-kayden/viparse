# Research spike: Vietnamese diacritic restoration (VIP-73)

> SPEC-3 lists diacritic restoration as **v2 (optional)**. This is the timeboxed spike that
> decides whether viparse should build it. **No production code ships from this spike.**

## The question

Restore *missing* Vietnamese diacritics — `"Tieng Viet"` → `"Tiếng Việt"` — for sources where
the accents were stripped (SMS-style text, broken exports, ASCII-only systems). This is **not**
a legacy-encoding problem (that is the existing, deterministic moat); the information was
*lost*, so restoration must *guess* it back.

## Why this is categorically different from the moat

The moat (TCVN3/VNI/VISCII/VPS → Unicode) is **deterministic and lossless**: each legacy byte
maps to exactly one Unicode letter, reversibly. Diacritic restoration is **probabilistic and
lossy**: one accentless syllable can be many valid Vietnamese words, and the correct one depends
on sentence context. It structurally conflicts with the project's cardinal rule — *never corrupt
good text*.

## Evidence — ambiguity is severe (measured, not assumed)

Prototype over a real 39k-entry Vietnamese wordlist (`duyet/vietnamese-wordlist`), with usage
frequencies from `wordfreq`:

| Metric | Value |
|---|---|
| Unique syllables | 6,633 |
| Unique accentless (bare) keys | 1,556 |
| **Bare keys that are ambiguous (>1 accented form)** | **1,244 — 79.9% of types** |
| Worst offenders | `do`→29 forms, `doi`/`dam`/`dan`→25, `day`→21 |
| **Frequency-weighted ceiling of a context-free "always most-frequent form" dictionary** | **≈ 72.7% per-token** (≈ 1 in 4 tokens wrong) |

High-frequency syllables are among the *most* ambiguous, and disambiguation is genuinely
context-dependent:

```
co    -> có / cơ / cô / cổ / cố …
toi   -> tôi / tới / tối / tội …
duong -> đường / dương / đương / dưỡng …
nam   -> năm / nam / nằm / nắm …
```

Context-free restorer on real sentences (errors in **bold**):

```
nam nay toi hai muoi lam tuoi   ->  năm **này** tôi hai **mười** **làm** tuổi
                                     (correct: năm nay … hai mươi lăm tuổi)  — 3 wrong in 6 words
```

## The safety problem is worse than the accuracy problem

Even a 99%-accurate model (the literature's best, see below) still rewrites 1% of tokens — and
the *harder, unsolved* half is deciding **which text to touch at all**. The restorer must never
alter (a) text that already has diacritics, or (b) non-Vietnamese text (English, code, IDs,
proper nouns). A naive restorer fails both catastrophically:

```
"Tiếng Việt"     (already correct) ->  "tiếng việt"      # good text mangled
"the can is on"  (English)         ->  "thể cần is ổn"   # non-Vietnamese destroyed
```

Any accentless Latin string *looks like* accentless Vietnamese. Reliable input-gating is a
research problem in itself; getting it wrong corrupts input viparse currently handles perfectly.

## Approaches surveyed

| Approach | Reported accuracy | Dependencies / size | Offline | Fit for viparse |
|---|---|---|---|---|
| **Context-free dictionary** (most-frequent form) | ~73% (measured here) | tiny wordlist, stdlib | ✅ | ❌ far too inaccurate |
| **N-gram / pointwise (CRF/SVM)** ([pointwise ~94.7%](https://www.academia.edu/10584474/A_Pointwise_Approach_for_Vietnamese_Diacritics_Restoration)) | ~90–95% | n-gram tables (tens–hundreds of MB) + a classifier | ✅ | ⚠️ moderate size, still ~1-in-20 wrong |
| **Seq2seq / MT / char-LSTM** ([MT approach](https://arxiv.org/pdf/1709.07104)) | ~97% | trained model weights | ✅ (bundled model) | ⚠️ custom model to train + host |
| **Transformer (fine-tuned)** ([deep-learning](https://www.semanticscholar.org/paper/Vietnamese-Diacritics-Restoration-Using-Deep-Hung/b726244caff59dcb9cbd4814b8827fc8e5d0b0a3)) | ~98–99% | `torch`/`transformers`, hundreds of MB | ✅ but heavy | ❌ huge dep + supply-chain surface |

The accuracy needed to be *safe by default* (≥99%) only comes from heavy ML; the light,
offline, dependency-free options viparse prefers cap around 73–95%.

## Safety contract — required IF this is ever built

Non-negotiable design constraints, mirroring why content-detection is opt-in:

1. **Strictly opt-in** — a `restore_diacritics=True` flag, never a default.
2. **Extras-gated & lazy-imported** — any model/data behind `viparse[restore]`; `core` stays
   stdlib-only.
3. **Never touch already-diacritized text** — if a span contains *any* Vietnamese diacritic, or
   NFC composition shows tone/vowel marks, leave it untouched.
4. **Vietnamese-only gating** — only restore spans a language/character model scores as
   confidently accentless-Vietnamese; leave English/code/mixed spans alone.
5. **Per-token confidence threshold** — restore a token only above a high threshold; emit the
   original token unchanged otherwise (prefer a *miss* over a wrong guess).
6. **Declared best-effort** — `metadata.warnings` records that diacritics were restored and the
   output may contain errors; the restored text is never presented as authoritative.

Even with all six, the guarantee weakens from *"never corrupts good text"* to *"rarely corrupts,
opt-in only"* — a real erosion of the brand.

## Recommendation: **NO-GO for now (defer)**

1. **Wrong character for the moat.** viparse's value is *deterministic, lossless* normalization.
   Diacritic restoration is *probabilistic, lossy* — a different product bolted onto the brand
   promise.
2. **The cheap version is unsafe** (~73%), and the safe version is heavy (transformer + `torch`,
   hundreds of MB, large supply-chain surface) — contradicting "heavy engines are lazy / core is
   light" and adding real CVE/maintenance exposure.
3. **The input-gating problem is unsolved** and, done wrong, corrupts non-Vietnamese and
   already-correct text — the one thing viparse must never do.
4. **Better ROI elsewhere.** More deterministic wins (additional legacy encodings, more formats:
   `.rtf`/`.pptx`/images) extend the moat without risking it.

**If the user still wants it**, ship it as a **separate, clearly-labelled optional package**
(e.g. `viparse-restore` or a `viparse[restore]` extra) implementing the full safety contract
above — never wired into the default `load()` path.

## Follow-up breakdown (only if a GO is chosen)

1. **Epic: opt-in diacritic restoration (`viparse[restore]`).**
   - T: input-gating detector — classify a span as accentless-Vietnamese vs already-correct vs
     non-Vietnamese (this is the hard, safety-critical part; build & measure first).
   - T: restoration model — start with n-gram/pointwise (offline, no `torch`); measure P/R.
   - T: `restore_diacritics` option + `metadata` "best-effort" flag; lazy import behind the extra.
   - T: golden corpus incl. **negative** cases (English, code, already-correct) that must pass
     through byte-identical.
   - T: docs + prominent accuracy/limitations disclaimer.

## Artifacts

Throwaway prototype and data (scratchpad, not committed): `vip73_ambiguity.py`, `viet39k.txt`,
`wordfreq` venv. Re-runnable to reproduce every number above.
