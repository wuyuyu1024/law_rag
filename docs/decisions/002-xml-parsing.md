# ADR 002: XML Parsing with lxml

## Context

The corpus starts with Dutch law XML and Rechtspraak XML. Legal text is highly structured and must be parsed without losing hierarchy, titles, article numbers, or case-law sections.

## Decision

Use `lxml` for XML parsing in ingestion and legal-aware chunking.

## Why

- The project needs more robust XML handling than a minimal parser provides.
- `lxml` supports stronger XPath-style querying, namespace handling, and more production-grade XML processing.
- The chunkers re-open source XML during legal-aware chunking, so parser robustness matters beyond ingestion.

## Alternatives Considered

### `xml.etree.ElementTree`

Rejected as the primary parser.

Reason:
- It was fine for the scaffold phase.
- It is lighter, but it offers a weaker XML toolset for the kind of structured parsing this domain needs.

### Generic document loaders

Rejected.

Reason:
- The assignment is explicitly about preserving legal hierarchy.
- Generic loaders hide too much of the structure needed for legal citations.

## Tradeoffs

- `lxml` introduces a compiled dependency.
- The code still needs legal-domain parsing logic; the library removes XML plumbing, not domain reasoning.

## Consequences

- XML parsing is more robust and extensible.
- The system is better positioned for richer XPath-based extraction later.
- The design is easier to justify because the XML library choice matches the structure-heavy nature of the corpus.
