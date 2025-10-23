# Tasks: Wildberries Stock Tracker

**Input**: Design documents from `/specs/001-wildberries-stock-tracker/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**🚨 CRITICAL API REFERENCE**: ALL development must reference `urls.md` file which contains complete Wildberries API documentation, endpoints, parameters, and calculation logic. Verify EVERY implementation against this file.

**Tests**: Tests are not explicitly requested in the specification, so they are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths follow Python package structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (src/stock_tracker/, tests/, config/)
- [x] T002 Initialize Python project with requirements.txt (gspread, requests, pytest, APScheduler, pydantic)
- [x] T003 [P] Configure .gitignore for Python project with secrets exclusion
- [x] T004 [P] Create .env.example template file
- [x] T005 [P] Setup basic logging configuration in src/stock_tracker/utils/logger.py
- [x] T006 [P] Create main entry point in src/stock_tracker/main.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create configuration management in src/stock_tracker/utils/config.py
- [x] T008 [P] Implement Google Sheets authentication setup in src/stock_tracker/database/sheets.py
- [x] T009 [P] Implement Wildberries API client base in src/stock_tracker/api/client.py (**MUST reference urls.md for exact endpoints and parameters**)
- [x] T010 [P] Create Product dataclass in src/stock_tracker/core/models.py (**MUST match fields from urls.md: supplierArticle, nmId**)
- [x] T011 [P] Create Warehouse dataclass in src/stock_tracker/core/models.py (**MUST match warehouseName, quantity from urls.md**)
- [x] T012 [P] Create SyncSession dataclass in src/stock_tracker/core/models.py
- [x] T013 Create data validation utilities in src/stock_tracker/core/validator.py (**MUST validate against urls.md data types**)
- [x] T014 Create calculation utilities in src/stock_tracker/core/calculator.py (**MUST implement logic from urls.md calculation section**)
- [x] T015 Create error handling and custom exceptions in src/stock_tracker/utils/exceptions.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create Product Inventory Record (Priority: P1) 🎯 MVP

**Goal**: Продавец может создать запись о товаре с основными данными: артикул продавца, артикул Wildberries, общие заказы и остатки, что позволяет начать базовый учет товаров.

**Independent Test**: Можно полностью протестировать созданием одной записи товара и проверкой корректности сохранения всех основных полей.

### Implementation for User Story 1

- [ ] T016 [P] [US1] Implement Google Sheets table structure management in src/stock_tracker/database/structure.py
- [ ] T017 [P] [US1] Implement basic product data formatting in src/stock_tracker/core/formatter.py
- [ ] T018 [US1] Implement Google Sheets CRUD operations in src/stock_tracker/database/operations.py
- [ ] T019 [US1] Create product creation/update logic in src/stock_tracker/services/analytics.py
- [ ] T020 [US1] Implement turnover calculation logic (handles division by zero)
- [ ] T021 [US1] Add product validation (unique seller articles, non-negative values)
- [ ] T022 [US1] Implement basic sheet formatting (headers, number formats)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Manage Multi-Warehouse Data (Priority: P2)

**Goal**: Продавец может добавить данные по нескольким складам для одного товара, указав название склада, заказы и остатки по каждому складу в структурированном виде.

**Independent Test**: Можно протестировать добавлением данных по 2-3 складам для одного товара и проверкой синхронизации порядка данных в колонках F, G, H.

### Implementation for User Story 2

- [x] T023 [P] [US2] Implement multi-warehouse data handling in src/stock_tracker/core/formatter.py
- [x] T024 [P] [US2] Create warehouse data processing logic in src/stock_tracker/api/warehouses.py
- [x] T025 [US2] Implement synchronized data ordering for columns F, G, H
- [x] T026 [US2] Add multi-line cell formatting with newline characters
- [x] T027 [US2] Implement warehouse data validation and synchronization checks
- [x] T028 [US2] Add text wrapping and cell formatting for warehouse columns

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Automatic Calculations and Aggregation (Priority: P3)

**Goal**: Система автоматически рассчитывает общие показатели (суммы заказов и остатков по всем складам) и обновляет оборачиваемость при изменении данных по отдельным складам.

**Independent Test**: Можно протестировать изменением данных по отдельным складам и проверкой автоматического пересчета общих показателей.

### Implementation for User Story 3

- [x] T029 [P] [US3] Implement Wildberries API data fetching in src/stock_tracker/api/products.py (**MUST use /supplier/orders endpoint per urls.md**)
- [x] T030 [P] [US3] Create automatic aggregation logic in src/stock_tracker/core/calculator.py (**MUST follow calculation logic from urls.md**)
- [x] T031 [US3] Implement data synchronization service in src/stock_tracker/services/sync.py (**MUST handle task creation + download workflow from urls.md**)
- [x] T032 [US3] Add automatic recalculation triggers (**MUST verify against urls.md grouping logic**)
- [x] T033 [US3] Implement batch data processing for multiple warehouses (**MUST handle /warehouse_remains task workflow from urls.md**)
- [x] T034 [US3] Create scheduling service in src/stock_tracker/services/scheduler.py
- [x] T035 [US3] Implement daily sync at 00:00 using APScheduler
- [x] T036 [US3] Add sync session tracking and error handling (**MUST handle API rate limits mentioned in urls.md**)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T037 [P] Add comprehensive error logging and monitoring
- [ ] T038 [P] Implement configuration validation with pydantic
- [ ] T039 [P] Add retry logic for API calls with exponential backoff (**MUST handle API timeouts per urls.md**)
- [ ] T040 [P] Implement rate limiting for Wildberries API calls (**MUST respect API limits documented in urls.md**)
- [ ] T041 [P] Create health check utilities in src/stock_tracker/utils/health.py
- [ ] T042 [P] Add command-line interface for manual operations
- [ ] T043 Code cleanup and refactoring across all modules (**MUST verify all API calls match urls.md exactly**)
- [ ] T044 Performance optimization for batch operations
- [ ] T045 Security hardening for API credentials storage
- [ ] T046 Run quickstart.md validation and documentation updates

---

## 🚨 CRITICAL: Wildberries API Implementation Requirements

**MANDATORY REFERENCE**: Every developer MUST consult `urls.md` before implementing ANY API-related functionality.

### Key API Endpoints from urls.md:
1. **Warehouse Remains**: `https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains`
2. **Task Download**: `https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download`
3. **Orders Data**: `https://statistics-api.wildberries.ru/api/v1/supplier/orders`

### Required Field Mapping (from urls.md):
- **supplierArticle** (string) → Column A: Артикул продавца
- **nmId** (integer) → Column B: Артикул товара  
- **warehouseName** (string) → Column F: Название склада
- **quantity** (integer) → Column H: Остатки на складе

### Calculation Logic (MUST implement exactly as specified in urls.md):
- **Остатки всего**: Сумма всех quantity для одного nmId со всех складов
- **Заказы всего**: Количество записей в /supplier/orders с одинаковым nmId
- **Заказы по складу**: Количество записей где совпадают nmId + warehouseName
- **Группировка**: По связке supplierArticle + nmId

### API Workflow (MUST follow exactly):
1. Create task via `/warehouse_remains` with required parameters
2. Wait for task completion 
3. Download results via `/tasks/{task_id}/download`
4. Process orders data via `/supplier/orders` with dateFrom parameter

### Validation Checkpoints:
- [ ] **Before T009**: Review warehouse_remains endpoint parameters in urls.md
- [ ] **Before T029**: Review supplier/orders endpoint parameters in urls.md  
- [ ] **Before T031**: Review task creation + download workflow in urls.md
- [ ] **Before T033**: Review field mapping table in urls.md
- [ ] **After each API task**: Verify implementation matches urls.md exactly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 formatting but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses calculation logic from US1 but should be independently testable

### Within Each User Story

- Models before services
- Services before main logic
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Models and utilities within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch core components for User Story 1 together:
Task: "Implement Google Sheets table structure management in src/stock_tracker/database/structure.py"
Task: "Implement basic product data formatting in src/stock_tracker/core/formatter.py"

# Then proceed with integration:
Task: "Implement Google Sheets CRUD operations in src/stock_tracker/database/operations.py"
Task: "Create product creation/update logic in src/stock_tracker/services/analytics.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently - can create and display basic product records
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: basic product tracking!)
3. Add User Story 2 → Test independently → Deploy/Demo (Enhanced: multi-warehouse support!)
4. Add User Story 3 → Test independently → Deploy/Demo (Full: automated sync!)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (basic product records)
   - Developer B: User Story 2 (multi-warehouse support)
   - Developer C: User Story 3 (API integration and automation)
3. Stories complete and integrate independently

---

## Task Count Summary

- **Total Tasks**: 46
- **Setup Phase**: 6 tasks
- **Foundational Phase**: 9 tasks
- **User Story 1**: 7 tasks
- **User Story 2**: 6 tasks  
- **User Story 3**: 8 tasks
- **Polish Phase**: 10 tasks

**Parallel Opportunities**: 23 tasks marked [P] can run in parallel within their phases

**MVP Scope**: Phases 1-3 (22 tasks) deliver a functional product tracking system

---

## Notes

- **🚨 MANDATORY**: Reference `urls.md` for ALL API-related tasks
- **🚨 ONLY USE**: Endpoints documented in `urls.md` - NO other endpoints exist
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Focus on US1 completion for fastest MVP delivery
- API integration in US3 enables full automation
- **CRITICAL**: Every API call must match the exact specifications in `urls.md`
- **VALIDATION**: Before completing any API task, cross-reference with `urls.md` documentation