---
noteId: "4dbf51f0d3a311f18d5e8305d12a06ac"
tags: []
name: "li-dm"
description: "Write connection notes and DM follow-ups that get replies - the 200-character invite, the first message, and the two follow-ups. Use when the user says \"write a connection request\", \"DM this person\", \"outreach message\", \"how do I follow up\", or is reaching out to someone specific on LinkedIn. Bilingual: understands French requests (\"écris un post LinkedIn\") and returns every copy-ready text in both French and English."

---

# li-dm

The invite note is 200 characters. The first DM decides whether there is a
second one. Neither is a pitch.

## Before writing, get the specifics

Ask for, in one batched question:

1. **Who** - name, role, company.
2. **The hook** - the actual reason to reach out now. A post they wrote, a
   thing their company shipped, a mutual connection, a talk they gave. Not
   "they fit my ICP".
3. **What the user wants** - a conversation, a referral, a job, a sale. Be
   honest internally, even if the message does not lead with it.

If there is no specific reason to message this person today, say so. A message
with no reason is what everyone else sends, and it is why their reply rate is
2%.

## The invite note (200 characters)

```
{one specific reference to them} + {one line of who you are} + {no ask}
```

The note asks for nothing. It exists to make the accept obvious. Under 200
characters including spaces - count them and show the count.

```
Saw your post on killing the discovery call - we did the same thing in March
and it worked. I run ops at a 12-person studio. Would like to follow along.
                                                                    [187/200]
```

## The first message, after they accept

Wait a day. Then:

- **Two to four sentences.** A screen of text is a delete.
- **Reference the specific thing** from the note - continuity is the whole
  reason the note was specific.
- **Give something before asking.** A number, a template, a name, an answer.
- **One ask, and make it small.** "Worth a 15-minute call?" beats "let me walk
  you through our platform".
- **No calendar link in message one.** It reads as a funnel, because it is.

## Follow-ups

Two. That is the number.

- **+4 days** - add something new. Never "just bumping this" or "following up
  on my last message". If you have nothing new, you have no follow-up.
- **+10 days** - the close-the-loop message. Say you will stop, and mean it.
  This one gets a surprising share of the total replies, because it removes
  the pressure.

Then stop. A third follow-up converts nobody and costs the relationship.

## Never

- Never send an automated connection or message sequence. Automated outreach
  tools violate LinkedIn's User Agreement and get accounts restricted.
- Never fabricate a mutual connection, a shared school, or having read
  something the user has not read.
- Never write the message that opens "I hope this message finds you well".
- Never send more than 20 invites a day. Beyond that, LinkedIn throttles the
  account, and a throttled account is a dead one.

## Output

The invite note with its character count, the first message, and both
follow-ups with the day they go out. All humanized through `/li-human`. The
user sends every one of them by hand.

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
- The message to send is in the **recipient's language**. If you do not know
  it, ask. Show the 200-character count for **both** invite notes. Each one
  has to fit on its own.
