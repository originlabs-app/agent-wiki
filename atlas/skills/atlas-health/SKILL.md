---
name: atlas-health
description: >
  Deep audit of the knowledge graph and wiki. Finds contradictions,
  orphans, broken links, stale content, god nodes, and surprising
  connections. Use weekly or when things feel stale.
---

# /atlas-health

Deep audit of the knowledge graph and wiki. Not a quick check — a thorough review. Run weekly or when things feel stale.

## Usage

```bash
# Full audit — graph + wiki health
atlas audit --root /path/to/project

# Top god nodes (most connected)
atlas god-nodes --root /path/to/project --top 20

# Most surprising edges
atlas surprises --root /path/to/project --top 20

# Quick stats
atlas stats --root /path/to/project
```

## Step-by-step instructions

When the user invokes this skill, run the full audit pipeline:

### 1. Run the full audit (silent)

Execute all checks before showing anything:

```bash
# Full audit — orphans, broken links, stale pages, god nodes, health score
atlas audit --root <project>

# Top 20 most connected nodes
atlas god-nodes --root <project> --top 20

# Top 20 most surprising connections
atlas surprises --root <project> --top 20

# Quick graph stats
atlas stats --root <project>

If in a code repo, also check:

```bash
# What changed recently in the repo
git log --oneline -20

# What files changed in the last week
git diff --stat @{7.days.ago}
```

### 2. Report issues by category

Group findings by severity and category. Be specific and actionable.

**Health score:** Start with the number. "Health score: 72/100 (good). Penalty breakdown: 3 orphans (-6), 2 broken links (-4), 5 stale pages (-10)."

**Contradictions:** "Page A says [X] but page B says [Y]. Which is correct?"
- Look for nodes in different communities that share the same label.
- Check if wiki decisions conflict with project status.

**Broken links:** "These wikilinks point to pages that don't exist:"
- Format: `[[concept]]` in `wiki/projects/acme.md` → no `wiki/concepts/concept.md`
- Suggest: create the missing page or remove the link.

**Orphan pages:** "These pages have no inbound links from other pages:"
- Every orphan is either a gap in cross-linking or dead content.
- Suggest adding wikilinks from related pages.

**Stale pages:** "These pages haven't been updated in 30+ days:"
- The threshold is configurable (default: 30 days).
- For stale pages in `wiki/sources/`, suggest re-ingesting the original source.
- For stale pages in `wiki/projects/`, compare with git log.

**God nodes:** "The top 5 most connected concepts are: [list with degree]"
- God nodes are expected (auth, db, api are always connected).
- Unexpected god nodes deserve investigation — why is this so connected?

**Surprise edges:** "Unexpected cross-community connections:"
- These are edges between concepts in different communities with cross-type links.
- Example: an auth module calling an email template system.

**Low confidence nodes:** Check the graph for nodes with confidence="low" or "AMBIGUOUS" edges.
- "These nodes have ambiguous connections. Should I investigate or mark for review?"

**Repo vs wiki drift:** If in a code repo:
- "The repo has had 14 commits since the wiki was last updated."
- "Key changes: [list from git log]. The wiki still says [old state]."

**Error propagation:** "I found a claim in [page] that seems to have been copied from [other page] without verification."

### 3. Suggest improvements

After reporting, propose concrete actions:

**Fill gaps:** "The wiki mentions [topic] 4 times but has no dedicated page. Create wiki/concepts/[topic].md?"

**Refresh stale pages:** "These 5 project pages are over 30 days stale. Want me to cross-reference with git log and update them?"

**Fix broken links:** "I found 3 broken wikilinks. I can remove them or create stub pages. Which do you prefer?"

**Orphan resolution:** "These 4 orphan pages could be linked from [related pages]. Want me to add the links?"

**Web enrichment:** "The wiki has no sources for [concept]. Want me to search the web, find a good source, save to raw/, and compile it?"

**Re-scan:** "The repo has changed since the last scan. Want me to run `atlas scan --update .` to refresh the graph?"

**Deep re-compile:** "These sources in raw/ingested/ were ingested but the wiki pages are thin. Re-compile with more detail?"

### 4. Ask for approval before fixing

Never silently fix. The whole point of health is surfacing issues for the human to validate.

Show a prioritized list:
1. P0: contradictions (data integrity risk)
2. P1: broken links (broken knowledge)
3. P2: stale pages (outdated decisions)
4. P3: orphans (discoverability)
5. P4: low-confidence nodes (validation needed)

Ask: "Want me to fix 1-3? I'll propose exact changes for each."

### 5. Execute approved fixes

After user approval:
1. Fix each issue with specific commands or wiki edits
2. Re-run audit to verify health score improved
3. Report: "Health score: 72 → 89. Fixed: [list of actions]."

## How health scoring works

The health score has two components:

1. **Graph health** (from `GraphStats.health_score`): Based on confidence ratio. `(EXTRACTED / total) * 100 - (AMBIGUOUS / total) * 50`
2. **Wiki penalty** (from audit): `-2` per issue (orphan, broken link, stale page), capped at `-30`

Score ranges:
- **80-100**: Healthy. Minor maintenance.
- **60-79**: Some issues. Priority fixes recommended.
- **40-59**: Needs attention. Multiple issues.
- **0-39**: Degraded. Structural problems. Consider re-scan or re-compile.

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. The goal is finding real issues, not hypothetical ones.
3. Show write-back proposals before executing. User approves all changes.
4. 2-5 questions max. Never more.
5. If atlas CLI is not available, continue normally (grep wiki/ and check git log).
6. Health is weekly, not monthly. Run `atlas audit` regularly.
7. A low health score isn't bad — it means the wiki is being actively written and hasn't been linted yet.
8. The audit is read-only until user approves fixes.
9. Always re-run audit after fixes to confirm improvement.

---

## Other Atlas skills

- `/atlas-start` — begin a session, read the graph, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
