---
noteId: "4dbf51f2d3a311f18d5e8305d12a06ac"
tags: []
name: "li-profile"
description: "Score a LinkedIn profile out of 100 against a 12-part rubric and rewrite the parts that lose points - headline, about, experience, featured, banner. Use when the user says \"optimize my profile\", \"score my LinkedIn\", \"rewrite my headline\", \"fix my about section\", or pastes their profile and asks how it reads. Bilingual: understands French requests (\"écris un post LinkedIn\") and returns every copy-ready text in both French and English."

---

# li-profile

A profile is not a resume. A resume answers "what have you done". A profile
answers "should I message this person", and it answers it in about four
seconds, from the headline and the first two lines of the about.

## Input

Ask the user to paste: headline, about section, current role and the last two
experience entries, plus whether they have a banner and featured section. A
screenshot of the top card is enough for the first pass. Do not log into
LinkedIn on their behalf.

## Score it

Read `rubric.json` in this folder. Twelve items, 100 points, each with what
full marks looks like. Score every item, show the table, and give the total.
Be honest - most profiles land in the 30s and 40s on the first pass, and a
generous score is useless.

```
PROFILE SCORE  41/100

  headline            3/12   job title only, no outcome, no audience
  about first 2 lines 2/10   opens with "passionate about"
  about body          4/10   history, not offer
  featured            0/8    empty
  banner              0/6    default blue
  ...
```

## Then rewrite, in this order

Fix in descending order of points lost. Do not rewrite everything at once -
the user has to actually paste each of these in.

**1. Headline (220 characters).** The formula that works:
`{what you do for whom} | {proof} | {how to start}`. Not your job title. Not
"Helping X do Y" as the first three words, which every second profile now
opens with. Give three options.

**2. About, first two lines.** Everything after line 2 is behind "see more" on
mobile, so those two lines are the whole about section for most readers. They
must state who you help and what changes. No "passionate", no "results-driven",
no third-person bio, no opening with your own name.

**3. About body.** Written to one reader, in the second person. Structure:
the problem they have, what you do about it, one piece of proof with a number,
what to do next. Under 1,400 characters even though the limit is 2,600.

**4. Featured.** Three items: the best post, the proof asset, the way to
contact. An empty featured section is eight points and the only place on the
profile you fully control.

**5. Experience.** Each role gets one line of scope and two to three bullets
that are outcomes with numbers, not duties. Cut anything older than ten years
to a single line.

**6. Banner.** One sentence of positioning and one way to reach you. The
default blue gradient is the clearest signal on the page that nobody is home.

## Output

Score table, then the rewrites as copy-ready blocks in fix-first order, each
one already run through `/li-human`. Re-score at the end and show the delta
honestly - if the rewrite gets to 88 and not 98, say 88, and say what the
remaining points need (usually recommendations, a real banner and posting
history, none of which a rewrite can create).

Nothing is saved to LinkedIn by this skill. The user pastes each section in.

## Bilingual output (FR <-> EN)

Every copy-ready text this skill produces ships in **both French and English**.

- Write first in the language the user wrote in (or the language of the source
  text). Then give the other language as a **second, separate copy-ready
  block**. Label them `FR` and `EN`.
- Adapt, do not translate word for word. Keep the same facts, numbers and
  structure, but use the idioms, hook rhythm and register that sound native in
  each language. A literal translation reads as machine text in both.
- Humanize each version on its own. `humanize.py` and `detect.py` detect the
  language and use `slop.fr.json` for French (`--lang fr` to force it). Report
  both scores.
- Keep every `{{your number}}` placeholder and flag in both versions. Never
  add a fact to one language that the other does not have.
- French typography: a space before `? ! : ;`, and vouvoiement unless
  `voice.md` says tu.
- Analysis, tables and explanations stay in the user's language only. Only
  the text meant to be pasted is doubled.
- If the user says "FR only", "EN only" or "seulement en français", drop the
  other version for the rest of the conversation.
- LinkedIn supports a secondary-language profile, so give every rewrite in
  both languages, ready to paste into each. Check the 220-character headline
  limit for each language separately.
