# Promotion checklist

Pre-flight checklist for `lgrlw promote` (v0.2). Tick every box (`- [ ]`
&rarr; `- [x]`) before invoking the command. `lgrlw promote` parses this
file: any remaining `- [ ]` aborts the run with a non-zero exit code,
and a checklist with no `- [x]` lines is treated as missing.

- [ ] `paper_status.md` frontmatter has `status: accepted`.
- [ ] `paper_status.md` frontmatter has non-null `final_title`,
      `final_authors`, `venue`, `year`.
- [ ] `paper_status.md` frontmatter has at least one of `doi` or
      `arxiv_id`.
- [ ] `06_Promotion/final_metadata.md` references the camera-ready
      PDF path or public-version URL.
- [ ] `06_Promotion/final_metadata.md` contains the camera-ready
      BibTeX entry (the auto-generated `01_Raw/bibtex/<id>.bib` will
      be a baseline; replace it post-promotion if you have a better
      one).
- [ ] `06_Promotion/add_back_to_kb_plan.md` lists the intended
      field-structure / evidence-map / method-taxonomy edits as `- `
      bullets. `lgrlw promote` does *not* apply them automatically;
      it will remind you to commit them as a follow-up.
- [ ] Claims to lift into KB are identified and marked accepted-only.
- [ ] Taxonomy impact has been reviewed end-to-end.

