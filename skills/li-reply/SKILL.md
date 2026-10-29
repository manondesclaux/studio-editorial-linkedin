---
noteId: "4dbf51f3d3a311f18d5e8305d12a06ac"
tags: []
name: "li-reply"
description: "Handle the replies under the user's own LinkedIn posts - draft answers to every comment, sorted by which ones are worth answering. Use when the user pastes the comments on their post, says \"reply to these\", \"handle my comments\", \"someone said X on my post\", or is dealing with a critic or a lead in the comments. Bilingual: understands French requests (\"écris un post LinkedIn\") and returns every copy-ready text in both French and English."

---

# li-reply

The reply thread under your own post is where reach is actually decided. Every
reply is a second engagement event on the post, and the first hour of replies
does most of the work. But the value is not equal across comments, so this
skill sorts before it writes.

## Input

The user pastes the comments, ideally with names and roles. Screenshots are
fine. Do not scrape the thread with a browser tool.

## Triage first

Sort every comment into one of five buckets and say the count out loud:

| bucket | what it is | what it gets |
| --- | --- | --- |
| **LEAD** | someone describing the problem you solve | a real answer + a soft open door |
| **SUBSTANCE** | adds data, disagrees, extends | the longest reply on the thread |
| **PEER** | a name worth being seen next to | a reply that gives them something |
| **SUPPORT** | "great post", 🔥, a tag | a like, and a 3-8 word reply at most |
| **NOISE** | pitch, spam, bad faith | nothing, or one line and out |

Then write in that order, and stop writing when the value stops.

## How to reply

- **Answer the actual question.** If someone asks how, tell them how, in the
  reply. Do not send them to a DM to hear the answer they could have had.
- **Use their name once**, at the start, and never with an exclamation mark.
- **Match their length.** A two-line comment does not get a six-line reply.
- **To a critic:** concede the true part first, in their words, then hold the
  line on the part you believe. Never delete, never get defensive, never reply
  twice on the same thread.
- **To a lead:** answer fully in public. The open door is one sentence at the
  end, and it is an offer of help, not a pitch. Public value is what makes the
  next person DM you.
- **To a pitch in your comments:** ignore it. Replying gives it reach.

## Output

One block, grouped by bucket, each reply copy-ready and already humanized:

```
REPLIES  ·  17 comments  ·  1 LEAD, 3 SUBSTANCE, 4 PEER, 8 SUPPORT, 1 NOISE

LEAD
@Sarah Chen - "we have the same problem with proposals"
> The part that fixed it for us was pulling the pricing table out of the doc
> entirely and sending it as its own page. Cut a whole review round. Happy to
> send you the template if it is useful.

SUBSTANCE
@Marcus Webb - disagrees on cadence
> Fair, and 4x a week only worked because I had 8 months of posts behind it.
> From a standing start I would do what you said.

SUPPORT  (like these, reply to the first three)
@... "This is great" -> Thanks Dan.
...

NOISE  (1)
Skipped: an agency pitch. Replying gives it reach.
```

Then the gate: **nothing is posted until the user says yes.** They paste the
replies themselves.

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
- Each reply to post is in the **language of the comment** it answers. The
  other version is a reference translation. Mark which one to paste.
