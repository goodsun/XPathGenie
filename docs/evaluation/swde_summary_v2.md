# SWDE Real Dataset Evaluation Results (v2)

**Evaluation Date**: 2026-02-18 17:32:25 UTC
**Duration**: 211.3 seconds

## Dataset Configuration

- **Dataset**: SWDE Real Dataset (W1ndness/SWDE-Dataset)
- **Verticals**: job, book, movie, auto, camera, nbaplayer, restaurant, university (8 total)
- **Sites**: 17 total (2-3 per vertical)
- **Pages per site**: 10 (0000.htm - 0009.htm)
- **Sample pages for XPath generation**: 3 (first 3 pages)

## Overall Results

### Job Vertical

#### monster

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | - | - | - | - | - | - |
| company | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| location | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| date_posted | - | - | - | - | - | - |

**monster Average F1**: 1.0000

#### dice

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| company | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| location | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| date_posted | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |

**dice Average F1**: 1.0000

#### careerbuilder

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | - | - | - | - | - | - |
| company | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| location | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| date_posted | - | - | - | - | - | - |

**careerbuilder Average F1**: 1.0000

**Job Vertical Average F1**: 1.0000

### Book Vertical

#### amazon

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | - | - | - | - | - | - |
| author | - | - | - | - | - | - |
| isbn_13 | - | - | - | - | - | - |
| publisher | 0.0000 | 0.0000 | 0.0000 | 0 | 43 | 10 |
| publication_date | 0.0000 | 0.0000 | 0.0000 | 0 | 37 | 10 |

**amazon Average F1**: 0.0000

#### borders

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 10 |
| author | 0.8696 | 1.0000 | 0.7692 | 10 | 0 | 3 |
| isbn_13 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 10 |
| publisher | 0.7000 | 0.7000 | 0.7000 | 7 | 3 | 3 |
| publication_date | - | - | - | - | - | - |

**borders Average F1**: 0.3924

**Book Vertical Average F1**: 0.1962

### Movie Vertical

- **imdb**: failed (no details)
#### yahoo

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| title | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| director | - | - | - | - | - | - |
| genre | - | - | - | - | - | - |
| mpaa_rating | - | - | - | - | - | - |

**yahoo Average F1**: 1.0000

**Movie Vertical Average F1**: 1.0000

### Auto Vertical

#### aol

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| model | 0.0000 | 0.0000 | 0.0000 | 0 | 10 | 10 |
| price | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| engine | - | - | - | - | - | - |
| fuel_economy | - | - | - | - | - | - |

**aol Average F1**: 0.5000

#### msn

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| model | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| price | - | - | - | - | - | - |
| engine | - | - | - | - | - | - |
| fuel_economy | - | - | - | - | - | - |

**msn Average F1**: 1.0000

#### yahoo

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| model | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| price | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| engine | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| fuel_economy | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |

**yahoo Average F1**: 1.0000

**Auto Vertical Average F1**: 0.8333

### Camera Vertical

- **amazon**: failed (no details)
- **buy**: failed (no details)
#### beachaudio

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| model | 0.1333 | 0.2000 | 0.1000 | 2 | 8 | 18 |
| manufacturer | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 20 |
| price | - | - | - | - | - | - |

**beachaudio Average F1**: 0.0667

**Camera Vertical Average F1**: 0.0667

### Nbaplayer Vertical

#### espn

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 0.0000 | 0.0000 | 0.0000 | 0 | 10 | 10 |
| team | 0.0000 | 0.0000 | 0.0000 | 0 | 10 | 10 |
| height | - | - | - | - | - | - |
| weight | - | - | - | - | - | - |

**espn Average F1**: 0.0000

#### yahoo

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| team | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| height | - | - | - | - | - | - |
| weight | - | - | - | - | - | - |

**yahoo Average F1**: 1.0000

#### wiki

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| team | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| height | 0.0000 | 0.0000 | 0.0000 | 0 | 10 | 10 |
| weight | 0.0000 | 0.0000 | 0.0000 | 0 | 10 | 10 |

**wiki Average F1**: 0.5000

**Nbaplayer Vertical Average F1**: 0.5000

### Restaurant Vertical

- **opentable**: failed (no details)
- **urbanspoon**: failed (no details)
#### fodors

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 0.9000 | 0.9000 | 0.9000 | 9 | 1 | 1 |
| address | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| phone | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| cuisine | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |

**fodors Average F1**: 0.9750

**Restaurant Vertical Average F1**: 0.9750

### University Vertical

#### collegeboard

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 0.9474 | 1.0000 | 0.9000 | 9 | 0 | 1 |
| phone | - | - | - | - | - | - |
| type | - | - | - | - | - | - |
| website | - | - | - | - | - | - |

**collegeboard Average F1**: 0.9474

#### matchcollege

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | - | - | - | - | - | - |
| phone | - | - | - | - | - | - |
| type | 0.0000 | 0.0000 | 0.0000 | 0 | 175 | 10 |
| website | - | - | - | - | - | - |

**matchcollege Average F1**: 0.0000

#### usnews

| Field | F1 | Precision | Recall | TP | FP | FN |
|-------|----|-----------|---------|----|----|----|\n| name | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| phone | - | - | - | - | - | - |
| type | 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |
| website | - | - | - | - | - | - |

**usnews Average F1**: 1.0000

**University Vertical Average F1**: 0.6491

## Summary

**Overall F1 Score**: 0.6888

### Comparison with AXE

| System | SWDE F1 Score |
|--------|---------------|
| **XPathGenie** | **0.6888** |
| AXE (baseline) | 0.881 |

📊 **XPathGenie shows promising results but has room for improvement.**

## Notes

- Evaluation uses fuzzy text matching (normalized whitespace, case-insensitive)
- XPath generation uses first 3 pages as samples, evaluation on all 10 pages
- Ground truth comparison handles multiple values per field correctly
- This evaluation uses the actual SWDE dataset HTML files (not live websites)
