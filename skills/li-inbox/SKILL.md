---
noteId: "4dbf51f1d3a311f18d5e8305d12a06ac"
tags: []
name: "li-inbox"
description: "Triage the LinkedIn inbox - sort connection requests and DMs into leads, recruiters, peers and spam, and draft the replies worth sending. Use when the user says \"my inbox is a mess\", \"triage my DMs\", \"should I reply to this\", pastes a batch of LinkedIn messages, or is drowning in connection requests. Bilingual: understands French requests (\"écris un post LinkedIn\") and returns every copy-ready text in both French and English."

---

# li-inbox

Most LinkedIn inboxes are 80% noise, and the cost of that noise is that the
20% goes unanswered for a week. This skill separates them, then writes only
what is worth writing.

## Input

The user pastes the messages. Screenshots are fine. Do not log into their
account or read their inbox with a browser tool.

## Sort into five

| bucket | signal | action |
| --- | --- | --- |
| **LEAD** | describes a problem the user solves, or asks about working together | reply today, full answer |
| **RECRUITER** | a role, a company, a salary band | reply if the role is real, one line if not |
| **PEER** | someone in the same field with something to say | reply this week, keep it human |
| **ASK** | wants advice, time, an intro, a favour | reply if it is cheap and specific, decline cleanly if not |
| **SPAM** | agency pitch, lead-gen sequence, crypto, "quick question" with no question | archive, no reply |

Print the counts first. Seeing "3 leads, 2 recruiters, 41 spam" is most of the
value.

## Detecting a sequence

Automated outreach has a shape: an invite note with no specifics, a message
that arrives within minutes of the accept, "quick question", "I noticed you're
in {industry}", a calendar link in message one, then a bump exactly four days
later. When you see it, mark it SPAM and say which tell gave it away. The user
does not owe a reply to a script.

## Replies

- **LEAD** - answer the actual question in the message, in full, for free. If
  it is a fit, the offer is one sentence at the end. If it is not, say so and
  point them somewhere useful. Both outcomes are good.
- **RECRUITER** - if the role is genuinely interesting, ask the three things
  the message left out: comp band, level, and whether it is in-office. If it
  is not, one line: not looking, happy to refer, and mean the refer.
- **ASK** - if it costs under ten minutes and is specific, do it. If it is
  "can I pick your brain", decline in one warm sentence and give them the one
  answer you would have given on the call. That is the polite version and it
  is also the more useful one.
- **DECLINES** are short, warm and final. No "let's revisit in Q3" if there is
  no Q3.

## Output

Grouped by bucket, counts first, drafts only for the buckets that get replies,
each one humanized. Then the gate: the user sends them.

```
INBOX  ·  52 items  ·  3 LEAD, 2 RECRUITER, 4 PEER, 2 ASK, 41 SPAM

SPAM  (41) - archive. 38 are the same sequence: no-specifics invite,
"quick question" within 4 minutes of accept, calendar link in message one.
```

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
- Each reply to send is in the **language of the incoming message**. The
  other version is a reference translation. Mark which one to send.
