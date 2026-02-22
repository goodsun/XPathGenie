# XPathGenie: LLM-Driven Automated XPath Generation with Multi-Page Validation and Two-Tier Refinement

**Author:** Chikara Kawashima  
**ORCID:** 0009-0008-9457-0181  
**Institution:** Independent Researcher  
**Date:** February 2026

---

## Abstract

We present XPathGenie, a novel system that automates XPath mapping generation from raw URLs using HTML structural compression (~97% reduction), large language model (LLM)-based inference, multi-page validation, and two-tier refinement. Unlike per-page LLM extraction systems, XPathGenie invokes AI exactly once to generate reusable XPath expressions, ensuring zero marginal AI cost per page extraction. Our evaluation across 23 medical job-listing websites achieved 85.1–87.3% field-level hit rate—deliberately measuring structural extraction stability rather than semantic accuracy, as our primary objective is reusable XPath generation rather than value extraction benchmarking—with 11 sites achieving 100% accuracy. Supplementary cross-domain evaluation on 10 sites across 5 non-medical domains (e-commerce, real estate, recipe platforms, restaurant reviews, news) achieved a macro-average hit rate of 79.4%, confirming domain generalizability. An additional English-language evaluation on 10 sites across 10 domains achieved a macro-average hit rate of 78.7% among successful sites, providing preliminary evidence of cross-linguistic applicability. Core-field analysis reveals that schema-guided extraction primarily expands coverage (+13.1pp) over open-ended discovery. Zero-shot evaluation on a subset of the SWDE benchmark (22 sites, 8 verticals, 220 pages) achieved F1 = 0.689 on fields where XPaths were successfully generated, with 60% of detected fields achieving perfect F1 = 1.0. The primary bottleneck is field discovery coverage (46%) rather than extraction accuracy, contrasting with supervised systems like AXE (F1 88.1%) that benefit from labeled training data. We identify the compression-generation gap—a systematic mismatch between compressed and raw HTML whitespace handling—resolved via `normalize-space()` predicates.

## 1. Introduction

Structured data extraction from websites constitutes a fundamental component of competitive intelligence, job aggregation, price monitoring, and numerous data-driven applications. At the core of most extraction pipelines lies XPath—a query language for selecting nodes from HTML/XML documents. Despite its expressive power, XPath authoring remains a predominantly manual craft requiring substantial domain expertise.

The challenges are threefold. First, **temporal cost**: constructing a reliable XPath mapping for a single website typically requires several hours of expert effort, involving page inspection, expression writing, edge-case handling, and cross-page validation. For organizations managing portfolios of dozens of target sites, this translates to hundreds of hours of specialized labor. Second, **tacit knowledge dependency**: effective XPath construction requires deep understanding of common HTML patterns (definition lists, table layouts, nested containers), site-specific idiosyncrasies, and the distinction between primary content and peripheral elements such as sidebars and recommendation widgets. This knowledge is difficult to systematize and transfer. Third, **scalability constraints**: as target sites evolve their HTML structures through redesigns or framework updates, previously valid XPaths become obsolete, necessitating ongoing maintenance that scales linearly with portfolio size.

This work does not attempt to eliminate human judgment entirely, but rather to reposition it as a sparse and structured intervention within an otherwise automated pipeline. XPathGenie addresses these challenges by reformulating XPath generation as an LLM inference problem operating on structurally compressed HTML, augmented by deterministic validation and refinement stages. The key architectural insight is that AI should be invoked exactly once—for initial mapping discovery—while all subsequent operations (validation, mechanical refinement, ongoing extraction) operate purely on DOM manipulation at zero marginal AI cost. Our evaluation measures structural extraction stability (whether XPaths consistently return non-empty values across pages) rather than semantic correctness against ground-truth labels; human verification via the companion tool Aladdin is recommended for production deployment.

This paper makes three primary contributions:

1. **A zero-marginal-cost XPath generation pipeline** combining HTML structural compression (~97% token reduction), LLM-based inference, multi-page validation, and two-tier refinement (mechanical narrowing at zero AI cost + targeted AI re-inference). The system invokes AI once per site; all subsequent extraction operates deterministically.

2. **An escalation-based human-in-the-loop architecture** (Genie–Jasmine–Aladdin) that optimally distributes cognitive labor between AI and humans: automated generation handles 87% of sites, while the interactive Jasmine tool provides single-click escalation for the remaining 13%, and Aladdin enables bulk verification workflows.

3. **Multi-faceted evaluation spanning 62 websites across 2 languages, 15+ domains, and 3 evaluation paradigms**: structural stability (hit rate 85–87% on 23 production sites), semantic accuracy (95.0% on 100 manually judged samples), and ground-truth F1 (0.689 on 22 SWDE benchmark sites in zero-shot setting), establishing both practical reliability and comparability with supervised baselines.

Additionally, we identify and resolve the **compression-generation gap**—a systematic mismatch between whitespace-normalized compressed HTML and raw-HTML execution contexts—via strategic adoption of `normalize-space()` predicates in generated XPaths.

## 2. Related Work

Automated web data extraction has been extensively studied across multiple research communities, yielding several distinct families of approaches. We organize prior work into five primary categories and position XPathGenie within this landscape.

### 2.1 Visual Scraping and CSS Selector Tools

**Visual scraping tools** (e.g., Octoparse, ParseHub, Import.io) provide point-and-click interfaces enabling users to visually select target elements through browser interaction. While these tools reduce the barrier to XPath syntax knowledge, they still require manual element selection per field and per site, offering limited automation of the mapping discovery process itself. **CSS selector generators** (e.g., SelectorGadget, browser DevTools) automatically suggest selectors for clicked elements but operate on single elements and single pages, lacking cross-page generalization capabilities and batch field discovery mechanisms.

### 2.2 Wrapper Induction

Wrapper induction systems learn extraction rules from labeled examples through supervised machine learning. Seminal work by Kushmerick et al. (1997) and Dalvi et al. (2011) established the paradigm of learning extraction patterns from annotated page sets. More recently, commercial systems such as **Diffbot** (Tong, 2014) and **Zyte Automatic Extraction** (formerly AutoExtract) apply machine learning techniques to extract structured data without explicit rule authoring. These systems achieve strong performance on common page types (articles, products) but rely on pre-trained models for specific verticals and may struggle with niche or unconventional layouts.

### 2.3 HTML-Aware Language Models

A family of language models has been specifically developed for HTML/DOM structure understanding. **MarkupLM** (Li et al., 2022) extends pre-trained language models with XPath-based position embeddings, enabling tasks such as web page classification and information extraction from semi-structured documents. **WebFormer** (Wang et al., 2022) proposes a Transformer architecture that models relationships between HTML tokens and DOM structure for enhanced web page understanding. **DOM-LM** (Deng et al., 2022) pre-trains on DOM trees with structure-aware objectives. These models demonstrate that explicit HTML structure encoding improves downstream extraction tasks, but they typically require fine-tuning on labeled data for each target schema.

### 2.4 LLM-Based Web Extraction

The emergence of large language models has enabled novel approaches to web data extraction. **ScrapeGraphAI** (Perini et al., 2024) orchestrates LLM calls through a graph-based pipeline to extract structured data from web pages, supporting multiple LLM backends. However, ScrapeGraphAI invokes the LLM at extraction time for each individual page, resulting in AI costs that scale linearly with the number of pages processed. In contrast, XPathGenie employs the LLM solely for generating reusable XPath expressions, incurring AI costs only once per site mapping.

**Zero-shot extraction** approaches apply LLMs to extract structured data without task-specific training. Lockard et al. (2020) demonstrated zero-shot closed information extraction from semi-structured web pages (ZeroShotCeres). More recent work has explored using LLMs to generate CSS selectors or XPath expressions from natural-language descriptions of desired fields (Gur et al., 2023; Zhou et al., 2024), though these typically operate on single pages without cross-page validation mechanisms.

Open-source crawling frameworks such as **FireCrawl** (2024) and **crawl4ai** (2024) convert web pages to LLM-friendly formats (Markdown, structured text) for downstream extraction. These tools focus on content conversion rather than reusable selector generation, invoking LLMs per page during the extraction phase.

Several systems have specifically targeted LLM-driven XPath generation. **XPath Agent** (arXiv:2502.15688, 2024) employs a two-stage approach where a lightweight LLM extracts candidate elements and a stronger LLM constructs XPath expressions from multiple sample pages and natural-language queries. **Automatic XPath generation for vertical websites** (Huang & Song, 2025) decomposes XPath generation into multi-task sub-problems, learning robust expressions from seed pages for vertical domains. **AXE (Adaptive X-Path Extractor)** (arXiv:2602.01838, 2026) applies aggressive DOM pruning achieving 97.9% token reduction, enabling a 0.6B parameter model to achieve F1 88.1% on the SWDE benchmark with Grounded XPath Resolution (GXR) for traceable extraction.

### 2.5 Boilerplate Detection and Content Extraction

Content extraction from web pages has a substantial research history. Kohlschütter et al. (2010) proposed boilerplate detection using shallow text features, achieving effective separation of main content from peripheral elements. XPathGenie's HTML compression pipeline draws on similar intuitions—identifying and removing non-content elements—but operates at the DOM structural level to preserve the hierarchical information necessary for XPath construction.

### 2.6 Positioning and Differentiation

XPathGenie differs fundamentally from all prior approaches in a critical architectural decision: the LLM generates *reusable XPath expressions*, not extracted data values. This design ensures AI costs are incurred once at mapping time, with all subsequent extractions consisting of deterministic DOM queries—fast, reliable, and cost-free. The HTML compression pipeline further distinguishes our approach by enabling LLM analysis within practical token budgets without requiring model fine-tuning.

Compared to the most recent LLM-based XPath systems, XPathGenie's key differentiators include: (1) **zero post-generation AI cost**—XPath Agent and AXE may invoke LLMs during extraction or agent execution, while XPathGenie's output consists purely of deterministic `lxml.xpath()` calls; (2) **multi-page cross-validation with two-tier refinement**—mechanical narrowing resolves identical-value multi-matches at zero cost, with AI re-inference reserved for genuinely ambiguous cases; (3) **different evaluation paradigms**—AXE operates in a supervised setting with labeled training data, while XPathGenie operates in a zero-shot setting; and (4) **structure-preserving compression**—unlike AXE's aggressive node pruning, XPathGenie's compression retains DOM hierarchy essential for XPath construction.

## 3. Methodology

XPathGenie implements a six-stage pipeline from URL input to validated XPath mappings, followed by optional human-in-the-loop verification via the companion tool Aladdin.

### 3.1 HTML Compression

Raw HTML pages from modern websites routinely exceed 500 KB, far exceeding practical LLM context windows when multiple pages must be analyzed simultaneously. The compression module applies multi-pass structural reduction:

1. **Tag removal**: Elements containing no extractable content are eliminated: `script`, `style`, `noscript`, `iframe`, `svg`, `link`, `meta`, and `head`.

2. **Structural strip**: Layout-only containers (`header`, `footer`, `nav`, `aside`) are removed as they rarely contain target data fields.

3. **Noise pre-removal**: Before main section detection, subtrees matching noise patterns are removed. Noise patterns target class or ID attributes containing: `recommend|related|sidebar|widget|breadcrumb|modal|slide|footer|banner|ad[-_]|popup|cookie|privacy|policy|inquiry|contact|sns[-_]|share`.

4. **Main section detection**: The algorithm locates primary content through three-tier fallback: (a) explicit semantic elements (`<main>`, `<article>`), (b) structured data detection—scoring candidate containers by the product of structured marker count (number of `<th>` and `<dt>` descendants) and text content length, and (c) the container with maximum text content.

5. **Residual noise removal**: Within the identified main section, remaining child subtrees matching noise patterns are recursively eliminated.

6. **Text truncation**: All text nodes are truncated to 30 characters, preserving structural labels while eliminating lengthy content.

7. **Empty element pruning**: Elements with no text content and no children are removed.

8. **Whitespace normalization**: Redundant whitespace is collapsed and inter-tag whitespace is eliminated.

This process achieves approximately 97% size reduction (e.g., 695 KB → 20 KB) while preserving DOM hierarchy, class names, and label text essential for XPath construction.

### 3.2 LLM-Based XPath Generation

The system offers two inference modes, both implemented as single-call prompts to Gemini 2.5 Flash with `temperature=0.1` and `responseMimeType=application/json`:

**Auto Discover mode** sends compressed HTML samples with instructions to identify all meaningful data fields and return a JSON mapping of field names to XPath expressions. The prompt enforces constraints critical for downstream reliability:

- XPaths must use `//` prefix and select element nodes
- Class matching must use `contains(@class, ...)` for multi-class attributes
- Text matching must use `normalize-space()` for whitespace resilience
- XPath functions beyond `contains()` and `normalize-space()` are prohibited
- Output limited to 20 most important fields
- Field names must be lowercase English and semantically generic

**Want List mode** accepts user-provided JSON schema where keys are desired field names and values are natural-language descriptions. The LLM matches fields by semantic meaning rather than literal label text, enabling cross-language semantic matching.

After LLM response, automatic root prefixing inspects the first compressed HTML's root element for meaningful class names, prepending them to all generated XPaths as scoping containers.

### 3.3 Multi-Page Validation

Generated XPaths are evaluated against original (uncompressed) HTML of every fetched page. For each field, the validator computes:

- **Confidence score**: Fraction of pages where XPath returns at least one non-empty result
- **Sample values**: First 100 characters of extracted text from each page
- **Multi-match warnings**: Fields where XPath matches more than one DOM node

When multiple nodes match, the validator selects the best match using depth-weighted content scoring that combines structural signals with DOM depth preferences.

### 3.4 Two-Tier Refinement

XPathGenie addresses multi-match scenarios through a two-tier strategy:

**Tier 1: Mechanical narrowing (zero AI cost)** When all matched values are identical, the system performs deterministic DOM analysis, traversing ancestor chains for elements with class attributes and constructing candidate XPaths by inserting intermediate container selectors.

**Tier 2: AI re-inference (contextual refinement)** When matched values differ, the system sends surrounding HTML context back to the LLM with a refinement prompt to identify the primary match and return a more specific XPath.

### 3.5 Human-in-the-Loop Verification

The companion tool **XPathAladdin** provides:
- 10-page bulk testing with tabbed comparison interface
- Cross-page hit rate visualization
- Real-time XPath editing with immediate re-evaluation
- Seamless handoff from XPathGenie via localStorage
- JSON/YAML export compatibility with crawling frameworks

## 4. Evaluation

### 4.1 Experimental Design

XPathGenie was evaluated on 35 Japanese medical/healthcare job-listing websites, with 23 having accessible server-side rendered pages. Additional evaluations included cross-domain assessment (10 websites across 5 non-medical domains), English-language evaluation (10 sites across 10 domains), and SWDE benchmark comparison (22 sites across 8 verticals).

Three evaluation metrics were employed:
1. **Field-level hit rate**: Fraction of pages returning non-empty XPath results
2. **Site-level average hit rate**: Mean field-level hit rates per site  
3. **Core field hit rate**: Performance on universally present fields (salary, location, employment type, etc.)

### 4.2 Results

**Primary Evaluation (23 Japanese Medical Sites):**
- Auto Discover mode: 85.1% field-level hit rate (298/350 perfect fields)
- Want List mode: 87.3% field-level hit rate (337/386 perfect fields)
- 11 sites achieved 100% accuracy in both modes
- Core field hit rate: 89.3% with 75.2% coverage

**Cross-Domain Evaluation (Japanese):**
- Macro-average hit rate: 79.4% across 7 accessible sites
- Perfect performance on SUUMO (real estate) and Cookpad (recipes)
- Failure modes: CSS-in-JS frameworks, bot protection, page-type mismatch

**English-Language Evaluation:**
- Macro-average hit rate: 78.7% across 7 successful sites
- Perfect performance on GitHub and Quotes to Scrape
- StackOverflow achieved 86% with comprehensive field discovery

**SWDE Benchmark Evaluation:**
- F1 = 0.689 on successfully detected fields (strict F1 = 0.317 including undetected)
- Field detection coverage: 46% (40/87 target fields)
- 60% of detected fields achieved perfect F1 = 1.0
- Primary limitation: field discovery rather than extraction accuracy

### 4.3 Failure Analysis

Three primary failure modes were identified:

1. **Compression-generation gap**: Whitespace normalization mismatches between compressed HTML analyzed by LLM and raw HTML during execution, resolved via `normalize-space()` predicates

2. **CSS framework compatibility**: Sites using utility-class frameworks (Tailwind CSS) or CSS-in-JS produce non-semantic class names, reducing structural anchors for XPath generation  

3. **Single-Page Application limitations**: JavaScript-rendered content appears as minimal HTML shells, requiring headless browser integration

### 4.4 Reproducibility

Multi-run evaluation on 21 sites showed:
- 38% perfectly stable (σ = 0)
- 38% stable with minor variation (0 < σ < 0.05)  
- Overall mean hit rate: 83.1% across runs
- Instability correlated with non-standard HTML structures

## 5. Design Principles

### 5.1 Intent Communication Over Constraint Specification

XPathGenie's prompt engineering emphasizes communicating *why* constraints exist rather than merely specifying *what* they are. For example, the instruction to use `contains(@class, ...)` is accompanied by the explanation "because classes often have multiple values." This approach enables the LLM to understand underlying principles and adapt to novel situations.

### 5.2 Role Reversal in Human-AI Collaboration

Traditional web scraping workflow assigns XPath creation to humans and execution to machines. XPathGenie inverts this relationship: machines generate XPaths through LLM inference, while humans verify extracted values through Aladdin's visual interface. This leverages human pattern recognition strengths while automating systematic code generation.

### 5.3 Cost Optimization Through Single-Inference Architecture

XPathGenie's most significant architectural decision is invoking the LLM exactly once per site mapping. The output consists of reusable XPath expressions—deterministic, portable, and executable without AI infrastructure. For a site with *n* pages, traditional per-page extraction incurs *O(n)* AI costs, while XPathGenie maintains *O(1)* AI cost plus *O(n)* deterministic DOM queries at zero marginal cost.

## 6. Limitations and Future Directions

**Single-Page Application Support**: Current HTTP-based fetching cannot handle JavaScript-rendered content. Integration with headless browsers would enable SPA compatibility.

**Site Evolution Robustness**: Generated XPaths are tied to DOM structure at analysis time. Periodic re-analysis or change detection mechanisms would improve production durability.

**CSS Framework Compatibility**: Utility-class frameworks reduce semantic structure available for XPath anchoring. Adaptive compression preserving wrapper structure could improve performance.

**Model Dependency**: Evaluation employed Gemini 2.5 Flash exclusively. While architectural principles suggest portability to other capable LLMs, empirical validation across models remains incomplete.

**Ground Truth Limitations**: Primary evaluation measures extraction coverage rather than semantic accuracy. Expanded ground-truth comparison would strengthen accuracy claims.

## 7. Conclusion

XPathGenie demonstrates that LLM-based XPath generation, combined with aggressive HTML compression, deterministic multi-page validation, and two-tier refinement, achieves reliable extraction coverage across diverse production websites. Field-level hit rates of 85.1–87.3% across 23 medical job-listing sites, with cross-domain validation achieving 79.4% macro-average across 5 additional domains and cross-linguistic validation achieving 78.7% across English sites, establish practical viability while identifying clear boundaries of applicability.

The system's architectural insight—using AI for one-time mapping discovery rather than per-page extraction—ensures zero marginal operational costs after initial generation. The three-tool ecosystem (Genie for generation, Jasmine for section selection, Aladdin for verification) distributes cognitive labor optimally: AI handles systematic pattern matching and code generation, while humans provide semantic recognition and quality judgment.

Key technical contributions include resolution of the compression-generation gap through strategic `normalize-space()` adoption, demonstration of zero-shot competitive performance on SWDE benchmark subset (F1 = 0.689 on detected fields vs. supervised AXE F1 = 88.1%), and establishment of escalation-based human-in-the-loop architecture requiring intervention on only 13% of sites.

Future work should prioritize JavaScript rendering support for SPA compatibility, adaptive compression for CSS framework sites, and expanded multi-model validation. The fundamental paradigm—LLM-generated reusable extractors with deterministic execution—provides a scalable foundation for automated web data extraction across diverse domains and languages.

---

## References

1. Clark, J., & DeRose, S. (1999). XML Path Language (XPath) Version 1.0. W3C Recommendation.

2. Dalvi, N., Kumar, R., & Soliman, M. (2011). Automatic wrappers for large scale web extraction. Proceedings of the VLDB Endowment, 4(4), 219-230.

3. Deng, X., Sun, Y., Galley, M., & Gao, J. (2022). DOM-LM: Learning generalizable representations for HTML documents. arXiv preprint arXiv:2201.10608.

4. Gur, I., Furuta, H., Huang, A., et al. (2023). A real-world WebAgent with planning, long context understanding, and program synthesis. arXiv preprint arXiv:2307.12856.

5. Hao, Q., Cai, R., Pang, Y., & Zhang, L. (2011). From one tree to a forest: A unified solution for structured web data extraction. Proceedings of the 34th International ACM SIGIR Conference, 775-784.

6. Huang, J., & Song, J. (2025). Automatic XPath generation agents for vertical websites by LLMs. Journal of King Saud University—Computer and Information Sciences.

7. Kohlschütter, C., Fankhauser, P., & Nejdl, W. (2010). Boilerplate detection using shallow text features. Proceedings of the Third ACM International Conference on Web Search and Data Mining, 441-450.

8. Kushmerick, N., Weld, D. S., & Doorenbos, R. (1997). Wrapper induction for information extraction. Proceedings of the 15th International Joint Conference on Artificial Intelligence, 729-735.

9. Li, J., Xu, Y., Cui, L., & Wei, F. (2022). MarkupLM: Pre-training of text and markup language for visually rich document understanding. Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics, 6078-6087.

10. Lockard, C., Dong, X. L., Einolghozati, A., & Shiralkar, P. (2020). ZeroShotCeres: Zero-shot relation extraction from semi-structured webpages. Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics, 8105-8117.

11. Perini, M., Samardzic, L., & Pozzoli, M. (2024). ScrapeGraphAI: A web scraping python library that uses LLM and direct graph logic to create scraping pipelines. arXiv preprint arXiv:2411.13104.

12. Tong, M. (2014). Diffbot: A visual learning agent for the web. Diffbot Technologies.

13. Wang, X., Jiang, Y., Bach, N., et al. (2022). WebFormer: The web-page transformer for structure information extraction. Proceedings of the ACM Web Conference 2022, 3124-3133.

14. XPath Agent. (2024). Multi-sample XPath generation via two-stage LLM pipeline. arXiv preprint arXiv:2502.15688.

15. AXE: Adaptive X-Path Extractor. (2026). DOM pruning for efficient LLM-based XPath extraction with grounded resolution. arXiv preprint arXiv:2602.01838.