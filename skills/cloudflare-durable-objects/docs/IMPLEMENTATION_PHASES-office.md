# Implementation Phases: `office` Skill

**Project**: TypeScript document generation skill (DOCX, XLSX, PDF)
**Estimated Total**: ~4-5 hours (~4-5 min human time)
**Brief**: `planning/PROJECT_BRIEF-office-skill.md`

---

## Phase 1: Skill Scaffolding (~30 min)

**Type**: Setup
**Goal**: Create skill directory structure following claude-skills standards

### Tasks

1. **Create skill directory structure**
   ```
   skills/office/
   ├── SKILL.md
   ├── README.md
   ├── rules/
   ├── templates/
   ├── references/
   └── scripts/
   ```

2. **Create SKILL.md skeleton**
   - YAML frontmatter (name, description)
   - Section headers for each format (DOCX, XLSX, PDF)
   - "Use when" scenarios
   - Known issues placeholder

3. **Create README.md with keywords**
   - Auto-trigger keywords for each format
   - Library names for discoverability

4. **Verify against claude-skills standards**
   - Check ONE_PAGE_CHECKLIST.md compliance
   - Ensure YAML frontmatter is valid

### Exit Criteria
- [ ] `skills/office/` directory exists with all subdirectories
- [ ] SKILL.md has valid YAML frontmatter
- [ ] README.md has comprehensive keywords
- [ ] Structure matches `templates/skill-skeleton/`

---

## Phase 2: DOCX Patterns (~1 hour)

**Type**: Implementation
**Goal**: Complete Word document generation patterns using `docx` npm package

### Tasks

1. **Research current `docx` npm API**
   - Check latest version (v9.x)
   - Review key classes: Document, Paragraph, TextRun, Table, ImageRun
   - Note Workers compatibility requirements

2. **Write SKILL.md DOCX section**
   - Installation: `npm install docx`
   - Basic document structure pattern
   - Headings, paragraphs, formatting
   - Tables with styling
   - Images (from buffer/URL)
   - Export patterns (Node.js vs browser)

3. **Create `templates/docx-basic.ts`**
   - Complete working example
   - Comments explaining each section
   - Both Node.js and browser export

4. **Create `references/docx-api.md`**
   - Quick reference for common classes
   - Formatting options table
   - Measurement units (DXA: 1440 = 1 inch)

5. **Add correction rules to `rules/office.md`**
   - Common mistakes with `docx` package
   - Import patterns
   - Export gotchas

### Exit Criteria
- [ ] SKILL.md DOCX section complete with patterns
- [ ] `templates/docx-basic.ts` creates valid .docx file
- [ ] Reference doc covers key API
- [ ] Correction rules prevent common errors

---

## Phase 3: XLSX Patterns (~1 hour)

**Type**: Implementation
**Goal**: Complete Excel spreadsheet generation patterns using SheetJS

### Tasks

1. **Research SheetJS (xlsx) API**
   - Check latest version (v0.18.x)
   - Review key functions: utils, writeFile, write
   - Confirm Workers compatibility

2. **Write SKILL.md XLSX section**
   - Installation: `npm install xlsx`
   - Workbook/worksheet creation
   - Cell data types and formatting
   - Formulas (basic)
   - Column widths and row heights
   - Export patterns

3. **Create `templates/xlsx-basic.ts`**
   - Complete working example
   - Multiple sheets
   - Formulas and formatting
   - Both Node.js and browser export

4. **Create `references/xlsx-api.md`**
   - Quick reference for utils functions
   - Cell reference formats (A1 vs R1C1)
   - Data type handling

5. **Add XLSX corrections to `rules/office.md`**
   - Formula syntax gotchas
   - Date handling issues
   - Large file considerations

### Exit Criteria
- [ ] SKILL.md XLSX section complete
- [ ] `templates/xlsx-basic.ts` creates valid .xlsx file
- [ ] Reference doc covers key API
- [ ] Correction rules added

---

## Phase 4: PDF Patterns (~1 hour)

**Type**: Implementation
**Goal**: Complete PDF generation patterns using pdf-lib

### Tasks

1. **Research pdf-lib API**
   - Check latest version (v1.17.x)
   - Review key classes: PDFDocument, PDFPage, PDFFont
   - Form filling capabilities
   - Merge/split operations

2. **Write SKILL.md PDF section**
   - Installation: `npm install pdf-lib`
   - Create PDF from scratch
   - Add text, images, shapes
   - Fill existing PDF forms
   - Merge multiple PDFs
   - Export patterns

3. **Create `templates/pdf-basic.ts`**
   - Complete working example
   - Text with custom fonts
   - Images from buffer
   - Basic shapes/lines

4. **Create `templates/pdf-form-fill.ts`**
   - Load existing PDF
   - Fill form fields
   - Save modified PDF

5. **Create `references/pdf-lib-api.md`**
   - Quick reference for key methods
   - Coordinate system (origin bottom-left)
   - Font embedding options

6. **Add PDF corrections to `rules/office.md`**
   - Coordinate system confusion
   - Font embedding requirements
   - Async patterns

### Exit Criteria
- [ ] SKILL.md PDF section complete
- [ ] `templates/pdf-basic.ts` creates valid PDF
- [ ] `templates/pdf-form-fill.ts` fills forms correctly
- [ ] Reference doc covers key API
- [ ] Correction rules added

---

## Phase 5: Workers Integration (~45 min)

**Type**: Implementation
**Goal**: Add Cloudflare Workers examples and HTML→PDF via Browser Rendering

### Tasks

1. **Create `templates/workers-docx.ts`**
   - Hono route that generates DOCX
   - Returns as download or R2 upload
   - Demonstrate Workers compatibility

2. **Create `templates/workers-pdf-browser.ts`**
   - HTML→PDF using Browser Rendering API
   - Template-based generation
   - Invoice/report example

3. **Add Workers section to SKILL.md**
   - Browser Rendering setup
   - Binding configuration
   - Cost considerations (paid feature)

4. **Add wrangler.jsonc snippet to references**
   - Browser Rendering binding example
   - R2 binding for storage

### Exit Criteria
- [ ] Workers DOCX template works
- [ ] Browser Rendering PDF example documented
- [ ] SKILL.md has Workers section
- [ ] Clear note about Browser Rendering being paid feature

---

## Phase 6: Polish & Marketplace (~30 min)

**Type**: Finalization
**Goal**: Complete skill, generate manifest, test installation

### Tasks

1. **Review and polish SKILL.md**
   - Ensure consistent formatting
   - Add "Use when" scenarios
   - Document limitations clearly
   - Add error prevention tips

2. **Finalize README.md keywords**
   - All format names (docx, xlsx, pdf, word, excel)
   - Use case keywords (invoice, report, export, spreadsheet)
   - Error keywords users might search

3. **Create `scripts/verify-deps.sh`**
   - Check docx, xlsx, pdf-lib versions
   - Output compatibility status

4. **Generate marketplace manifest**
   ```bash
   ./scripts/generate-plugin-manifests.sh office
   ```

5. **Test local installation**
   ```bash
   /plugin install ./skills/office
   ```

6. **Verify skill triggers correctly**
   - Ask Claude Code to "create a Word document"
   - Verify skill is discovered and proposed

### Exit Criteria
- [ ] SKILL.md polished and complete
- [ ] README.md has comprehensive keywords
- [ ] Manifest generated in `.claude-plugin/plugin.json`
- [ ] Local installation works
- [ ] Skill triggers on relevant queries

---

## Success Criteria (MVP Complete)

- [ ] `/plugin install office` works from marketplace
- [ ] DOCX: Create documents with headings, paragraphs, tables, images
- [ ] XLSX: Create spreadsheets with data, formulas, formatting
- [ ] PDF: Create PDFs, fill forms, merge documents
- [ ] All templates work in Node.js AND Cloudflare Workers
- [ ] Follows claude-skills standards (verified via checklist)
- [ ] Clear documentation of limitations vs Anthropic's skills

---

## Phase 2 Roadmap (Post-MVP)

After MVP is complete and validated:

1. **PPTX Generation** - Add PowerPoint support using pptxgenjs
2. **Template Filling** - Fill placeholders in existing DOCX/XLSX
3. **Advanced DOCX** - Headers, footers, table of contents
4. **Reading Files** - Parse existing Office documents
5. **CSV/JSON Export** - Data format conversions
