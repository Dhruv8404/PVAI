# Phase 2 Execution Tasks

## Step 1: Database Models & Dependencies
- [x] Install `openpyxl` in the project virtual environment
- [x] Add `openpyxl` to `backend/requirements.txt`
- [x] Add `llm_provider` column to `AIConfiguration` (`backend/app/modules/templates/model.py`)
- [x] Create `ExcelUploadSession` model (`backend/app/modules/templates/model.py`)
- [x] Create `CustomerHeaderMapping` model (`backend/app/modules/templates/model.py`)

## Step 2: Service Layer & Coordinator Implementation
- [x] Create `excel_header_service.py` for reading spreadsheet headers and column indices (`backend/app/modules/templates/services/excel_header_service.py`)
- [x] Create `header_embedding_service.py` for mapping config embeddings (`backend/app/modules/templates/services/header_embedding_service.py`)
- [x] Create `header_similarity_service.py` for ChromaDB cosine similarity queries (`backend/app/modules/templates/services/header_similarity_service.py`)
- [x] Create `llm_mapping_service.py` for LLM mapping checks and fallback logic (`backend/app/modules/templates/services/llm_mapping_service.py`)
- [x] Create `mapping_validator.py` for validating result mapping bounds (`backend/app/modules/templates/services/mapping_validator.py`)
- [x] Create `mapping_cache_service.py` for retrieving and writing cache entries (`backend/app/modules/templates/services/mapping_cache_service.py`)
- [x] Create `header_mapping_coordinator.py` to run the orchestrator mapping pipeline (`backend/app/modules/templates/services/header_mapping_coordinator.py`)

## Step 3: API & Schema Layer
- [x] Update Pydantic schemas in `backend/app/modules/templates/schema.py`
- [x] Register new endpoints in `backend/app/modules/templates/html_routes.py`

## Step 4: Verification & Tests
- [x] Create test suite `backend/app/tests/test_header_mapping.py`
- [x] Run verification tests and confirm all pass

---

# Phase 3 Execution Tasks

## Step 1: Database Models & Setup
- [x] Create `StandardizedDataset` and `ValidationLog` models (`backend/app/modules/templates/model.py`)

## Step 2: Service Layer & Coordinator Implementation
- [x] Create `excel_data_service.py` to parse spreadsheet rows and attach `_source` provenance (`backend/app/modules/templates/services/excel_data_service.py`)
- [x] Create `data_standardization_service.py` to normalize cell types (`backend/app/modules/templates/services/data_standardization_service.py`)
- [x] Create `file_merge_service.py` to group datasets by expected file label (`backend/app/modules/templates/services/file_merge_service.py`)
- [x] Create `validation_service.py` to execute required fields, types, and duplicate checks (`backend/app/modules/templates/services/validation_service.py`)
- [x] Create `dataset_builder_service.py` to compile metadata, files dictionary, and global statistics (`backend/app/modules/templates/services/dataset_builder_service.py`)
- [x] Create `data_standardization_coordinator.py` to orchestrate pipeline status stages and transaction commits (`backend/app/modules/templates/services/data_standardization_coordinator.py`)

## Step 3: API & Schema Layer
- [x] Update Pydantic schemas in `backend/app/modules/templates/schema.py`
- [x] Register endpoints in `backend/app/modules/templates/html_routes.py`

## Step 4: Verification & Tests
- [x] Create test suite `backend/app/tests/test_standardization.py`
- [x] Run verification tests and confirm all pass

---

# Phase 4 Execution Tasks

## Step 1: Database Models & Setup
- [x] Create `PromptTemplate`, `ReportVersion`, `ReportGeneration`, `ReportAudit`, `AIProcessingLog`, and `LearningHistory` database models (`backend/app/modules/templates/model.py`)

## Step 2: Service Layer & Coordinator Implementation
- [x] Create `prompt_service.py` to retrieve and format database prompts (`backend/app/modules/templates/services/prompt_service.py`)
- [x] Create `section_agents.py` containing modular LLM narrative generators with confidence scores (`backend/app/modules/templates/services/section_agents.py`)
- [x] Create `report_assembler.py` to merge narrative sections with deterministic calculations (`backend/app/modules/templates/services/report_assembler.py`)
- [x] Create `explanation_service.py` to document AI choices (`backend/app/modules/templates/services/explanation_service.py`)
- [x] Create `quality_service.py` to score completeness and suggest recommendations (`backend/app/modules/templates/services/quality_service.py`)
- [x] Create `learning_service.py` to analyze reviewer modifications and log style learnings (`backend/app/modules/templates/services/learning_service.py`)
- [x] Create `feedback_service.py` to save approval details and write audit trails (`backend/app/modules/templates/services/feedback_service.py`)
- [x] Create `report_intelligence_coordinator.py` to orchestrate pipeline stages and save data (`backend/app/modules/templates/services/report_intelligence_coordinator.py`)

## Step 3: API & Schema Layer
- [x] Add Pydantic schemas for Phase 4 (`backend/app/modules/templates/schema.py`)
- [x] Create `report_routes.py` with endpoints for generation, retrieval, approval, feedback, quality, explanation, and audits (`backend/app/modules/templates/report_routes.py`)
- [x] Register new report router in main app router (`backend/app/main.py`)

## Step 4: Verification & Tests
- [x] Create test suite `backend/app/tests/test_report_generation.py`
- [x] Run verification tests and confirm all pass
