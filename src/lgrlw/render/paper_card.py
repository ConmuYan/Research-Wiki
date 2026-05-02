"""Render the markdown body of a literature paper card."""

from __future__ import annotations

from jinja2 import Environment, StrictUndefined

from lgrlw.schemas import PaperFrontmatter

_PAPER_CARD_TEMPLATE = """\
# {{ fm.title }}

{{ fm.authors | join(', ') }} &middot; {{ fm.year }}{% if fm.venue %} &middot; *{{ fm.venue }}*{% endif %}

{% if fm.doi %}DOI: [{{ fm.doi }}](https://doi.org/{{ fm.doi }})  {% endif %}
{% if fm.arxiv_id %}arXiv: [{{ fm.arxiv_id }}](https://arxiv.org/abs/{{ fm.arxiv_id }})  {% endif %}
{% if fm.url %}URL: <{{ fm.url }}>  {% endif %}

---

## Summary

<!-- One paragraph summary of what the paper actually argues. -->

## Claims

<!-- 1-3 bullet claims, phrased as "the paper argues ...", each linked to
     a specific section / figure / table in the paper. -->

## Methods

<!-- Core methods. Link to literature-kb/04_Concepts/Methods/ when a method
     concept page exists. Do not describe *your own* method here. -->

## Results

<!-- The paper's own reported results. Do not mix in your reproduction
     numbers or ablations; those belong in a workspace. -->

## Related Work (within this KB)

<!-- Links to other papers already in literature-kb/02_Literature/Papers/.
     No workspace links allowed. -->

## Notes

<!-- Your reading notes on this paper. If these notes outgrow the card and
     turn into a research direction, move them into a workspace via
     `lgrlw new-workspace`. -->
"""


def render_paper_card(fm: PaperFrontmatter) -> str:
    """Return the markdown body for a paper card given its frontmatter."""
    env = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        undefined=StrictUndefined,
    )
    template = env.from_string(_PAPER_CARD_TEMPLATE)
    return template.render(fm=fm)


__all__ = ["render_paper_card"]
