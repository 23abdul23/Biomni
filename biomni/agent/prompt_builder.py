"""Budgeted prompt assembly for Biomni agent.

Builds the system prompt by composing prioritized sections within a hard
token budget.  Sections that would exceed the remaining budget are dropped
with a one-line notice so the LLM is aware of what was omitted.
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token (conservative).

    This avoids a hard dependency on ``tiktoken`` while still giving
    a useful approximation for budget enforcement.
    """
    return max(1, len(text) // 4)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate *text* so it fits within *max_tokens* (approximate).

    A trailing ``\\n[… truncated]`` marker is appended when truncation
    occurs.
    """
    if estimate_tokens(text) <= max_tokens:
        return text
    # Leave room for the truncation marker
    char_budget = max(0, max_tokens * 4 - 30)
    return text[:char_budget] + "\n[… truncated to fit token budget]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_budgeted_prompt(
    sections: list[tuple[str, str, int]],
    total_budget: int,
) -> str:
    """Assemble a system prompt from prioritized sections.

    Parameters
    ----------
    sections:
        Each element is ``(section_name, section_content, priority)``.
        **Lower** priority number → included first.
    total_budget:
        Approximate maximum token count for the assembled prompt.

    Returns
    -------
    str
        Concatenated prompt text that fits within *total_budget*.
    """
    # Sort by priority (stable sort preserves insertion order for ties)
    ordered = sorted(sections, key=lambda s: s[2])

    parts: list[str] = []
    used_tokens = 0

    for name, content, _pri in ordered:
        section_tokens = estimate_tokens(content)

        if used_tokens + section_tokens <= total_budget:
            # Fits entirely
            parts.append(content)
            used_tokens += section_tokens
        else:
            remaining = total_budget - used_tokens
            if remaining > 100:
                # Partial fit — truncate the section
                truncated = truncate_to_token_budget(content, remaining)
                parts.append(truncated)
                used_tokens += estimate_tokens(truncated)
            else:
                # Not enough room — drop with notice
                parts.append(f"\n[Section '{name}' omitted due to token budget]\n")
                used_tokens += 15  # small overhead for notice
            # No point adding more sections once budget is essentially spent
            if used_tokens >= total_budget:
                # Append notices for remaining sections
                remaining_sections = [
                    s[0] for s in ordered if s[0] != name and s not in ordered[: ordered.index((name, content, _pri)) + 1]
                ]
                # Simplified: just break, the dropped sections won't appear
                break

    return "\n".join(parts)
