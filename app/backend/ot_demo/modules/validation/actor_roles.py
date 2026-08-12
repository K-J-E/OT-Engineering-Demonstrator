"""Single controlled local actor/role authority for validation assurance."""

from __future__ import annotations


CONTROLLED_LOCAL_ACTOR_ROLES: dict[str, str] = {
    "graduate-engineer": "GRADUATE_ENGINEER",
    "independent-reviewer": "INDEPENDENT_ENGINEERING_REVIEWER",
    "backend-integrity-monitor": "BACKEND_ASSURANCE_PROPOSER",
    "backend-assurance-reviewer": "BACKEND_ASSURANCE_REVIEWER",
}


def controlled_actor_role(actor_id: str) -> str | None:
    """Resolve one identity through the accepted local validation role registry."""

    return CONTROLLED_LOCAL_ACTOR_ROLES.get(actor_id)
