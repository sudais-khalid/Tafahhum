# OCR

## The source in hand

`Nayl us Sayireen fi Tabaqat al-Mufassireen.pdf` — 570 pages, 43.8 MB.

Surveyed before any processing (`python scripts/ingest_nayl.py --survey`):

| Property | Value |
|---|---|
| Text layer | none — 0 characters across a 40-page sample |
| Median native resolution | **67 DPI** |
| Language | **Urdu**, not Arabic |
| Script | **Nastaliq**, lithographed/calligraphic |
| Embedded quotations | Arabic, in Naskh |
| Producer | PDFsharp, re-processed through ilovepdf |
| Watermark | a library site stamp on every page |

Two of those matter more than the rest. The work is in **Urdu**, so it is a
ṭabaqāt work *about* the Mufassirūn written for Urdu readers, not an Arabic
primary text. And it is set in **Nastaliq**, which is the hardest widely-used
script for OCR: cursive, with heavy ligature overlap, context-dependent letter
forms, and a baseline that slopes within each word.

At 67 DPI, even Naskh would be marginal.

## Measured Tesseract performance

Tesseract 5.5.2 with `tessdata_best` `urd+ara`, page rendered at 400 DPI (which
adds pixels, not information — the underlying scan is still 67 DPI).

Ground truth for page 31, read directly from the image:

> فصل / فضیلت تابعین
> ابن ابی حاتم لکھتے ہیں :
> صحابہ کرام رضوان اللہ علیھم اجمعین کے بعد تابعین حضرات نے، جنہیں اللہ تعالیٰ …

Tesseract output:

> فص
> ان الی عاتم یت یں :
> صوکراممر ضوان ارڈر مم مین کے بعد نین نطرات نے میس ابد نکی …

Observations:

- The section heading **فضیلت تابعین** was dropped entirely.
- `ابن ابی حاتم` → `ان الی عاتم`. A named authority, unrecoverable.
- `صحابہ کرام` → `صوکراممر`. Merged and mangled.
- Function words survive: `کے بعد`, `نے`, `اور`, `کی`.

Word accuracy is roughly **20–35%**, and the errors are not randomly
distributed — **function words survive and proper names do not.** For a ṭabaqāt
work, whose entire value is names, generations, and dates, that inverts what the
extraction is for.

Tesseract's own reported confidence corroborates this independently: mean
per-word confidence across the sampled pages is **0.52–0.59**, far below any
threshold at which output would be worth reviewing rather than re-doing.

```
p  29   1330 chars  conf=0.52
p  30   1365 chars  conf=0.59
p  31   1120 chars  conf=0.57
p  32    521 chars  conf=0.54
p  33   1047 chars  conf=0.52
p  34   1301 chars  conf=0.53
```

## Why a vision model is the right engine here

Conventional OCR segments glyphs and classifies them. Nastaliq resists that: the
segmentation step has no reliable boundaries to find. A vision-language model
reads words in context instead, which is why it handles Nastaliq, degraded
scans, and mixed Urdu/Arabic pages that Tesseract cannot.

`VisionOcrEngine` implements the same `OcrEngine` protocol, so switching engines
changes one flag and nothing else:

```bash
python scripts/ingest_nayl.py --ocr --engine vision --batch
```

It needs Anthropic credentials (`ant auth login`, or `ANTHROPIC_API_KEY`).

### Batching

570 pages is not latency-sensitive, so the vision path uses the Batches API:
half the standard price, up to 100,000 requests per batch, and results retained
for 29 days. The script submits every pending page as one batch, polls, and
stores results keyed by `custom_id` — which is the `scan_page` id, so results
can arrive in any order without being mismatched.

### The transcription prompt

The system prompt is written to make the model a transcriber rather than a
reader. Its load-bearing instructions:

- reproduce verbatim; do not translate, modernise, correct, or complete
- keep Urdu in Urdu and Arabic quotations in Arabic
- write `[؟]` for anything unreadable — **never guess a plausible word**
- do not transcribe watermarks or added URLs

The gap marker is the important one. A wrong name is worse than a visible hole:
a hole is a research task, a wrong name is a fabricated attestation that looks
exactly like a real one.

## Nothing here is citable yet

Every page lands in `MACHINE_PROPOSED` with `needs_review = true`. The
`/api/v1/biblio` endpoint reports `citable: false` until pages carry
`ocr_verified_text`, written by a named human reviewer.

```
Nayl al-Sairin fi Tabaqat al-Mufassirin
  pages=570  ocr=6  verified=0  citable=false  mean_conf=0.547
```

`test_nothing_from_this_source_is_citable_yet` fails if that gate is ever
crossed without review. Machine transcription is a proposal about what a page
says, not evidence of what it says.

## Text representations

`scan_page` carries the same three representations as `passage`:

| Column | Meaning | Mutable |
|---|---|---|
| `ocr_raw_text` | exactly what the engine produced | never, once non-empty |
| `ocr_normalized_text` | matching form, feeds the FTS index | derived |
| `ocr_verified_text` | human-approved reading | reviewer only |

The immutability trigger deliberately treats an **empty** result as "not yet
read" rather than as a reading. An earlier version froze pages on an empty
string, which permanently locked out a better engine — migration `009` fixed
that, and `test_empty_ocr_does_not_lock_a_page` pins the behaviour.

## Recommended path for this source

1. **A better scan is worth more than a better engine.** A 300 DPI capture would
   improve every downstream step, including the vision model's accuracy.
2. Failing that, run `--engine vision --batch` over all 570 pages.
3. Review the fihrist and the ṭabaqāt entry pages first. Those carry the names,
   generations, and page references that populate `mufassir_attestation`, and
   they are the reason to read this book at all.
4. Only then draft scholarly rules from it, each anchored to a volume and page,
   for human approval. See `SOURCE_POLICY.md` §6.

## Cost shape

Page images are ~1,100–1,600 tokens each at the rendered size, plus output.
For 570 pages, expect on the order of 1M input tokens and 0.5M output tokens.
At Claude Opus 5 batch rates (50% of $5/$25 per MTok) that is roughly **$9**.
Measure before committing: `client.messages.count_tokens` on a single page gives
an exact per-page figure to multiply.
