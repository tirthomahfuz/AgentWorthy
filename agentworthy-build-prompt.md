# Agentworthy Build Specification

See the uploaded build prompt PDF for the full specification. This file is the canonical reference committed to the repo per the master execution prompt.

## Phase Overview

1. **Phase 1**: Static scan engine + free public scanner
2. **Phase 2**: Auth, dashboard, site management
3. **Phase 3**: Agent simulation engine
4. **Phase 4**: Fix generation
5. **Phase 5**: Billing
6. **Phase 6**: Monitoring and alerts

## Static Check Suite (20 checks)

### A. Discoverability (15)
- robots_agent_access, llms_txt_present, sitemap_present, canonicals_clean

### B. Machine Readability (25)
- ssr_content_ratio, schema_present, schema_correct_type, prices_machine_readable, contact_machine_readable

### C. Actionability (30)
- forms_semantic, cta_reachable, no_blocking_interstitials, critical_widgets_accessible, accessible_names

### D. Trust & Freshness (15)
- https_valid, content_freshness, nap_consistent

### E. Performance (15)
- ttfb, page_weight, pagination_exists

## Scoring

`score = 100 × (pass weights + 0.5 × warn weights) / applicable weights`

Grades: A 90+, B 80+, C 70+, D 60+, F below 60.
