"""
Engingers GPA Calculator Tools
Provides stateless, pure-computation tools for GPA and grade management.
State (subjects, components) is passed in/out via structured Pydantic models
so the agent maintains all context across the conversation.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------------------------
# Shared domain models
# ---------------------------------------------------------------------------

class AssessmentComponent(BaseModel):
    """A single assessment item within a subject (e.g. Midterm, Assignment 1)."""
    name: str
    weight_percent: float    # e.g. 30.0 means 30 %
    score_obtained: float    # marks the student received
    max_score: float         # full marks for this component


class Subject(BaseModel):
    """A university/college subject with its assessment breakdown."""
    subject_name: str
    subject_code: str
    credit_hours: float
    components: list[AssessmentComponent]


class GradeResult(BaseModel):
    """Computed grade details for one subject."""
    subject_name: str
    subject_code: str
    credit_hours: float
    total_weight_used: float
    weighted_score: float       # 0–100
    letter_grade: str
    grade_point: float          # 4.0 scale
    is_valid: bool              # True when total weights == 100 %
    validation_message: str
    component_breakdown: list[dict]


class GPAResult(BaseModel):
    """Overall GPA across all supplied subjects."""
    subject_results: list[GradeResult]
    cumulative_gpa: float
    total_credit_hours: float
    gpa_classification: str
    summary: str


class WeightValidation(BaseModel):
    """Result of validating assessment weights for a subject."""
    subject_name: str
    total_weight: float
    is_valid: bool
    remaining_weight: float
    message: str


class ComponentUpdateResult(BaseModel):
    """Confirmation after adding/editing/removing a component."""
    subject_name: str
    action: str
    component_name: str
    updated_components: list[AssessmentComponent]
    current_total_weight: float
    message: str


# ---------------------------------------------------------------------------
# Internal helpers (not tools)
# ---------------------------------------------------------------------------

def _letter_grade(score: float) -> tuple[str, float]:
    """Return (letter, grade_point) for a 0-100 weighted score."""
    if score >= 90:
        return "A+", 4.0
    elif score >= 85:
        return "A", 4.0
    elif score >= 80:
        return "A-", 3.7
    elif score >= 77:
        return "B+", 3.3
    elif score >= 73:
        return "B", 3.0
    elif score >= 70:
        return "B-", 2.7
    elif score >= 67:
        return "C+", 2.3
    elif score >= 63:
        return "C", 2.0
    elif score >= 60:
        return "C-", 1.7
    elif score >= 57:
        return "D+", 1.3
    elif score >= 50:
        return "D", 1.0
    else:
        return "F", 0.0


def _gpa_classification(gpa: float) -> str:
    if gpa >= 3.7:
        return "Distinction / Dean's List"
    elif gpa >= 3.0:
        return "Merit"
    elif gpa >= 2.0:
        return "Pass"
    elif gpa >= 1.0:
        return "Conditional Pass"
    else:
        return "Fail"


# ---------------------------------------------------------------------------
# Internal computation helper (shared by both subject-grade tools)
# ---------------------------------------------------------------------------

def _compute_subject_grade(subj: Subject) -> GradeResult:
    """Pure-Python grade computation — does NOT go through the ADK tool wrapper."""
    components = [
        AssessmentComponent(**c) if isinstance(c, dict) else c
        for c in subj.components
    ]
    total_weight = sum(c.weight_percent for c in components)
    is_valid = abs(total_weight - 100.0) < 0.01

    weighted_score = 0.0
    breakdown = []
    for comp in components:
        if comp.max_score <= 0:
            contribution = 0.0
        else:
            contribution = (comp.score_obtained / comp.max_score) * comp.weight_percent
        weighted_score += contribution
        breakdown.append({
            "component": comp.name,
            "score": f"{comp.score_obtained}/{comp.max_score}",
            "weight": f"{comp.weight_percent}%",
            "contribution": f"{contribution:.2f}%",
        })

    weighted_score = round(weighted_score, 2)
    letter, gp = _letter_grade(weighted_score)

    if is_valid:
        val_msg = "✅ All weights sum to 100% — result is accurate."
    elif total_weight < 100.0:
        val_msg = (
            f"⚠️  Weights only sum to {total_weight:.1f}%. "
            "Result is a partial estimate. Add the remaining components."
        )
    else:
        val_msg = (
            f"❌ Weights exceed 100% ({total_weight:.1f}%). "
            "Please correct weights before relying on this result."
        )

    return GradeResult(
        subject_name=subj.subject_name,
        subject_code=subj.subject_code,
        credit_hours=subj.credit_hours,
        total_weight_used=round(total_weight, 2),
        weighted_score=weighted_score,
        letter_grade=letter,
        grade_point=gp,
        is_valid=is_valid,
        validation_message=val_msg,
        component_breakdown=breakdown,
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def Engingers_validate_subject_weights(subject: Subject) -> WeightValidation:
    """Validate that the total weight percentages of all assessment components for a subject add up correctly.

    Use this tool before calculating grades to confirm the weights are valid (should sum to 100%).

    Args:
        subject (Subject): The subject with its assessment components including weights.
    Returns:
        WeightValidation: Validation result showing whether weights are correct and any remaining weight.
    """
    if isinstance(subject, dict):
        subject = Subject(**subject)
    subject.components = [
        AssessmentComponent(**c) if isinstance(c, dict) else c
        for c in subject.components
    ]
    total = sum(c.weight_percent for c in subject.components)
    remaining = round(100.0 - total, 4)
    is_valid = abs(total - 100.0) < 0.01

    if is_valid:
        message = (
            f"✅ Weights for '{subject.subject_name}' are valid. "
            f"Total = {total:.1f}% (100%). You're ready to calculate grades."
        )
    elif total < 100.0:
        message = (
            f"⚠️  Weights for '{subject.subject_name}' only sum to {total:.1f}%. "
            f"You still have {remaining:.1f}% unassigned. "
            "Please add more components or adjust existing weights."
        )
    else:
        message = (
            f"❌ Weights for '{subject.subject_name}' exceed 100% (currently {total:.1f}%). "
            f"Please reduce some weights by {abs(remaining):.1f}%."
        )

    return WeightValidation(
        subject_name=subject.subject_name,
        total_weight=round(total, 4),
        is_valid=is_valid,
        remaining_weight=remaining,
        message=message,
    )


@tool(permission=ToolPermission.READ_ONLY)
def Engingers_calculate_subject_grade(subject: Subject) -> GradeResult:
    """Calculate the final weighted score and letter grade for a single subject.

    Each component contributes (score_obtained / max_score) * weight_percent to the final score.
    A subject is valid only when all component weights sum to 100%.

    Args:
        subject (Subject): The subject containing all assessment components with scores and weights.
    Returns:
        GradeResult: Detailed grade breakdown including weighted score, letter grade, and grade point.
    """
    if isinstance(subject, dict):
        subject = Subject(**subject)
    return _compute_subject_grade(subject)


@tool(permission=ToolPermission.READ_ONLY)
def Engingers_calculate_cumulative_gpa(subjects: list[Subject]) -> GPAResult:
    """Calculate the cumulative GPA across multiple subjects using a credit-hour weighted average.

    This is the main GPA calculation tool. Each subject must have all its assessment
    components fully entered with weights summing to 100%.

    Args:
        subjects (list[Subject]): All subjects the student is enrolled in, each with complete components.
    Returns:
        GPAResult: Overall GPA, per-subject grade results, classification, and a summary message.
    """
    subject_results: list[GradeResult] = []
    total_quality_points = 0.0
    total_credits = 0.0
    warnings = []

    for subj in subjects:
        if isinstance(subj, dict):
            subj = Subject(**subj)
        result = _compute_subject_grade(subj)
        subject_results.append(result)
        total_quality_points += result.grade_point * subj.credit_hours
        total_credits += subj.credit_hours
        if not result.is_valid:
            warnings.append(
                f"'{subj.subject_name}': {result.validation_message}"
            )

    cumulative_gpa = round(total_quality_points / total_credits, 2) if total_credits > 0 else 0.0
    classification = _gpa_classification(cumulative_gpa)

    lines = [f"📊 Cumulative GPA: {cumulative_gpa} / 4.0 — {classification}"]
    for r in subject_results:
        lines.append(
            f"  • {r.subject_code} {r.subject_name}: {r.weighted_score}% → {r.letter_grade} ({r.grade_point})"
        )
    if warnings:
        lines.append("\n⚠️  Incomplete weight warnings:")
        lines.extend(f"  - {w}" for w in warnings)

    summary = "\n".join(lines)

    return GPAResult(
        subject_results=subject_results,
        cumulative_gpa=cumulative_gpa,
        total_credit_hours=total_credits,
        gpa_classification=classification,
        summary=summary,
    )


@tool(permission=ToolPermission.WRITE_ONLY)
def Engingers_add_or_update_component(
    subject: Subject,
    component_name: str,
    weight_percent: float,
    score_obtained: float,
    max_score: float,
) -> ComponentUpdateResult:
    """Add a new assessment component to a subject, or update an existing one if the name already exists.

    Use this when the student wants to add or edit an assessment item such as an assignment,
    midterm, final exam, quiz, or project.

    Args:
        subject (Subject): The subject to modify (with its current list of components).
        component_name (str): Name of the assessment component (e.g., 'Midterm', 'Assignment 1').
        weight_percent (float): Weight of this component as a percentage of the total grade (e.g., 30.0).
        score_obtained (float): The student's actual score for this component.
        max_score (float): The maximum possible score for this component.
    Returns:
        ComponentUpdateResult: The updated components list, new total weight, and a confirmation message.
    """
    if isinstance(subject, dict):
        subject = Subject(**subject)
    subject.components = [
        AssessmentComponent(**c) if isinstance(c, dict) else c
        for c in subject.components
    ]
    components = [c for c in subject.components if c.name.lower() != component_name.lower()]
    action = "updated" if any(c.name.lower() == component_name.lower() for c in subject.components) else "added"

    new_comp = AssessmentComponent(
        name=component_name,
        weight_percent=weight_percent,
        score_obtained=score_obtained,
        max_score=max_score,
    )
    components.append(new_comp)

    total_weight = sum(c.weight_percent for c in components)
    remaining = round(100.0 - total_weight, 4)

    if abs(total_weight - 100.0) < 0.01:
        weight_note = "✅ Weights now sum to 100% — ready to calculate grade."
    elif total_weight < 100.0:
        weight_note = f"ℹ️  Total weight is now {total_weight:.1f}%. {remaining:.1f}% remaining."
    else:
        weight_note = f"❌ Total weight is {total_weight:.1f}% — exceeds 100%. Please adjust."

    message = (
        f"✅ Component '{component_name}' {action} for '{subject.subject_name}'. "
        f"Score: {score_obtained}/{max_score} at {weight_percent}% weight. {weight_note}"
    )

    return ComponentUpdateResult(
        subject_name=subject.subject_name,
        action=action,
        component_name=component_name,
        updated_components=components,
        current_total_weight=round(total_weight, 4),
        message=message,
    )


@tool(permission=ToolPermission.WRITE_ONLY)
def Engingers_remove_component(
    subject: Subject,
    component_name: str,
) -> ComponentUpdateResult:
    """Remove an assessment component from a subject by name.

    Use this when the student wants to delete an entry they no longer need.

    Args:
        subject (Subject): The subject to modify with its current components.
        component_name (str): Exact name of the component to remove (case-insensitive).
    Returns:
        ComponentUpdateResult: Updated components list, new total weight, and a confirmation message.
    """
    if isinstance(subject, dict):
        subject = Subject(**subject)
    subject.components = [
        AssessmentComponent(**c) if isinstance(c, dict) else c
        for c in subject.components
    ]
    original_count = len(subject.components)
    components = [c for c in subject.components if c.name.lower() != component_name.lower()]

    if len(components) == original_count:
        message = (
            f"⚠️  No component named '{component_name}' was found in '{subject.subject_name}'. "
            "Please check the name and try again."
        )
        action = "not_found"
    else:
        total_weight = sum(c.weight_percent for c in components)
        remaining = round(100.0 - total_weight, 4)
        message = (
            f"🗑️  Component '{component_name}' removed from '{subject.subject_name}'. "
            f"Total weight is now {total_weight:.1f}% ({remaining:.1f}% remaining)."
        )
        action = "removed"

    total_weight = sum(c.weight_percent for c in components)
    return ComponentUpdateResult(
        subject_name=subject.subject_name,
        action=action,
        component_name=component_name,
        updated_components=components,
        current_total_weight=round(total_weight, 4),
        message=message,
    )


@tool(permission=ToolPermission.READ_ONLY)
def Engingers_review_subject_summary(subject: Subject) -> dict:
    """Display a full summary of a subject's assessment components, current weights, and a grade preview.

    Use this whenever the student asks to review, view, or check their entered data for a subject.

    Args:
        subject (Subject): The subject to summarise.
    Returns:
        dict: Formatted summary including all components, weight totals, and a grade preview if weights are complete.
    """
    if isinstance(subject, dict):
        subject = Subject(**subject)
    subject.components = [
        AssessmentComponent(**c) if isinstance(c, dict) else c
        for c in subject.components
    ]
    total_weight = sum(c.weight_percent for c in subject.components)
    remaining = round(100.0 - total_weight, 4)
    is_complete = abs(total_weight - 100.0) < 0.01

    rows = []
    for i, comp in enumerate(subject.components, 1):
        pct = (comp.score_obtained / comp.max_score * 100) if comp.max_score > 0 else 0
        rows.append({
            "no": i,
            "component": comp.name,
            "score": f"{comp.score_obtained} / {comp.max_score}  ({pct:.1f}%)",
            "weight": f"{comp.weight_percent}%",
        })

    preview = None
    if is_complete and subject.components:
        result = _compute_subject_grade(subject)
        preview = {
            "weighted_score": f"{result.weighted_score}%",
            "letter_grade": result.letter_grade,
            "grade_point": result.grade_point,
        }

    weight_status = "✅ Complete (100%)" if is_complete else f"⚠️  {total_weight:.1f}% entered, {remaining:.1f}% remaining"

    return {
        "subject": f"{subject.subject_code} — {subject.subject_name}",
        "credit_hours": subject.credit_hours,
        "components": rows,
        "total_weight": total_weight,
        "weight_status": weight_status,
        "grade_preview": preview if preview else "Add remaining components to see a grade preview.",
    }
