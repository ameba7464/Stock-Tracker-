# Tasks: Google Sheets Stock Tracker для Wildberries

**Input**: Design documents from `/specs/master/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL и не включены, так как не были явно запрошены в спецификации.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Google Apps Script project**: `src/stock_tracker/`, `src/sheets/`, `src/config/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic Google Apps Script structure

- [ ] T001 Create project structure per implementation plan: src/stock_tracker/, src/sheets/, src/config/, tests/
- [ ] T002 Initialize Google Apps Script project with base configuration in src/sheets/tracker_template.gs
- [ ] T003 [P] Create configuration module in src/config/settings.js with API tokens and constants
- [ ] T004 [P] Setup error handling utility in src/stock_tracker/utils/error_handler.js
- [ ] T005 [P] Create logging utility in src/stock_tracker/utils/logger.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Setup Wildberries API client in src/stock_tracker/api/wildberries_client.js with authentication
- [ ] T007 Setup Google Sheets operations handler in src/stock_tracker/database/sheets_manager.js
- [ ] T008 [P] Create data validation utilities in src/stock_tracker/utils/validators.js  
- [ ] T009 [P] Implement retry logic and rate limiting in src/stock_tracker/utils/retry_handler.js
- [ ] T010 Create base data transformation service in src/stock_tracker/core/data_processor.js
- [ ] T011 Setup scheduler service for daily triggers in src/stock_tracker/services/scheduler.js

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Учет товаров (Priority: P1) 🎯 MVP

**Goal**: Фиксация артикулов продавца и товара в Google таблице с базовой структурой

**Independent Test**: Создать таблицу с заголовками, добавить тестовые данные и проверить корректность структуры

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create Product entity model in src/stock_tracker/core/models/product.js
- [ ] T013 [P] [US1] Create Warehouse entity model in src/stock_tracker/core/models/warehouse.js
- [ ] T014 [US1] Implement product data service in src/stock_tracker/services/product_service.js (depends on T012, T013)
- [ ] T015 [US1] Create Google Sheets table initialization in src/stock_tracker/database/table_initializer.js
- [ ] T016 [US1] Implement basic data writing to sheets in src/stock_tracker/database/data_writer.js
- [ ] T017 [US1] Add data validation for product articles in src/stock_tracker/core/validators/product_validator.js
- [ ] T018 [US1] Create main orchestration function in src/sheets/tracker_template.gs for US1

**Checkpoint**: At this point, User Story 1 should be fully functional - можно создать таблицу и записать базовые данные товаров

---

## Phase 4: User Story 2 - Агрегация данных (Priority: P2)

**Goal**: Автоматический расчет общих показателей заказов и остатков по всем складам

**Independent Test**: Проверить что колонки "Заказы (всего)" и "Остатки (всего)" правильно суммируют данные по складам

### Implementation for User Story 2

- [ ] T019 [P] [US2] Implement stocks data fetching from Wildberries API in src/stock_tracker/api/stocks_api.js
- [ ] T020 [P] [US2] Implement orders data fetching from Wildberries API in src/stock_tracker/api/orders_api.js
- [ ] T021 [US2] Create data aggregation logic in src/stock_tracker/core/aggregators/warehouse_aggregator.js
- [ ] T022 [US2] Implement 7-day period filtering in src/stock_tracker/core/filters/date_filter.js
- [ ] T023 [US2] Update product service to handle aggregated data in src/stock_tracker/services/product_service.js
- [ ] T024 [US2] Add totals calculation to data writer in src/stock_tracker/database/data_writer.js
- [ ] T025 [US2] Update main orchestration for aggregation workflow in src/sheets/tracker_template.gs

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - таблица показывает как отдельные товары, так и суммарные показатели

---

## Phase 5: User Story 3 - Расчет оборачиваемости (Priority: P3)

**Goal**: Автоматическое вычисление коэффициента оборачиваемости (заказы/остатки)

**Independent Test**: Проверить что колонка "Оборачиваемость" правильно рассчитывается и обрабатывает деление на ноль

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create turnover calculation logic in src/stock_tracker/core/calculators/turnover_calculator.js
- [ ] T027 [P] [US3] Add division by zero handling in src/stock_tracker/utils/math_utils.js
- [ ] T028 [US3] Update product model to include turnover field in src/stock_tracker/core/models/product.js
- [ ] T029 [US3] Integrate turnover calculation into product service in src/stock_tracker/services/product_service.js
- [ ] T030 [US3] Add turnover formatting for Google Sheets in src/stock_tracker/database/formatters/number_formatter.js
- [ ] T031 [US3] Update data writer to include turnover column in src/stock_tracker/database/data_writer.js

**Checkpoint**: User Stories 1, 2, AND 3 should work - таблица показывает товары с правильными расчетами оборачиваемости

---

## Phase 6: User Story 4 - Множественные склады (Priority: P4)

**Goal**: Поддержка нескольких складов для одного товара с отображением через перевод строки

**Independent Test**: Добавить товар с несколькими складами и проверить синхронизацию колонок F, G, H

### Implementation for User Story 4  

- [ ] T032 [P] [US4] Create multi-warehouse data formatter in src/stock_tracker/core/formatters/warehouse_formatter.js
- [ ] T033 [P] [US4] Implement warehouse synchronization validator in src/stock_tracker/core/validators/warehouse_sync_validator.js
- [ ] T034 [US4] Update warehouse aggregator for multi-warehouse support in src/stock_tracker/core/aggregators/warehouse_aggregator.js
- [ ] T035 [US4] Add newline-separated formatting to data writer in src/stock_tracker/database/data_writer.js
- [ ] T036 [US4] Update Google Sheets formatting for text wrapping in src/stock_tracker/database/formatters/cell_formatter.js
- [ ] T037 [US4] Integrate multi-warehouse logic into product service in src/stock_tracker/services/product_service.js

**Checkpoint**: User Stories 1-4 работают - таблица поддерживает товары с множественными складами

---

## Phase 7: User Story 5 - Структурированное отображение (Priority: P5)

**Goal**: Упорядоченное представление данных по складам с правильным форматированием таблицы

**Independent Test**: Проверить что таблица имеет правильные заголовки, форматирование и порядок данных

### Implementation for User Story 5

- [ ] T038 [P] [US5] Create table styling and formatting in src/stock_tracker/database/formatters/table_formatter.js
- [ ] T039 [P] [US5] Implement header formatting (bold, colored background) in src/stock_tracker/database/formatters/header_formatter.js
- [ ] T040 [US5] Add column width and alignment settings in src/stock_tracker/database/formatters/column_formatter.js
- [ ] T041 [US5] Implement data sorting and ordering logic in src/stock_tracker/core/sorters/product_sorter.js  
- [ ] T042 [US5] Update table initializer with complete formatting in src/stock_tracker/database/table_initializer.js
- [ ] T043 [US5] Create final presentation layer in src/stock_tracker/services/presentation_service.js
- [ ] T044 [US5] Complete main workflow integration in src/sheets/tracker_template.gs

**Checkpoint**: Все user stories работают - таблица полностью оформлена и структурирована

---

## Phase 8: Automation & Scheduling

**Goal**: Настройка автоматического ежедневного обновления в 00:00

**Independent Test**: Создать тестовый триггер и проверить автоматическое обновление данных

### Implementation for Automation

- [ ] T045 [P] Create daily trigger setup function in src/stock_tracker/services/scheduler.js
- [ ] T046 [P] Implement update status tracking in src/stock_tracker/services/status_tracker.js
- [ ] T047 Add error notification system in src/stock_tracker/services/notification_service.js
- [ ] T048 Create manual update trigger function in src/sheets/tracker_template.gs
- [ ] T049 Add configuration management for scheduling in src/config/settings.js
- [ ] T050 Implement cleanup and maintenance tasks in src/stock_tracker/services/maintenance_service.js

**Checkpoint**: Система полностью автоматизирована и готова к продакшену

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T051 [P] Add comprehensive error handling across all modules in src/stock_tracker/utils/error_handler.js
- [ ] T052 [P] Implement performance monitoring and logging in src/stock_tracker/utils/performance_monitor.js
- [ ] T053 Create setup and configuration documentation in docs/setup.md  
- [ ] T054 Add API rate limiting and quota management in src/stock_tracker/api/rate_limiter.js
- [ ] T055 [P] Create backup and recovery procedures in src/stock_tracker/services/backup_service.js
- [ ] T056 Run quickstart.md validation and testing
- [ ] T057 Code cleanup and optimization across all modules
- [ ] T058 [P] Add security hardening for API tokens in src/config/security.js

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Automation (Phase 8)**: Depends on all user stories being complete
- **Polish (Phase 9)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 models but independently testable
- **User Story 3 (P3)**: Can start after US2 completion - Requires aggregated data for turnover calculation
- **User Story 4 (P4)**: Can start after US2 completion - Needs aggregation logic for multi-warehouse support
- **User Story 5 (P5)**: Can start after US1 completion - Enhances presentation but independently testable

### Within Each User Story

- Models before services
- API clients before data processing
- Core logic before database operations
- Database operations before main integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes:
  - US1 can start immediately
  - US2 can start immediately (parallel to US1)
  - US3 must wait for US2 completion
  - US4 must wait for US2 completion
  - US5 can start after US1 (parallel to US2/US3/US4)
- All tasks within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 2

```bash
# Launch parallel tasks for User Story 2:
Task: "Implement stocks data fetching from Wildberries API in src/stock_tracker/api/stocks_api.js"
Task: "Implement orders data fetching from Wildberries API in src/stock_tracker/api/orders_api.js" 

# After API tasks complete, launch data processing tasks:
Task: "Create data aggregation logic in src/stock_tracker/core/aggregators/warehouse_aggregator.js"
Task: "Implement 7-day period filtering in src/stock_tracker/core/filters/date_filter.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Basic product tracking)
4. **STOP and VALIDATE**: Test basic table creation and product data entry
5. Deploy/demo basic functionality

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: basic product table)
3. Add User Story 2 → Test independently → Deploy/Demo (adds API integration & aggregation)
4. Add User Story 3 → Test independently → Deploy/Demo (adds turnover calculations)  
5. Add User Story 4 → Test independently → Deploy/Demo (adds multi-warehouse support)
6. Add User Story 5 → Test independently → Deploy/Demo (adds professional formatting)
7. Add Automation → Deploy final automated solution

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + User Story 5 (presentation)
   - Developer B: User Story 2 + User Story 3 (API & calculations)  
   - Developer C: User Story 4 + Automation setup
3. Stories complete and integrate independently

---

## Summary

- **Total Tasks**: 58 tasks
- **Task Count per User Story**: 
  - US1: 7 tasks (basic product tracking)
  - US2: 7 tasks (API integration & aggregation)
  - US3: 6 tasks (turnover calculations)
  - US4: 6 tasks (multi-warehouse support)
  - US5: 7 tasks (formatting & presentation)
- **Parallel Opportunities**: 23 tasks marked [P] for parallel execution
- **Independent Test Criteria**: Each user story has clear validation criteria
- **Suggested MVP Scope**: User Story 1 only (basic product table with manual data entry)

**Format Validation**: ✅ All tasks follow the required checklist format with checkbox, ID, optional [P] and [Story] labels, and file paths