# Overview

Worked example: the research direction covered here is
**retrieval-augmented generation (RAG)** for knowledge-intensive NLP
tasks.

## Scope

In scope: parametric + non-parametric NLP systems that answer or
generate text by retrieving from an external corpus at inference or
training time. Adjacent: long-context language models, tool-use agents,
open-domain QA without retrieval.

## Core questions

- How should a generator consume retrieved passages: as prefix, as
  cross-attention input, or via an explicit critique/decoding step?
- How are retrievers trained, and how tightly must they be coupled to
  the generator?
- When and why does retrieval help vs. hurt generation quality?
- How should a RAG system report its sources (attribution)?

## Entry-point papers

- [Lewis et al., 2020 -- RAG for knowledge-intensive NLP](../02_Literature/Papers/lewis-2020-retrieval-augmented-generation-for-knowledge-inte.md)
  &mdash; the original RAG architecture (parametric + non-parametric).
- [Karpukhin et al., 2020 -- Dense Passage Retrieval](../02_Literature/Papers/karpukhin-2020-dense-passage-retrieval-for-open-domain-quest.md)
  &mdash; the dense-retrieval substrate most RAG systems build on.
- [Asai et al., 2023 -- Self-RAG](../02_Literature/Papers/asai-2023-self-rag-learning-to-retrieve-generate-and-critiqu.md)
  &mdash; a self-reflective / critique-aware RAG variant.

## See also

- [Problem evolution](./Problem_Evolution.md)
- [Method taxonomy](./Method_Taxonomy.md)
- [Timeline](./Timeline.md)
