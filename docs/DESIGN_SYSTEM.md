# Design System

## Direction

Warm paper, iron-gall ink, and one restrained accent. The register is a scholarly
reading environment, not a consumer app: generous spacing, hairline rules, no
gradients, no shadows beyond a focus ring.

## The colour law

**Gold belongs to Quranic text and to nothing else.**

Commentary, interface, and synthesis never borrow it. A reader can tell revealed
text from interpretation before reading a label, which makes the "never silently
combine evidence kinds" requirement a visual property rather than a convention.

```
--paper       #FBF9F5   unbleached paper
--paper-sunk  #F4F0E8   recessed surfaces
--ink         #1F1B16   warm near-black
--ink-muted   #6B6155
--rule        #E4DED2   hairlines
--accent      #2F5D62   deep teal, interactive and resolved states
--gold        #A88B4A   Quranic text only
--warn        #8A6D3B   disclosure notices
```

Teal rather than the expected terracotta: terracotta on cream is the default
these interfaces drift toward, and it carries no meaning here.

## Type

| Role | Face | Why |
|---|---|---|
| Source Arabic | Amiri | A Naskh revival drawn from the Bulaq press types, the typographic tradition printed Tafsir actually belongs to |
| Urdu | Noto Nastaliq Urdu | The script Urdu readers expect; Naskh is legible but reads as foreign |
| Latin prose | Spectral | A serif designed for screen reading, scholarly without being decorative |
| Citations and metadata | IBM Plex Mono | A citation is a verifiable field, not prose, and should read as data |
| Interface labels | IBM Plex Sans | Quiet, gets out of the way |

Arabic passages are set at 1.22rem with line-height 2.1; Quranic text larger
still. Arabic needs more leading than Latin, and cramped Arabic is the most
common typographic failure in products like this.

## Signature: the provenance ladder

Every passage carries a five-stage meter:

```
Work ─── Edition ─── Volume ─── Page ─── Scan
 ●────────●─────────○────────○────────○
```

Filled means the citation resolves that far; hollow means that link does not
exist yet. It encodes the provenance chain structurally and puts the corpus's
current limitation on every card, where a reader skimming cannot miss it.

This is the one place boldness is spent. Everything else stays quiet.

## RTL

Direction is set on `<html>` from the interface language, so layout follows from
one property rather than being re-implemented per component. Logical properties
(`margin-inline-start`, `padding-inline`, `border-inline-start`) throughout.

Arabic passages are always `dir="rtl"` regardless of interface language, because
the text is Arabic whatever the chrome is.

## Quality floor

Responsive to mobile; the ladder drops its labels below 620px and keeps its dots.
Visible keyboard focus via `:focus-visible`. `prefers-reduced-motion` respected.
Motion is limited to a single rise-in on results and a spinner during search.
