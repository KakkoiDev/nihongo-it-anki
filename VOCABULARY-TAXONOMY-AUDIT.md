# Vocabulary Taxonomy Audit Report
## nihongo-it-anki Project

**Date**: 2026-01-18
**Scope**: Analysis of Note field taxonomy across tier1-6 vocabulary CSV files
**Total Entries Analyzed**: ~600 vocabulary items

---

## Executive Summary

The current taxonomy system exhibits **significant inconsistencies** that hinder filtering, organization, and learning progression. Major issues include:

1. **Inconsistent naming conventions** - mixing formats (hyphenated, plain text, prefixed)
2. **Unclear hierarchies** - flat structure with no parent-child relationships
3. **Duplicate concepts** - same meaning expressed multiple ways
4. **Over-granular categories** - excessive specificity reducing usability
5. **Missing logical groupings** - related concepts scattered across categories

**Impact**: Users cannot effectively filter by technology area, skill level, or functional domain.

---

## Current State Analysis by Tier

### Tier 1: Foundational (Basic Git, Status, Time Expressions)
**Total Unique Categories**: ~160

**Pattern Observations**:
- **Git operations**: Highly granular with "Git -" prefix (15 subcategories)
  - Examples: "Git - save changes", "Git - upload", "Git - temporary save"
  - **Issue**: Too specific, could be consolidated
- **Status reporting**: Scattered across multiple categories
  - "Status - completed", "Status - in progress", "Status - cannot proceed", "Status report"
- **Time expressions**: Inconsistent naming
  - "At present", "Already", "Still/yet", "Soon", "Later", "Right now", "By today"
- **Basic verbs**: Mixed with technical terms
  - "Add", "Create", "Delete", "Change" alongside "Refactor", "Deploy"

**Critical Issues**:
1. Mix of Japanese phrases and English categories (9 Japanese entries)
2. Compound categories with slashes: "Get/retrieve", "Handle/process", "Repair/solve"
3. No clear distinction between technical actions and soft skills

### Tier 2: Agile, Testing, API Basics
**Total Unique Categories**: ~180

**Pattern Observations**:
- **API terminology**: Well-structured with prefixes
  - "API architecture", "API call", "API reply", "API URL"
  - **Good practice** to emulate
- **Testing categories**: Overly granular (20+ test-related categories)
  - "Test assertion", "Test check", "Test cleanup", "Test collection", "Test data"
  - Could be consolidated under "Testing -" hierarchy
- **HTTP methods**: Grouped effectively
  - "HTTP method" appears 5 times, "HTTP response code" separate
- **SQL operations**: Similar good grouping
  - "SQL command" (4x), "SQL clause" (4x)
- **Agile/Project Management**: Scattered
  - "Daily meeting", "Work unit", "Work item", "Task queue", "Task organization"

**Critical Issues**:
1. Testing taxonomy is too fragmented (20+ categories for testing alone)
2. Database/SQL terms not consolidated with broader data categories
3. Agile terminology lacks consistent prefix pattern

### Tier 3: Code Review, Architecture, AWS, DevOps
**Total Unique Categories**: ~260

**Pattern Observations**:
- **AWS services**: Extremely granular (60+ AWS-specific categories)
  - "AWS alarm", "AWS API", "AWS audit", "AWS auth", etc.
  - **Issue**: Each AWS service is separate category
  - **Better**: Group under "AWS - Compute", "AWS - Storage", "AWS - Networking"
- **Architecture patterns**: Well-named but flat
  - "Singleton", "Factory", "Observer", "MVC", "Microservices"
  - No grouping under "Architecture -" or "Design Pattern -"
- **Code quality**: Mixed naming
  - "DRY" vs "Don't repeat yourself", "KISS", "SOLID principles"
- **Review feedback**: Good variety but inconsistent
  - "Minor suggestion" vs "Minor issue", "Major issue"

**Critical Issues**:
1. AWS category explosion (60+ categories) - needs hierarchical consolidation
2. Acronyms (DRY, KISS, SOLID) mixed with spelled-out equivalents
3. No clear separation of DevOps tools vs cloud providers vs practices

### Tier 4: Security, Frontend, Data Storage
**Total Unique Categories**: ~200

**Pattern Observations**:
- **Security**: Scattered across general terms
  - "Security", "Encryption", "Decrypt", "Hash", "Salt", "XSS", "CSRF"
  - No "Security -" prefix for consistency
- **Frontend technologies**: Mixed specificity
  - "Frontend", "Backend", "Fullstack" (general)
  - "React", "DOM", "Virtual DOM", "Hook", "Props", "State" (React-specific)
  - "CSS", "Flexbox", "Grid" (CSS-specific)
- **Data storage**: Better organized
  - "Cache", "Cache hit", "Cache miss" (grouped conceptually)
  - "Redis", "Memcached" (specific technologies)
- **Authentication**: Good grouping potential
  - "OAuth", "JWT", "SAML", "SSO", "Two-factor auth"

**Critical Issues**:
1. Frontend framework specifics (React) not clearly labeled as such
2. Security terms need "Security -" prefix hierarchy
3. Mix of abstract concepts ("Accessibility", "a11y") with concrete tools

### Tier 5: Communication, Soft Skills, Workplace
**Total Unique Categories**: ~100

**Pattern Observations**:
- **Communication**: Well-defined soft skills
  - "Agree", "Disagree", "Suggest", "Propose", "Recommend"
  - "Acknowledge", "Confirm", "Clarify", "Explain"
- **Acronyms**: Heavy use of workplace shorthand
  - "ASAP", "EOD", "ETA", "TBD", "TL;DR", "FYI", "IMO", "BTW"
  - "WFH", "OOO", "PTO"
- **Meeting/collaboration**: Consistent verbs
  - "Follow up", "Circle back", "Touch base", "Check in", "Loop in"
- **Project management**: Clear terms
  - "Deadline", "Milestone", "Deliverable", "Timeline", "Scope"

**Critical Issues**:
1. Mix of 6 Japanese full-sentence categories (should be removed from Note field)
2. Acronyms useful but not grouped as "Acronym -" prefix
3. Some categories redundant: "Notice" vs "Announcement"

### Tier 6: Presentations, Career Development
**Total Unique Categories**: ~100

**Pattern Observations**:
- **Presentation phrases**: **EXCELLENT** hierarchical structure
  - "Presentation - agenda", "Presentation - overview", "Presentation - conclusion"
  - All consistently prefixed, creating logical grouping
  - **Best practice example** for entire taxonomy
- **Career development**: Also well-structured
  - "Career - team", "Career - manager", "Career - growth"
  - Consistent prefix creates clear domain
- **Japanese entries**: 2 full sentences (should be removed)

**Critical Issues**:
1. Two Japanese sentence categories (cleanup needed)
2. Otherwise, **this tier demonstrates ideal taxonomy structure**

---

## Identified Issues Summary

### 1. Inconsistent Naming Conventions

| Issue | Examples | Recommended Fix |
|-------|----------|-----------------|
| **Hyphen vs Plain** | "Git - save changes" vs "Save changes" | Use consistent separator (recommend " - ") |
| **Compound with slashes** | "Get/retrieve", "Repair/solve" | Choose one primary term per category |
| **Abbreviation inconsistency** | "DRY" vs "Don't repeat yourself" | Use abbreviation in category, spell out in KeyMeaning |
| **Prefix inconsistency** | "AWS alarm" vs "API - call" | All domain-specific terms get prefix |
| **Mixed languages** | English categories + Japanese sentences | Remove Japanese sentences from Note field |

### 2. Hierarchical Structure Problems

| Current State | Issue | Proposed Fix |
|---------------|-------|--------------|
| Flat categories | 900+ categories at same level | Introduce 2-level hierarchy (Domain - Specific) |
| No grouping | "Hash", "Salt", "Encrypt" separate | "Security - Hashing", "Security - Encryption" |
| Over-specific AWS | 60+ individual AWS services | Group by service type: "AWS - Storage (S3)", "AWS - Compute (EC2)" |
| Testing scattered | 20+ test categories | "Testing - Unit", "Testing - Integration", "Testing - E2E" |

### 3. Granularity Issues

**Too Granular** (reduce):
- Git operations: 15 categories → 5-7 consolidated
- Testing types: 20 categories → 6-8 consolidated
- AWS services: 60 categories → 15-20 consolidated

**Too Broad** (expand):
- "Development" - needs subcategories
- "Performance" - split into frontend/backend/database
- "Security" - needs auth/encryption/compliance subcategories

### 4. Duplicate Concepts

| Duplicate Set | Consolidate To |
|---------------|----------------|
| "Fail", "Failed", "Failure" | "Failure" |
| "Return", "Return URL", "Callback" | Separate: "Return (value)" vs "Callback (async)" |
| "Notice", "Announcement", "Reminder" | Merge to "Notification" with subtypes |
| "Question", "Inquiry" | "Question" |
| "Approve", "Approval", "Approved" | "Approval" (covers all tenses) |

### 5. Missing Logical Groupings

**Domains without prefixes** (should add):
- **Database**: PostgreSQL, MySQL, MongoDB concepts scattered
- **Security**: Encryption, auth, compliance not grouped
- **Frontend Frameworks**: React, Vue, Angular mixed with generic frontend
- **Communication Protocols**: HTTP, WebSocket, gRPC not grouped
- **Monitoring**: Logging, metrics, alerting scattered

---

## Proposed New Taxonomy

### Core Principles

1. **Two-level hierarchy**: `Domain - Specific Term`
2. **Consistent separators**: Use ` - ` (space-hyphen-space)
3. **Domain prefixes**: All domain-specific terms get prefix
4. **Logical grouping**: Related concepts under same domain
5. **Balanced granularity**: Specific enough to filter, general enough to browse

### Tier Progression Strategy

| Tier | Focus Areas | Complexity |
|------|-------------|------------|
| **1** | Git Basics, Time, Status, Greetings | Fundamental workflow |
| **2** | Agile, Testing, HTTP/REST, SQL Basics | Development practices |
| **3** | Architecture, Code Review, Cloud, DevOps | System design |
| **4** | Security, Frontend, Data, Advanced Backend | Specialized domains |
| **5** | Communication, Soft Skills, Workplace | Professional skills |
| **6** | Presentations, Leadership, Career | Advanced professional |

### Proposed Taxonomy Structure

#### **1. Git & Version Control** (Tier 1)
```
Git - Commit
Git - Branch
Git - Merge
Git - Conflict
Git - Remote (push/pull)
Git - History
Git - Undo (revert/reset)
Git - Collaboration (PR/review)
```

#### **2. Development Workflow** (Tier 1-2)
```
Workflow - Status
Workflow - Progress
Workflow - Blocking
Workflow - Completion
Workflow - Update
```

#### **3. Time & Scheduling** (Tier 1)
```
Time - Present
Time - Past
Time - Future
Time - Duration
Time - Deadline
Time - Frequency
```

#### **4. Communication - Basic** (Tier 1)
```
Communication - Greeting
Communication - Gratitude
Communication - Agreement
Communication - Apology
Communication - Request
Communication - Question
```

#### **5. Communication - Professional** (Tier 5)
```
Communication - Suggestion
Communication - Disagreement
Communication - Clarification
Communication - Feedback
Communication - Negotiation
Communication - Follow-up
```

#### **6. Agile & Project Management** (Tier 2)
```
Agile - Sprint
Agile - Backlog
Agile - User Story
Agile - Epic
Agile - Task
Agile - Meeting (standup/retro/planning)
Agile - Priority
Agile - Estimation
Agile - Capacity
```

#### **7. Testing** (Tier 2-3)
```
Testing - Unit
Testing - Integration
Testing - E2E
Testing - TDD
Testing - Assertion
Testing - Mock
Testing - Coverage
Testing - Flaky
Testing - Performance
```

#### **8. API & HTTP** (Tier 2)
```
API - REST
API - GraphQL
API - Endpoint
API - Request
API - Response
API - Authentication
HTTP - Method (GET/POST/PUT/PATCH/DELETE)
HTTP - Status Code
HTTP - Header
HTTP - Body
```

#### **9. Database - SQL** (Tier 2)
```
Database - Table
Database - Query
Database - Join
Database - Index
Database - Transaction
Database - Migration
Database - Relationship
SQL - SELECT
SQL - INSERT
SQL - UPDATE
SQL - DELETE
SQL - WHERE
```

#### **10. Database - NoSQL & Data** (Tier 3-4)
```
Database - NoSQL
Database - Cache (Redis/Memcached)
Database - Connection Pool
Database - ORM
Data - Model
Data - Schema
Data - Validation
Data - Serialization
Data - ETL
```

#### **11. Cloud - AWS** (Tier 3)
```
AWS - Compute (EC2, Lambda, ECS)
AWS - Storage (S3, EBS)
AWS - Database (RDS, DynamoDB)
AWS - Networking (VPC, Route53, CloudFront)
AWS - Security (IAM, Secrets Manager)
AWS - Monitoring (CloudWatch)
AWS - Deployment (CodePipeline, CloudFormation)
```

#### **12. Cloud - General** (Tier 3)
```
Cloud - Infrastructure
Cloud - Serverless
Cloud - Container (Docker, Kubernetes)
Cloud - Auto-scaling
Cloud - Load Balancing
Cloud - CDN
```

#### **13. DevOps** (Tier 3)
```
DevOps - CI/CD
DevOps - Pipeline
DevOps - Deployment
DevOps - Environment (dev/staging/prod)
DevOps - Monitoring
DevOps - Logging
DevOps - Alerting
DevOps - Incident
DevOps - Runbook
```

#### **14. Architecture** (Tier 3)
```
Architecture - Pattern (MVC, Microservices, Monolith)
Architecture - Design Pattern (Singleton, Factory, Observer)
Architecture - Layer (Controller, Service, Repository)
Architecture - Scalability
Architecture - Performance
Architecture - Coupling (Loose/Tight)
Architecture - Cohesion
Architecture - SOLID
```

#### **15. Code Quality** (Tier 3)
```
Code Quality - Review
Code Quality - Refactoring
Code Quality - Clean Code
Code Quality - DRY
Code Quality - KISS
Code Quality - YAGNI
Code Quality - Technical Debt
Code Quality - Legacy
Code Quality - Documentation
```

#### **16. Security** (Tier 4)
```
Security - Authentication (OAuth, JWT, SAML)
Security - Authorization (RBAC, Permissions)
Security - Encryption (AES, TLS, HTTPS)
Security - Hashing (bcrypt, Salt)
Security - Vulnerability (XSS, CSRF, Injection)
Security - Compliance (GDPR, PCI, SOC2)
Security - Audit
Security - Secret Management
```

#### **17. Frontend - Core** (Tier 4)
```
Frontend - HTML
Frontend - CSS (Flexbox, Grid)
Frontend - JavaScript
Frontend - DOM
Frontend - Event
Frontend - Form
Frontend - Responsive
Frontend - Accessibility (a11y, ARIA)
Frontend - SEO
Frontend - Performance
```

#### **18. Frontend - React** (Tier 4)
```
React - Component
React - Props
React - State
React - Hook
React - Lifecycle
React - Virtual DOM
React - Rendering
React - Event Handler
```

#### **19. Frontend - Tooling** (Tier 4)
```
Frontend - Build (webpack, Vite)
Frontend - Transpile (Babel)
Frontend - Bundling
Frontend - Code Splitting
Frontend - Minify
Frontend - SSR
Frontend - CSR
```

#### **20. Backend** (Tier 4)
```
Backend - Server
Backend - API
Backend - Service
Backend - Controller
Backend - Middleware
Backend - Authentication
Backend - Validation
Backend - Error Handling
Backend - Logging
```

#### **21. Data Engineering** (Tier 4)
```
Data - Pipeline
Data - Warehouse
Data - Lake
Data - Quality
Data - ETL
Data - Streaming
Data - Batch Processing
Data - Aggregation
```

#### **22. Performance** (Tier 4)
```
Performance - Caching
Performance - CDN
Performance - Optimization
Performance - Latency
Performance - Throughput
Performance - Load Testing
Performance - Profiling
Performance - Bottleneck
```

#### **23. Workplace Communication** (Tier 5)
```
Workplace - Meeting
Workplace - Email
Workplace - Slack
Workplace - Video Call
Workplace - Presentation
Workplace - Documentation
Workplace - Acronym (ASAP, EOD, FYI)
```

#### **24. Project Collaboration** (Tier 5)
```
Collaboration - Deadline
Collaboration - Milestone
Collaboration - Deliverable
Collaboration - Scope
Collaboration - Timeline
Collaboration - Stakeholder
Collaboration - Dependency
Collaboration - Risk
```

#### **25. Presentation Skills** (Tier 6)
```
Presentation - Opening (Agenda, Intro, Context)
Presentation - Body (Demo, Data, Diagram)
Presentation - Transition (Moving on, Going back)
Presentation - Closing (Summary, Conclusion, Q&A)
Presentation - Engagement (Question, Feedback, Clarification)
```

#### **26. Career Development** (Tier 6)
```
Career - Growth
Career - Skills
Career - Performance
Career - Feedback
Career - Mentorship
Career - Leadership
Career - Team
Career - Communication
Career - Work-Life Balance
```

---

## Mapping Recommendations (Old → New)

### Git & Version Control
```
Git - save changes        → Git - Commit
Git - upload             → Git - Remote
Git - download           → Git - Remote
Git - combine            → Git - Merge
Git - clash              → Git - Conflict
Git - version line       → Git - Branch
Git - temporary save     → Git - Stash
Git - undo              → Git - Undo
Git - replay commits     → Git - Rebase
Git - select commit      → Git - Cherry-pick
Git - combine commits    → Git - Squash
Git - show author       → Git - History
Git - switch branch     → Git - Branch
Git - label version     → Git - Tag
Git - copy repo         → Git - Clone
Git - personal copy     → Git - Fork
Pull request            → Git - Collaboration
Examine code            → Git - Collaboration
```

### Testing Consolidation
```
Test                    → Testing - Unit
Basic test              → Testing - Unit
Component test          → Testing - Integration
System test             → Testing - E2E
End-to-end test         → Testing - E2E
Test-driven development → Testing - TDD
TDD cycle              → Testing - TDD
Test assertion         → Testing - Assertion
Test check             → Testing - Assertion
Fake object            → Testing - Mock
Fake implementation    → Testing - Mock
Call tracker           → Testing - Mock
Test data              → Testing - Data
Test cleanup           → Testing - Setup
Test preparation       → Testing - Setup
Test environment       → Testing - Environment
Code coverage          → Testing - Coverage
Test success           → Testing - Result
Test summary           → Testing - Result
Flaky test             → Testing - Flaky
UI test                → Testing - E2E
Performance test       → Testing - Performance
Speed test             → Testing - Performance
Bug prevention test    → Testing - Regression
```

### AWS Consolidation (60+ → 15)
```
AWS - EC2, Lambda, ECS, Fargate          → AWS - Compute
AWS - S3, EBS, Glacier                  → AWS - Storage
AWS - RDS, DynamoDB, Aurora             → AWS - Database
AWS - VPC, Route53, CloudFront, API Gateway → AWS - Networking
AWS - IAM, Secrets Manager, KMS         → AWS - Security
AWS - CloudWatch, X-Ray                 → AWS - Monitoring
AWS - CodePipeline, CodeBuild, CloudFormation → AWS - Deployment
AWS - SNS, SQS, EventBridge            → AWS - Messaging
AWS - Glue, Athena, Redshift           → AWS - Analytics
```

### Communication Consolidation
```
Gratitude              → Communication - Gratitude
Agreement              → Communication - Agreement
Understanding          → Communication - Acknowledgment
Acknowledged           → Communication - Acknowledgment
Apology               → Communication - Apology
In fact               → Communication - Clarification
Question              → Communication - Question
Inquiry               → Communication - Question
Suggestion            → Communication - Suggestion
Propose               → Communication - Suggestion
Recommend             → Communication - Recommendation
```

### Agile/Project Management
```
Daily meeting          → Agile - Meeting
Standup               → Agile - Meeting
Retrospective         → Agile - Meeting
Planning              → Agile - Meeting
Sprint                → Agile - Sprint
Development cycle     → Agile - Sprint
Backlog               → Agile - Backlog
Task queue            → Agile - Backlog
User story            → Agile - User Story
Feature description   → Agile - User Story
Epic                  → Agile - Epic
Large feature         → Agile - Epic
Task                  → Agile - Task
Work unit             → Agile - Task
Work item             → Agile - Task
Ticket                → Agile - Task
Priority              → Agile - Priority
Importance level      → Agile - Priority
Estimate              → Agile - Estimation
Time prediction       → Agile - Estimation
Story points          → Agile - Estimation
Velocity              → Agile - Velocity
Team speed            → Agile - Velocity
Capacity              → Agile - Capacity
Available resources   → Agile - Capacity
Blocker               → Agile - Blocker
Critical obstacle     → Agile - Blocker
```

### API & HTTP
```
Application interface  → API - Concept
API architecture      → API - Architecture
API design            → API - Architecture
REST                  → API - REST
RESTful API          → API - REST
GraphQL              → API - GraphQL
Endpoint             → API - Endpoint
API URL              → API - Endpoint
Request              → API - Request
API call             → API - Request
Response             → API - Response
API reply            → API - Response
GET                  → HTTP - Method
POST                 → HTTP - Method
PUT                  → HTTP - Method
PATCH                → HTTP - Method
DELETE               → HTTP - Method
200                  → HTTP - Status Code
201                  → HTTP - Status Code
400                  → HTTP - Status Code
401                  → HTTP - Status Code
403                  → HTTP - Status Code
404                  → HTTP - Status Code
500                  → HTTP - Status Code
Header               → HTTP - Header
Request metadata     → HTTP - Header
Body                 → HTTP - Body
Request content      → HTTP - Body
Payload              → HTTP - Body
Query string         → HTTP - Query
URL parameters       → HTTP - Query
```

### Security
```
Security             → Security - General
Authentication       → Security - Authentication
Identity verification → Security - Authentication
OAuth               → Security - Authentication
JWT                 → Security - Authentication
SAML                → Security - Authentication
SSO                 → Security - Authentication
Two-factor auth     → Security - Authentication
MFA                 → Security - Authentication
Authorization       → Security - Authorization
Permission check    → Security - Authorization
RBAC                → Security - Authorization
Access control      → Security - Authorization
Encryption          → Security - Encryption
Encrypt             → Security - Encryption
Decrypt             → Security - Encryption
AES                 → Security - Encryption
TLS                 → Security - Encryption
HTTPS               → Security - Encryption
SSL                 → Security - Encryption
Certificate         → Security - Encryption
Hash                → Security - Hashing
Hashing             → Security - Hashing
bcrypt              → Security - Hashing
Salt                → Security - Hashing
XSS                 → Security - Vulnerability
CSRF                → Security - Vulnerability
Injection           → Security - Vulnerability
SQL injection       → Security - Vulnerability
Command injection   → Security - Vulnerability
Vulnerability       → Security - Vulnerability
Exploit             → Security - Vulnerability
Attack              → Security - Vulnerability
DDoS                → Security - Vulnerability
Breach              → Security - Vulnerability
GDPR                → Security - Compliance
PCI                 → Security - Compliance
SOC 2               → Security - Compliance
Compliance          → Security - Compliance
Audit               → Security - Audit
Pen test            → Security - Audit
Vulnerability scan  → Security - Audit
Secret              → Security - Secret Management
Secrets             → Security - Secret Management
Credential          → Security - Secret Management
Key rotation        → Security - Secret Management
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Goal**: Establish core taxonomy structure

1. **Define master category list** (150-200 categories total)
2. **Create mapping spreadsheet** (old category → new category)
3. **Update Tier 1 vocabulary** (validate with users)
4. **Document taxonomy guidelines** (for future additions)

### Phase 2: Systematic Migration (Week 3-4)
**Goal**: Update all existing vocabulary

1. **Tier 2-3 migration** (Agile, Testing, AWS, DevOps)
2. **Tier 4 migration** (Security, Frontend, Data)
3. **Tier 5-6 migration** (Communication, Career)
4. **Validation pass** (ensure no broken categories)

### Phase 3: Enhancement (Week 5)
**Goal**: Improve filtering and UX

1. **Add category descriptions** (help text for each category)
2. **Create category hierarchy file** (for UI filtering)
3. **Generate category statistics** (distribution per tier)
4. **User documentation** (how to use new taxonomy)

### Phase 4: Quality Assurance (Week 6)
**Goal**: Ensure consistency

1. **Automated validation script** (check for naming violations)
2. **Category usage report** (identify unused categories)
3. **User feedback collection** (test with sample learners)
4. **Final adjustments** (based on feedback)

---

## Validation Rules

### Naming Convention Rules
1. **Domain prefix**: All domain-specific terms MUST use format `Domain - Specific`
2. **Separator**: Always use ` - ` (space-hyphen-space), never `-`, `_`, or `/`
3. **Capitalization**: Title Case for both Domain and Specific (e.g., `Git - Commit`, not `git - commit`)
4. **Abbreviations**: Spell out in category when possible, use abbreviation in KeyMeaning
5. **No Japanese**: Note field MUST be English only (Japanese goes in Sentence/Translation fields)
6. **No slashes**: Never use `/` in categories (e.g., "Get/retrieve" → choose "Retrieve")
7. **Singular form**: Use singular nouns (e.g., "Test" not "Tests", "Branch" not "Branches")
8. **Verb form**: For actions, use base form (e.g., "Commit" not "Committing" or "Committed")

### Hierarchy Rules
1. **Two-level maximum**: Format `Domain - Specific`, never `Domain - Sub - Specific`
2. **Domain consistency**: Same domain prefix across related terms
3. **Specific granularity**: Specific term should be 1-3 words maximum
4. **Logical grouping**: Related terms under same domain (e.g., all Git operations under "Git -")
5. **Technology separation**: Framework-specific (React, Vue) gets own domain vs generic (Frontend -)

### Quality Rules
1. **No duplicates**: Each concept should map to exactly ONE category
2. **Clear meaning**: Category name should be self-explanatory
3. **Balanced granularity**: Not too broad ("Development") nor too narrow ("Save changes to local branch")
4. **Tier appropriate**: Category complexity should match tier difficulty
5. **Searchable**: Users should be able to guess category name for filtering

---

## Benefits of New Taxonomy

### For Learners
- **Easy filtering**: "Show me all Git commands" or "Security terminology only"
- **Clear progression**: See related concepts grouped by domain
- **Better retention**: Hierarchical structure aids memory
- **Skill assessment**: Track progress by domain (e.g., "90% complete in Testing domain")

### For Content Creators
- **Consistency**: Clear guidelines for categorizing new vocabulary
- **Scalability**: Easy to add new terms without creating chaos
- **Validation**: Automated checks prevent taxonomy drift
- **Documentation**: Category structure self-documents organization

### For Platform Development
- **Filtering UI**: Build category tree navigation
- **Analytics**: Track learning progress by domain/tier
- **Recommendations**: "You've mastered Git, try DevOps next"
- **Export/Import**: Standardized format for data exchange

---

## Appendix: Category Statistics

### Current State (Before Consolidation)
```
Tier 1:  ~160 unique categories
Tier 2:  ~180 unique categories
Tier 3:  ~260 unique categories (AWS explosion!)
Tier 4:  ~200 unique categories
Tier 5:  ~100 unique categories
Tier 6:  ~100 unique categories
--------------------------------------
Total:   ~1000 unique categories (TOO MANY!)
```

### Proposed State (After Consolidation)
```
Core Domains:           26 domains
Average per domain:     6-8 specific categories
Total categories:       150-200 (80% reduction!)
Domain distribution:
  - Git & VCS:          8 categories
  - Testing:            9 categories
  - AWS:               15 categories (was 60+)
  - API & HTTP:        12 categories
  - Database:          15 categories
  - Security:          12 categories
  - Frontend:          20 categories (inc. React)
  - DevOps:           10 categories
  - Communication:    15 categories
  - Career:           10 categories
  - Others:           34 categories
```

### Reduction Examples
| Domain | Before | After | Reduction |
|--------|--------|-------|-----------|
| AWS | 60+ | 15 | 75% |
| Testing | 20+ | 9 | 55% |
| Git | 15 | 8 | 47% |
| Communication | 25 | 15 | 40% |

---

## Next Steps

1. **Review this audit** with project stakeholders
2. **Validate proposed taxonomy** with sample users
3. **Create migration script** (CSV transformation)
4. **Test updated vocabulary** with Anki deck
5. **Document new guidelines** for contributors
6. **Implement validation** in CI/CD pipeline

---

**End of Audit Report**
