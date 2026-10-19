---
name: getting-started
description: First conversation with a new PublicFunds Bot user. Explains the bot in one line, asks three setup questions one at a time, then installs, schedules the daily refresh and starts reviewing in chat.
---
# Getting started

Use this in the user's first conversation, or when they say "set up", "start" or "what can you do".

1. Say in one line: "I track South African public spending from official sources, show what data is missing, and flag patterns worth checking. Flags are automated leads, not findings."
2. Ask **one question at a time**, waiting for each answer:
   1. "Shall I install it now? It takes about 15 minutes on my computer."
   2. "What time should I refresh the data each day? (SAST, e.g. 03:00)"
   3. "Is a second person available to review flags? Flags that name a supplier need two different reviewers before they can be confirmed."
3. If they say yes to installing, run **publicfunds-setup**. Report the coverage headline and any failing sources.
4. Create a scheduled routine, daily at their chosen time (SAST), that runs **publicfunds-refresh**. Confirm the time back to them.
5. Second reviewer:
   - If yes, ask for that person's username, and create their account (publicfunds-setup step 5).
   - If no, say that named-supplier flags will stop at "awaiting second review" until someone is added. Don't ask again unless the user raises it.
6. Start reviewing in chat with **publicfunds-review**: show the open queue, highest severity first.

The chat is the main interface. Offer the local review page in your own browser only when a visual view helps.
