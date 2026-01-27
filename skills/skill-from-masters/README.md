# Skill From Masters

> **Stand on the shoulders of giants** — Create AI skills built on proven methodologies from domain experts.

A skill that helps you discover and incorporate frameworks, principles, and best practices from recognized masters before generating any new skill. Works with Claude Code, Codex, and other AI agent platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Why This Skill?

**The hard part of creating a skill isn't the format — it's knowing the best way to do the thing.**

Most professional domains have masters who spent decades figuring out what works:
- Jobs on product, hiring, and marketing
- Bezos on writing (6-pager) and decision-making
- Munger on mental models
- Chris Voss on negotiation

This skill surfaces their methodologies before you write a single line, so your skill embodies world-class expertise from day one.

## How It Works

```
1. You: "I want to create a skill for user interviews"

2. Skill-from-masters:
   ├── Checks local methodology database
   ├── Searches web for additional experts
   ├── Finds golden examples of great outputs
   ├── Identifies common mistakes to avoid
   └── Cross-validates across sources

3. Surfaces experts:
   - Rob Fitzpatrick (The Mom Test)
   - Steve Portigal (Interviewing Users)
   - Nielsen Norman Group best practices

4. You select which methodologies to incorporate

5. Extracts actionable principles from primary sources

6. Hands off to skill-creator to generate the final skill
```

## Key Features

| Feature | Description |
|---------|-------------|
| **3-Layer Search** | Local database → Web search for experts → Deep dive on primary sources |
| **Golden Examples** | Finds exemplary outputs to define quality bar |
| **Anti-Patterns** | Searches for common mistakes to encode "don't do this" |
| **Cross-Validation** | Compares multiple experts to find consensus and flag disagreements |
| **Quality Checklist** | Verifies completeness before generating |

## Methodology Database

The skill includes a curated database covering 15+ domains:

| Domain | Example Experts |
|--------|-----------------|
| Writing | Barbara Minto, William Zinsser, Amazon 6-pager |
| Product | Marty Cagan, Teresa Torres, Gibson Biddle |
| Sales | Neil Rackham (SPIN), Challenger Sale, MEDDIC |
| Hiring | Laszlo Bock, Geoff Smart, Lou Adler |
| User Research | Rob Fitzpatrick, Steve Portigal, JTBD |
| Engineering | Martin Fowler, Robert Martin, Kent Beck |
| Leadership | Kim Scott, Ray Dalio, Andy Grove |
| Negotiation | Chris Voss, Fisher & Ury |
| Startups | Eric Ries, Paul Graham, YC |
| Decision Making | Jeff Bezos, Charlie Munger, Annie Duke |

Plus an **"Oral Tradition"** section for experts who share primarily through talks and interviews (Steve Jobs, Elon Musk, Jensen Huang, Patrick Collison, etc.)

## Installation

### Option 1: Clone directly (Recommended)

```bash
# Navigate to your skills directory
cd ~/.claude/skills  # Claude Code
# or your platform's skills path

# Clone this skill
git clone https://github.com/anthropics/skill-from-masters.git
```

### Option 2: Manual installation

1. Download the `skill-from-masters` folder
2. Place it in your skills directory

### Dependency

This skill works with **skill-creator**. Make sure skill-creator is available in your environment.

## Usage

The skill automatically activates when you ask to create a new skill. It runs **before** skill-creator to ensure your skill is built on proven methodologies.

### Example Session

**You:** "Help me create a skill for writing product requirement documents"

**Skill-from-masters:**
> Let me search for the best methodologies on PRD writing.
>
> *[Searches: "PRD best practices expert", "product requirements document methodology"]*
>
> I found several strong frameworks:
>
> **Product Management:**
> - Marty Cagan: Problem-first PRDs, separating problem space from solution space
> - Teresa Torres: Outcome-focused requirements
>
> **Business Writing:**
> - Barbara Minto: Pyramid Principle - lead with conclusion, MECE structure
> - Amazon: Working backwards, 6-pager narrative format
>
> **Golden Examples Found:**
> - Intercom's public PRD template
> - Linear's product spec format
>
> **Common Mistakes:**
> - Jumping to solutions before defining the problem
> - Writing for engineers instead of for alignment
> - Missing success metrics
>
> Which approaches resonate? Or should I search deeper into any of them?

**You:** "I like Amazon's approach combined with Cagan's problem-first thinking."

**Skill-from-masters:** *[Fetches primary sources on Amazon's methodology, extracts principles, then generates skill via skill-creator]*

## Skills

This repository contains the following skills:

| Skill | Description |
|-------|-------------|
| **[skill-from-masters](skill-from-masters/SKILL.md)** | Create new skills based on proven methodologies from domain experts. |
| **[search-skill](skills/search-skill/SKILL.md)** | Search for existing skills from trusted marketplaces. |
| **[skill-from-github](skills/skill-from-github/SKILL.md)** | Learn from high-quality GitHub projects and create skills based on that knowledge. |

### skill-from-masters

When you want to **create a new skill based on expert methodologies**:

- 3-layer search: local database → web experts → primary sources
- Finds golden examples and anti-patterns
- Cross-validates across multiple experts
- Hands off to skill-creator for final generation

**Example:**
```
You: "Help me create a skill for user interviews"
→ Finds: Rob Fitzpatrick (The Mom Test), Steve Portigal, Nielsen Norman Group
→ You select which methodologies to incorporate
→ Generates skill with those principles encoded
```

### search-skill

When you want to **find an existing skill** instead of creating one:

- Searches only 5 trusted sources (no random internet results)
- Tier-based priority: official → curated → aggregators
- Filters out low-quality results (stars < 10, outdated, no SKILL.md)
- Security checks for suspicious code patterns

**Example:**
```
You: "I need a skill for frontend design, automated testing, and code review"
→ Searches: anthropics/skills, ComposioHQ, travisvn, skills.sh, skillsmp.com
→ Returns: frontend-design (official), webapp-testing (official), code-review-excellence (26k stars)
```

### skill-from-github

When you want to **learn from a GitHub project** and turn that knowledge into a skill:

- Search GitHub for quality projects (stars > 100, actively maintained)
- Present options and wait for your confirmation
- Deep dive into selected project (README, source code, examples)
- Summarize what it learned, then create skill via skill-creator

**Example:**
```
You: "I want to convert images to ASCII art"
→ Searches GitHub, finds: ascii-image-converter (3.1k stars), RASCII (224 stars)
→ You select ascii-image-converter
→ Learns: brightness-to-character mapping, aspect ratio handling, color techniques
→ Creates skill encoding that knowledge (not just wrapping the tool)
```

**Key difference:** This skill encodes the *knowledge* from projects, so the skill works even without the original tool installed.

## File Structure

```
skill-from-masters/
├── skill-from-masters/
│   ├── SKILL.md                              # Core skill: create from expert methodologies
│   └── references/
│       ├── methodology-database.md           # Curated expert frameworks
│       └── skill-taxonomy.md                 # 11 skill type categories
├── skills/
│   ├── search-skill/
│   │   └── SKILL.md                          # Search existing skills from trusted sources
│   └── skill-from-github/
│       └── SKILL.md                          # Learn from GitHub projects
├── README.md
├── LICENSE
└── .gitignore
```

## Quality Checklist

Before finalizing any skill, this skill verifies:

- [ ] Searched beyond the local database
- [ ] Found primary sources, not just summaries
- [ ] Found golden examples of the output
- [ ] Identified common mistakes to avoid
- [ ] Cross-validated across multiple experts
- [ ] Encoded specific, actionable steps (not vague principles)

## Contributing

Contributions welcome! Especially:

- Adding new domains and experts to the methodology database
- Improving framework descriptions with source links
- Sharing examples of skills created with this approach

Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License — feel free to use, modify, and distribute.

---

**Philosophy:** Quality isn't written. It's selected.
