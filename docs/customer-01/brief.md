# CUST-001 – Nordwerk Industrie-Service: release candidate (Session 4)

Source: Nordwerk client brief v1.0 (23 October 2026), `task sheets/session-03-05/Client_Brief_Nordwerk_en.md` (DE: `Kundenbriefing_Nordwerk_de.md`).
Previous delivery of CUST-001: Session 3 ( run `ec76867e`, brief version in Factory commit `3d18a68`).
Fictional company. Static website, a single page with anchors. Website language: German.
Accountable Product Owner: Francisco.

## Task for Session 4

The start page becomes a complete release candidate: all required content N-01 to N-09 and acceptance criteria AC-01 to AC-08.
Content delivered in Session 3 stays exactly as it is.

User stories cover exactly these four content blocks (agent task):

1. Header and navigation (AC-01, AC-05): company name, main statement and navigation to Leistungen, Zielgruppen, Arbeitsweise and Kontakt.
2. Services (AC-02): all three services N-03, N-04 and N-05 with their required text.
3. Target groups and working approach (AC-03): N-06 and N-07.
4. Contact and course notice (AC-04): N-08 and N-09, unchanged from Session 3.

AC-06 to AC-08 (layout/CSS, keyboard focus, start command, product tests) are done by the team; they are not part of the agent task.

## Required content (German, copy verbatim, character by character)
- N-01 Company name: Nordwerk Industrie-Service
- N-02 Main statement: Praktische Unterstützung für Ihren technischen Betrieb.
- N-03 Service "Wartungsplanung": Wir strukturieren Wartungsaufgaben und dokumentieren Zuständigkeiten für kleine technische Betriebe.
- N-04 Service "Ersatzteilkoordination": Wir unterstützen bei der Abstimmung von Ersatzteilbedarfen und Lieferterminen.
- N-05 Service "Betriebsdokumentation": Wir bringen technische Unterlagen in eine nachvollziehbare und nutzbare Struktur.
- N-06 Target groups, two separate entries:
  - Kleine Produktionsbetriebe
  - Technische Serviceunternehmen
- N-07 Working approach: Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang und nachvollziehbare Ergebnisse.
- N-08 Contact: link text "Anfrage stellen", target mailto:kontakt@nordwerk.example
- N-09 Course notice: Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. Keine realen Angebote oder Kontaktaufnahme.

Do not shorten, rephrase, translate or put quotation marks around the required texts.
The dash in N-09 is an en dash (–), not a hyphen.
`kontakt@nordwerk.example` is a placeholder; no message is sent.

## Acceptance criteria AC-01 to AC-08 (wording from the client brief)

| ID | Criterion | Implemented by | Evidence |
|---|---|---|---|
| AC-01 | Company name and main statement are easy to find on the initial view. | Agent: slot `header` | Product check required content, browser review |
| AC-02 | All three services and their descriptions are identifiable. | Agent: slot `services` | Product check required content |
| AC-03 | Both target groups and the working approach are included; no invented promises. | Agent: slots `audiences`, `approach` | Product check required content, human gate |
| AC-04 | Clearly labelled contact link targets `mailto:kontakt@nordwerk.example`; the course notice is visible. | Agent: slots `contact`, `footer` | Product check contact/navigation, product check required content |
| AC-05 | Navigation reaches services and contact; internal links and local assets work. | Agent: slot `nav`; team: section IDs | Product check contact/navigation, product check local links/assets |
| AC-06 | At widths of 375 px and 1280 px there is no horizontal content overflow; text and contact remain usable. | Team: CSS | Browser review at 375/1280 px with reviewer name |
| AC-07 | Document title, German language metadata, meaningful headings and visible keyboard focus; appropriate alternative text if images exist. | Team: page skeleton, CSS | Product check language/title, browser review keyboard/focus |
| AC-08 | A fresh product checkout starts with a documented command without the Factory, LLM or Factory database; product tests run separately. | Team: README | Start record from a fresh checkout |

## Markup contract Factory ↔ product (`site/index.html`)

The agent only delivers the content of the slots. The page skeleton, `<nav>`, `<section id="...">`, `<h2>` headings and CSS are maintained by the team outside the slots.

| Slot | Location | Markup |
|---|---|---|
| `header` | `<header>` | `<h1>`N-01`</h1><p class="claim">`N-02`</p>` |
| `nav` | `<header>`, after the `header` slot, inside the team's `<nav aria-label="Hauptnavigation">` | `<ul><li><a href="#leistungen">Leistungen</a></li><li><a href="#zielgruppen">Zielgruppen</a></li><li><a href="#arbeitsweise">Arbeitsweise</a></li><li><a href="#kontakt">Kontakt</a></li></ul>` |
| `services` | `<section id="leistungen">` | one `<article class="service"><h3>`NAME`</h3><p>`TEXT`</p></article>` per service, order N-03, N-04, N-05 |
| `audiences` | `<section id="zielgruppen">` with `<h2>Zielgruppen</h2>` | `<ul><li>Kleine Produktionsbetriebe</li><li>Technische Serviceunternehmen</li></ul>` |
| `approach` | `<section id="arbeitsweise">` with `<h2>Arbeitsweise</h2>` | `<p>`N-07`</p>` |
| `contact` | `<section id="kontakt">` | `<p>Bei Fragen können Sie uns gerne kontaktieren.</p><a class="contact-link" href="mailto:kontakt@nordwerk.example">Anfrage stellen</a>` |
| `footer` | `<footer>` | `<p class="notice">`N-09`</p>` |

Section order in `<main>`: `leistungen`, `zielgruppen`, `arbeitsweise`, `kontakt`.

Rules for the agent:

- Change only the slots that need new content; leave all other slots as they are. Content from Session 3 stays unchanged.
- All visible website text is German; do not translate anything into English.
- Exactly one `<h1>` (in the `header` slot); `<h3>` only for the three service names; no `<h2>` inside slots.
- Only the classes `claim`, `service`, `contact-link`, `notice`.
- Link targets only `#leistungen`, `#zielgruppen`, `#arbeitsweise`, `#kontakt` and `mailto:kontakt@nordwerk.example`.
- No `<script>`, no inline styles, no event handlers, no images, no external URLs.
- No additional services, target groups, numbers, promises or response times.

## Markup notes from the client contract (team)

- A single page with anchors is sufficient. Pre-approved: HTML/CSS, a little JavaScript, a simple local web server. No PHP, no CMS, no form.
- `<html lang="de">`, a meaningful `<title>`, heading order h1 → h2 per section → h3 per service.
- Visible keyboard focus on all links (`:focus-visible`); do not remove focus outlines.
- A logo is optional and images are not needed; if images are used, they need appropriate alternative text. Local assets only, no external fonts, scripts or tracking.
- No horizontal overflow at 375 px and 1280 px; the contact link stays usable.
- Layout and headings may supplement the required content without changing its factual meaning. No invented customer logos, certifications, references, response times or success statistics.
- No payment, accounts, analytics, real personal data or public deployment.

## Team assumptions (not customer copy)

- The headings and navigation labels "Leistungen", "Zielgruppen", "Arbeitsweise" and "Kontakt" are layout additions; the client brief allows supplementary headings.
- The sentence in the contact section comes from Session 3, was approved in the CUST-001 human gate, contains no promise and stays unchanged.

## Not part of Session 4

- Change CR-01, security request SR-01 and customer acceptance (Session 5).
- Any services other than N-03 to N-05.