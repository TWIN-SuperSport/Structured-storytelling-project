# Structured-storytelling-project

Through conceptual storytelling, the plot and characters are created by working backward from the story's ending to establish the underlying premises.

This repository is for designing a structured storytelling workflow that:

1. reverse-engineers a story from ending conditions back to its earliest premises,
2. stores the canonical structure as JSON,
3. generates a human-readable plot in Markdown,
4. feeds that plot text into a fragment-linking app for scene and prose expansion.

## Current Structure

- `docs/specs/`: concrete specs for individual tools
- `draft/discussion/`: working discussion memos
- `reverse-plot-tool/`: deployable prototype for reverse plot generation

## Current Goal

Build a process where the story's canonical source is structured data, and Markdown plot documents are derived views for human review and downstream writing workflows.

## reverse-plot-tool

`reverse-plot-tool` is the first deployable child service under this repository.

- input: ending / final condition, protagonist hint, genre hint
- output: structured story JSON with plot skeleton
- deploy target: `ktsys-lab`
- current branch for active work: `ayano-dev`

## CI/CD

GitHub Actions are expected to handle:

- CI: syntax / compose validation for `reverse-plot-tool`
- CD: deploy `reverse-plot-tool` to `ktsys-lab` on push to `ayano-dev`
