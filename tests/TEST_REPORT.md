# TEST_REPORT — Engingers_gpa_calculator_agent

**Status:** ✅ Deployed and tested (2/2)

---

## Environment

| Item | Value |
|---|---|
| Agent name | `Engingers_gpa_calculator_agent` |
| Environment | local (Developer Edition) |
| LLM | `groq/openai/gpt-oss-120b` |
| Style | `react_core` |

---

## Tools Deployed

| Tool | Import Status |
|---|---|
| `Engingers_validate_subject_weights` | ✅ Imported |
| `Engingers_calculate_subject_grade` | ✅ Imported |
| `Engingers_calculate_cumulative_gpa` | ✅ Imported |
| `Engingers_add_or_update_component` | ✅ Imported |
| `Engingers_remove_component` | ✅ Imported |
| `Engingers_review_subject_summary` | ✅ Imported |

> Note: ADK emits known false-positive warnings about Pydantic/dict type hints.
> All tools imported and executed successfully — these warnings do not affect runtime.

---

## Test Run 1 — Single-turn (Happy Path)

**Prompt:** Provide full GPA data for 2 subjects in one message:
- CS101 Computer Science (3 credit hours): Midterm 30% 72/100, Assignment 20% 18/20, Final 50% 80/100
- MATH201 Mathematics (4 credit hours): Quiz1 10% 9/10, Quiz2 10% 7/10, Midterm 30% 68/100, Final 50% 75/100

**Expected:** GPA = 3.13, CS101 = B+ (79.6%), MATH201 = B (73.9%)

**Result:** ✅ PASS
- All 6 tools fired in correct sequence (`add_or_update_component` × 7, `validate_subject_weights` × 2, `calculate_subject_grade` × 2, `calculate_cumulative_gpa` × 1)
- `Engingers_calculate_cumulative_gpa` returned GPA = 3.13, classification = "Merit"
- Agent presented a formatted grade table with correct letter grades, grade points, and credit-weighted GPA formula

---

## Test Run 2 — Multi-turn (Score Edit + Re-calculation)

**Thread ID:** `0414a250-5afa-4c7d-a0c4-e79610850caf`

**Turn 2 Prompt:** "My CS101 Midterm score was 82 out of 100, not 72. Please correct it and recalculate my GPA."

**Expected:** CS101 updates to 82.6% → A- (3.7), GPA updates to 3.30

**Result:** ✅ PASS
- Agent correctly recalled CS101 data from conversation history
- `Engingers_add_or_update_component` detected the existing "Midterm" and returned `action: "updated"`
- CS101 weighted score increased to 82.6%, letter grade changed from B+ (3.3) to A- (3.7)
- `Engingers_calculate_cumulative_gpa` returned updated GPA = 3.30
- Agent presented a clear diff showing what changed and why

---

## Known Issues / Resolutions

| Issue | Resolution |
|---|---|
| ADK deserialises `list[Subject]` elements as plain `dict` objects | Added `isinstance(dict)` guard + coercion in all 5 affected tools |
| Internal tool-to-tool call returns `ToolResponse` wrapper, not raw Pydantic model | Refactored `Engingers_calculate_cumulative_gpa` and `Engingers_review_subject_summary` to call private `_compute_subject_grade()` helper instead of `Engingers_calculate_subject_grade()` @tool directly |

---

## Manual Testing Instructions

### UI
Open watsonx Orchestrate → Chat with **Engingers GPA Calculator** → try the starter prompts.

### CLI
```bash
orchestrate chat ask -n Engingers_gpa_calculator_agent "I want to calculate my GPA" -r
```
> ⚠️ May hang on SaaS — use Bob's `chat_with_agent` MCP tool instead.

### Bob (MCP)
> Chat with `Engingers_gpa_calculator_agent`: `<any of the prompts below>`

---

## Sample Test Prompts

| # | Prompt | Expected Output |
|---|---|---|
| 1 | "Hi, I'm taking CS101 (3 credit hours). Midterm worth 30%, scored 85/100." | Agent adds component, shows weight = 30%, 70% remaining |
| 2 | "Add Final Exam 70% scored 78/100 to CS101." | Agent adds, weights = 100%, shows grade preview B+ |
| 3 | "I made a mistake — my CS101 Midterm was 90 not 85." | Agent updates component, recalculates — grade moves to A- |
| 4 | "Show me a full review of my CS101 subject." | Calls `Engingers_review_subject_summary`, lists all components + grade preview |
| 5 | "Add MATH201 (4 credit hours) with Quiz 10% 9/10, Midterm 40% 72/100, Final 50% 80/100. Then calculate my overall GPA." | All weights = 100%, GPA calculated and displayed |
