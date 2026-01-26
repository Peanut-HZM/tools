# Project Brief: streamlit-snowflake Skill

**Created**: 2024-12-24
**Status**: Ready for Planning

---

## Vision

A Claude Code skill that accelerates building and publishing Streamlit apps natively in Snowflake, covering the complete workflow from project scaffold to Marketplace listing.

## Problem/Opportunity

Building Streamlit apps in Snowflake has several friction points:
- Complex `snowflake.yml` configuration with many options
- Package limitations (only Snowflake Anaconda Channel)
- Default Streamlit version is outdated (1.22.0 vs current 1.35)
- Marketplace publishing requires multiple steps (provider profile, listings, Native App packaging)
- Authentication patterns are evolving (password deprecation by Oct 2026)
- No existing Claude Code skills for this ecosystem

## Target Audience

- **Primary**: Developers building data apps on Snowflake
- **Secondary**: Data teams publishing data products to Marketplace
- **Context**: Building skills for personal use + potentially contributing to claude-skills repo

## Core Functionality (MVP)

### 1. Project Scaffolding
- `snowflake.yml` template with production-ready defaults
- `environment.yml` with common data viz packages + explicit Streamlit version
- `streamlit_app.py` with Snowpark session pattern and caching
- Multi-page structure (`pages/` directory)
- `.gitignore` for Snowflake projects

### 2. Connection Patterns
- `st.connection("snowflake")` usage examples
- Snowpark session management
- `@st.cache_data` patterns for expensive queries
- Secure credential handling (no hardcoding)

### 3. Deployment Workflow
- `snow streamlit deploy --replace` command patterns
- GitHub Actions CI/CD template
- Local development with Snowflake CLI

### 4. Marketplace Publishing (Native App)
- Provider profile setup guidance
- Listing creation workflow
- Native App file structure for Streamlit apps
- Permission SDK for consumer interactions
- `manifest.yml` and `setup.sql` templates

## Out of Scope for MVP (Future Skills)

- **Snowpark skill** (DataFrame API, UDFs, Stored Procedures) - separate skill
- **Snowflake MCP server** setup - already exists (Snowflake-Labs/mcp)
- **External Streamlit hosting** (Community Cloud) - different workflow
- **Cortex AI integration** (search, analyst) - separate concern

## Tech Stack (Validated)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CLI | Snowflake CLI (`snow`) | Official tool, required for deployment |
| Config | `snowflake.yml` v2 | Definition version 2 is current |
| Packages | Snowflake Anaconda Channel | Only supported option for native apps |
| Streamlit | 1.35.0 (explicit) | Latest supported, avoids 1.22.0 default |
| Python | 3.11 | Best compatibility with Snowpark |

## Research Findings

### Key Documentation Sources
- [Create and deploy Streamlit apps using Snowflake CLI](https://docs.snowflake.com/en/developer-guide/streamlit/create-streamlit-snowflake-cli)
- [Initializing a Streamlit app](https://docs.snowflake.com/en/developer-guide/snowflake-cli/streamlit-apps/manage-apps/initialize-app)
- [About Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- [Adding Streamlit to Native Apps](https://docs.snowflake.com/en/developer-guide/native-apps/adding-streamlit)
- [Marketplace Publishing Guidelines](https://docs.snowflake.com/en/developer-guide/native-apps/publish-guidelines)

### Official Templates & Examples
- [snowpark-python-template](https://github.com/Snowflake-Labs/snowpark-python-template) - CI/CD ready
- [native-apps-templates](https://github.com/snowflakedb/native-apps-templates) - CLI compatible
- [snowflake-demo-streamlit](https://github.com/Snowflake-Labs/snowflake-demo-streamlit) - Comprehensive demos

### Package Discovery Tool
- [Snowpark Python Packages Explorer](https://snowpark-python-packages.streamlit.app/) - Check available packages
- SQL: `select * from information_schema.packages where language = 'python';`

### Known Limitations
1. **No custom Streamlit components** - native platform limitation
2. **Only Snowflake Anaconda Channel packages** - no conda-forge
3. **No Azure Private Link / GCP Private Service Connect** for app access
4. **page_title and page_icon not supported** in st.set_page_config

### Errors to Prevent

| Error | Cause | Prevention |
|-------|-------|------------|
| Package not found | Using external Anaconda channel | Always use `channels: - snowflake` |
| Old Streamlit features | Default 1.22.0 version | Explicitly set `streamlit=1.35.0` |
| Deployment fails | Using deprecated ROOT_LOCATION | Use `FROM source_location` (CLI 3.14.0+) |
| Auth failures 2026+ | Password-only authentication | Document key-pair/OAuth patterns |
| File too large | >250MB files | Document size limits |

## Scope Validation

**Why Build This?**
- No existing skill covers this workflow
- Significant setup time for each new project
- Multiple error-prone configuration steps
- Marketplace publishing is multi-step and undocumented in skill form

**Why Single Skill (Not Split)?**
- Streamlit + Marketplace are often used together
- Provider profile setup is one-time, not repeated
- Native App packaging is tightly coupled to Streamlit structure
- Keeps context together for coherent workflow

**What Could Go Wrong?**
1. **Snowflake CLI changes** - Mitigation: Pin to CLI 3.14+ patterns, document version
2. **Package availability changes** - Mitigation: Link to package explorer, document how to check
3. **Auth deprecation timeline** - Mitigation: Document modern auth patterns, warn about 2026 deadline

## Estimated Effort

- **Skill creation**: ~2-3 hours (templates, documentation, error prevention)
- **With Claude Code**: ~5-10 minutes human interaction time
- **Breakdown**:
  - SKILL.md structure: 30 min
  - Templates (4-5 files): 1 hour
  - Error prevention docs: 30 min
  - Testing/validation: 30 min

## Success Criteria

- [ ] `snow init` replacement with better defaults works
- [ ] Deployed app runs in Snowflake without errors
- [ ] Marketplace listing can be created following guidance
- [ ] No hardcoded credentials in templates
- [ ] Token savings ≥50% vs manual setup

## Skill Structure (Proposed)

```
skills/streamlit-snowflake/
├── SKILL.md                    # Main skill documentation
├── README.md                   # Auto-trigger keywords
├── templates/
│   ├── snowflake.yml           # Project definition
│   ├── environment.yml         # Package dependencies
│   ├── streamlit_app.py        # Entry point with patterns
│   ├── pages/
│   │   └── example_page.py     # Multi-page example
│   ├── common/
│   │   └── utils.py            # Shared utilities
│   └── .gitignore              # Snowflake-specific ignores
├── templates-native-app/       # Marketplace publishing
│   ├── manifest.yml            # Native App manifest
│   ├── setup.sql               # Installation script
│   └── README.md               # Publishing workflow
├── references/
│   ├── available-packages.md   # How to check Anaconda channel
│   ├── authentication.md       # Key-pair, OAuth patterns
│   └── ci-cd.md                # GitHub Actions template
└── scripts/
    └── check-packages.sql      # Query available packages
```

## Next Steps

**If proceeding**:
1. Run `/plan-project` to generate IMPLEMENTATION_PHASES.md
2. Create skill directory structure
3. Write templates based on official docs
4. Test with a real Snowflake project
5. Add to skills repo

---

## Research References

- [Snowflake CLI Streamlit Commands](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/streamlit-commands/overview)
- [Streamlit in Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- [Snowflake Marketplace About](https://other-docs.snowflake.com/en/collaboration/collaboration-marketplace-about)
- [Native Apps Adding Streamlit](https://docs.snowflake.com/en/developer-guide/native-apps/adding-streamlit)
- [Snowpark Python Packages Explorer](https://snowpark-python-packages.streamlit.app/)
- [GitLab's Streamlit Framework in Snowflake](https://about.gitlab.com/blog/how-we-built-a-structured-streamlit-application-framework-in-snowflake/)
- [Snowflake MCP Server](https://github.com/Snowflake-Labs/mcp)
