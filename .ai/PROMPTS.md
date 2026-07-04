# PROMPTS.md — Useful AI Prompts
# TN Board Portal

> Save prompts here that produce high-quality results for this project.
> Update this file as you discover better prompts.

---

## Master Bootstrap Prompt

Use this at the start of every new AI session to establish context:

```
Read the entire .ai/ folder before making any changes to this project.

Start with AGENTS.md, then PROJECT_CONTEXT.md, ARCHITECTURE_RULES.md, DATABASE_RULES.md, 
and CODING_STANDARDS.md. After reading, summarize your understanding of the project 
and confirm you are ready before I give you a task.
```

---

## Feature Request Prompt

```
I want to implement [FEATURE NAME].

Before writing any code:
1. Read the relevant .ai/ documentation
2. Identify all files that will be affected
3. Produce an implementation plan covering:
   - Database migration (if needed)
   - Service layer changes
   - Component changes
   - Page changes
   - Router changes
   - Documentation updates
4. Wait for my approval before implementing anything
```

---

## Bug Fix Prompt

```
Bug report: [DESCRIBE THE BUG]

Before fixing:
1. Read BUG_FIX_WORKFLOW.md
2. Identify the root cause layer (Frontend? Service? DB? RLS? RPC?)
3. Trace the data flow to confirm understanding
4. Propose a fix with justification
5. Wait for my approval before modifying any code
```

---

## Code Review Prompt

```
Review this file/component for:
1. Adherence to CODING_STANDARDS.md
2. Correct use of the service layer pattern (no direct Supabase calls from components)
3. Loading states and error handling completeness
4. Accessibility issues
5. Performance concerns
6. Security issues

File: [PASTE FILE CONTENTS OR PATH]
```

---

## Migration Writing Prompt

```
Write a new database migration for this project.

Requirements:
- It must be numbered 015 (next in sequence)
- Follow the template in DATABASE_RULES.md
- Must be backward compatible
- Use CREATE OR REPLACE for any functions
- Use IF NOT EXISTS / IF EXISTS for all DDL
- Include explicit GRANT statements
- Comment every section clearly

Purpose: [DESCRIBE WHAT THE MIGRATION DOES]
```

---

## Architecture Decision Prompt

```
I'm considering this architectural change: [DESCRIBE CHANGE]

Before recommending anything:
1. Read ARCHITECTURE_RULES.md
2. Read DECISIONS.md for past decisions
3. Assess whether this change is compatible with the existing architecture
4. Identify the tradeoffs
5. Recommend the approach that best fits this project's goals
6. If you recommend the change, provide a migration path

Do NOT implement anything. Only provide analysis and recommendation.
```

---

## Documentation Update Prompt

```
Update the documentation for this project after the following change was made:

Change: [DESCRIBE WHAT WAS IMPLEMENTED]

Update these files:
- CHANGELOG.md (add to [Unreleased] section)
- ROADMAP.md (mark completed items if applicable)
- docs/ARCHITECTURE.md (if architecture changed)
- .ai/CHANGE_HISTORY.md (log the implementation)
- .ai/DECISIONS.md (log any new decisions made)

Follow DOCUMENTATION_RULES.md for format and content requirements.
```

---

## Supabase RPC Writing Prompt

```
Write a new PostgreSQL RPC function for this project.

Requirements:
- Follow DATABASE_RULES.md for function structure
- Use SECURITY DEFINER only if anon access is needed
- Include explicit parameter types
- Use parameterized queries (never string concatenation)
- Return typed data
- Include a GRANT statement at the end
- Use CREATE OR REPLACE (idempotent)

Function purpose: [DESCRIBE WHAT THE FUNCTION DOES]
Parameters: [LIST PARAMETERS]
Returns: [DESCRIBE RETURN TYPE]
```

---

## Component Creation Prompt

```
Create a new React component for this project.

Component name: [NAME]
Purpose: [WHAT IT DOES]
Props it receives: [LIST PROPS]

Requirements from CODING_STANDARDS.md:
- Functional component with hooks
- No direct Supabase calls (receive data via props if needed)
- Loading state if async
- Error state if needed
- Tailwind CSS only
- Accessible (semantic HTML, aria labels)
- No console.log
- Follow the existing component file structure
```
