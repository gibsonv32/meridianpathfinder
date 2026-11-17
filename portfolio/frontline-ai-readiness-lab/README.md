# Frontline AI Readiness Lab

An interactive work sample for the Manager, Learning & Enablement Consultant for AI role (R1004111). It is a 15-minute adaptive learning sprint for contact center teams, plus the adoption dashboard a leader would use to judge the rollout.

Independent demonstration. Not affiliated with or endorsed by Capital One. The company (Northfield Card Services), the tool (Relay Assist), and every person, policy and metric are fictional.

## What is in it

| View | What a reviewer does |
|---|---|
| Diagnostic | Answers five scenarios with a confidence rating. A rule set builds a lesson path from the answers, the confidence and the role. |
| Learn | Takes two to four short lessons with a tutor beside each one. Each lesson has a check and an explain-back. |
| Simulation | Works a realistic case: writes a prompt that is scored against a rubric, finds the errors in an AI draft, makes a judgment call. |
| Results and coaching | Sees five competencies scored before and after, the evidence behind each score, a guided reflection and a team-leader toolkit. |
| Adoption analytics | Explores a synthetic 2,400-person rollout: funnel, weekly use, competency heatmap, business results, teams needing support. |
| Deployment blueprint | Reads how this maps to the role, a reference architecture, governance, measurement and a 90-day plan. |

Three role tracks: contact center agent, back-office specialist, team leader.

## Files

- `index.html`: page markup and styles. It has no `<html>` or `<head>` wrapper because the Claude artifact host adds one.
- `content.js`: all learning content and the synthetic data.
- `app.js`: application logic. Plain JavaScript, no dependencies, no build step.
- `standalone.html`: the same app as one self-contained file. Open it in any browser, attach it to an email, or put it on any static host.
- `build-standalone.mjs`: regenerates `standalone.html`.

```bash
node build-standalone.mjs
```

## The tutor

The tutor answers from prepared lesson notes by default, so the app works for anyone with no account. When the page is opened as a Claude artifact by a signed-in viewer who allows it, the same panel answers live through Claude. Scores never depend on the live model: the adaptive rules and every rubric are rule-based and shown to the learner.

Nothing is sent to a server. Progress is kept in the browser's local storage so a reviewer can close the tab and resume.
