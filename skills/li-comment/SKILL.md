---
noteId: "4dbf2ae2d3a311f18d5e8305d12a06ac"
tags: []
name: "li-comment"
description: "Write comments on other people's LinkedIn posts that read as a person with an opinion, not a bot. Use when the user pastes a post and wants a comment, says \"comment on this\", \"engage with this\", \"what do I say here\", or wants a batch of comments for their engagement round. Bilingual: understands French requests (\"écris un post LinkedIn\") and returns every copy-ready text in both French and English."

---

# li-comment

Commenting is the highest-leverage thing on LinkedIn and the easiest to do
badly. A comment on a post with 400 reactions gets seen by more people than
most of your own posts. A generic one gets seen by nobody and costs you
credibility with the author.

## Input

The user pastes the post text (and the author's name and role if they have
it). If they paste a screenshot, read it. If they give you a URL you cannot
open, ask them to paste the text - do not guess what the post said, and do not
use browser automation to scrape the feed.

## The nine comment types

Pick by what the post actually is. Never default to type 1.

| # | type | when | shape |
| --- | --- | --- | --- |
| 1 | **Add a datum** | post makes a claim you can support with a number | "We saw the same thing: 40% of our..." |
| 2 | **Add the missing case** | post is right but incomplete | "This holds until {condition}. Then..." |
| 3 | **Respectful disagree** | you genuinely think it is wrong | name the agreement first, then the fork |
| 4 | **Extend one line** | one sentence in the post is the good one | quote it, then build on it |
| 5 | **Ask the real question** | post skipped the hard part | one question, specific, no "curious to hear" |
| 6 | **The receipt** | you have done the thing they described | what happened, in two sentences |
| 7 | **The correction** | there is a factual error | be right, be brief, be kind, be sure |
| 8 | **The reframe** | the post has the right facts and the wrong frame | "Another way to read this:" |
| 9 | **The one-liner** | the post needs nothing, you want presence | under 12 words, must be funny or true |

## Rules

- **2 to 4 sentences.** Longer reads as a hijack. Shorter reads as filler.
- **Never open with "Great post"**, "Love this", "So true", "Couldn't agree
  more", "This resonates", or the author's first name followed by an
  exclamation mark. All six are invisible.
- **No emoji openers.** No 🔥 or 👏 as a first character.
- **Never restate the post.** The author knows what they wrote and so does
  everyone reading.
- **One idea.** A comment with two points reads as a blog attempt.
- **Say the specific thing.** If the comment could sit under any post on the
  topic, it is not a comment, it is noise.
- **Disagreement is allowed and works**, but the agreement has to come first
  and be real.

## Output

Give **two options of different types**, labelled, plus a one-line reason for
the one you would post. Run both through `/li-human` first - a comment with an
em dash in it is more obviously machine-written than a post, because comments
are short and people read them closely.

```
COMMENT OPTIONS  (on @author's post about hiring)

[6 · Receipt]
We tried the no-resume version of this for 3 hires last year. Two were the
best hires we made. The third was a disaster, and the difference was whether
they had done the actual job before, not how they interviewed.

[3 · Respectful disagree]
Agree on the signal problem. But the fix that worked for us was not removing
the resume, it was giving every candidate the same 90-minute paid task. Same
outcome, far less argument internally.

Post the first. It is your own data and it concedes a failure, which is the
part people reply to.
```

## Batch mode

If the user wants an engagement round, ask for the 5-10 posts as pasted text
in one message, return one comment each in a single block, and keep a running
note of who they have already commented on this week in
`~/.claude/linkedin/log.md`. Commenting on the same three people every day is
visible and it looks like what it is.

## Never

Do not auto-post. Do not use a browser tool to publish comments on the user's
behalf. Automated posting and scraping both violate LinkedIn's User Agreement
and put the account at risk. This skill writes the comment. The user posts it.

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
- The comment to post is in the **language of the post** being commented on.
  The other version is a reference translation, so the user knows exactly what
  they are posting. Say which one to post.
