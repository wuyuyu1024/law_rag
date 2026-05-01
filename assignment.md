# Technical Assessment: Enterprise RAG Architecture for the Tax Authority

## 1. The Scenario

The National Tax Authority is developing a secure, internal AI assistant for its employees, including tax inspectors, legal counsel, and helpdesk staff. The system must flawlessly answer complex fiscal questions based on a massive corpus of **500,000 documents**.

### Corpus

The corpus includes:

- **Legislation & Regulations**  
  Hierarchical legal texts, including historical and current versions.

- **Case Law & Jurisprudence**  
  Dense, complex court rulings and verdicts.

- **Internal Policy Guidelines**  
  Operational manuals and memos.

- **E-learning**  
  Training modules and internal wikis.

### Strict System Constraints

- **Zero-Hallucination Tolerance**  
  Fiscal advice must be 100% factually accurate. Every claim must include an exact citation, including:
  - Document name
  - Article
  - Paragraph

- **Security & Access Control**  
  Strict Role-Based Access Control, or RBAC. A helpdesk employee must not be able to retrieve or generate answers based on classified fraud-investigation, or FIOD, documents.

- **High Performance at Scale**  
  The system will process tens of millions of vector chunks. Time-to-First-Token, or TTFT, must remain low, under **1.5 seconds**, despite the scale.

---

## 2. The Assignment

As the Lead AI Engineer, you are tasked with designing the architecture and specifying the exact configurations for this system.

Please detail your design for the following four modules. Provide:

- Conceptual architecture
- Specific configuration parameters
- Pseudo-code where applicable

Your design should be concrete enough that a DevOps or AI engineering team can immediately begin implementation.

---

# Module 1: Ingestion & Knowledge Structuring

## Data Pipeline

Standard recursive text splitters destroy the hierarchical context of legal documents.

### Chunking Strategy

Design a chunking strategy specifically for legal codes and case law.

Address the following:

- How do you ensure the LLM knows a chunk belongs to **"Article 3.114, Paragraph 2"**?
- Provide a brief pseudo-code or configuration example, for example using LlamaIndex or LangChain, showing how metadata is preserved.

### Vector Database & Scale

Which vector database do you select for **500,000 documents**, potentially **20M+ chunks**?

Specify:

- Exact index configurations, for example:
  - HNSW parameter `m`
  - HNSW parameter `ef_construct`
- Memory optimization techniques, for example:
  - Quantization
- How you would prevent:
  - Out-of-Memory errors
  - Latency spikes

---

# Module 2: Retrieval Strategy

## High Precision

Queries will contain a mix of exact matches and semantic concepts.

Examples:

- Exact match: `"Ruling ECLI:NL:HR:2023:123"`
- Semantic concept: `"deductibility of home office expenses"`

### Hybrid Search

Design the retrieval query.

Address the following:

- How do you combine sparse retrieval, such as BM25 or keyword search, with dense vector retrieval?
- What weighting or fusion strategy do you advise for this legal domain?
  - Example: alpha values
  - Example: Reciprocal Rank Fusion, or RRF
- Why is this strategy suitable for legal search?

### Reranking

To maintain precision without sacrificing latency:

- Which reranking strategy or model do you implement?
  - Example: Cross-Encoder
  - Example: Cohere reranker
- Specify the Top-K parameters for:
  - Initial retrieval
  - Final reranker output

---

# Module 3: Agentic RAG & Self-Healing

## Generation

Standard linear RAG pipelines are fragile. If retrieval fails, the LLM hallucinates.

### Query Transformation

Describe how you handle complex, multi-part tax questions using techniques such as:

- Query Decomposition
- HyDE, or Hypothetical Document Embeddings

### Corrective RAG, or CRAG, Implementation

Design a state machine, or control loop, using a framework such as LangGraph.

Address the following:

- How do you implement a Retrieval Evaluator, or Grader?
- Define the exact fallback actions the system takes if the retrieved context is classified as:
  - `Irrelevant`
  - `Ambiguous`
  - `Relevant`

---

# Module 4: Production Ops, Security & Evaluation

## Semantic Caching

To reduce costs and latency for FAQs, such as:

> What is the Box 1 tax rate for 2024?

Design a Semantic Cache, for example using Redis.

Address the following:

- What cosine similarity threshold is safe for financial or tax data?
- How do you prevent stale or incorrect cached answers?

### Database-Level Security

Explain exactly how you implement RBAC to ensure unauthorized users cannot access classified documents.

Crucially:

- At what stage of the RAG pipeline must this filtering occur to prevent data leaks mathematically?

### CI/CD & Observability

Before deploying a new embedding model or LLM to production:

- How do you automatically evaluate the system?
- Specify the exact metrics, for example via DeepEval or Ragas, that you would track for:
  - Faithfulness
  - Context Precision