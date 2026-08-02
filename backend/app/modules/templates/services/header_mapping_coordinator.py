import logging
import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.exceptions import ValidationException
from app.modules.templates.model import HtmlTemplate, ExcelUploadSession, TemplateField
from app.modules.templates.services.excel_header_service import excel_header_service
from app.modules.templates.services.header_embedding_service import header_embedding_service
from app.modules.templates.services.header_similarity_service import header_similarity_service
from app.modules.templates.services.llm_mapping_service import llm_mapping_service
from app.modules.templates.services.mapping_cache_service import mapping_cache_service
from app.modules.templates.services.template_service import template_service

logger = logging.getLogger(__name__)


class HeaderMappingCoordinator:
    async def match_file_to_expected_type(self, file_name: str, required_files: List[str]) -> str:
        """Helper to match an uploaded file name to the template's required files."""
        clean_name = file_name.lower()
        
        # Word search: first check exact matches
        for req in required_files:
            req_clean = req.lower()
            if req_clean == clean_name:
                return req

        # Substring / token match scoring: score each expected label
        best_req = None
        max_score = 0
        
        for req in required_files:
            req_clean = req.lower()
            parts = req_clean.split()
            
            score = 0
            for p in parts:
                if len(p) >= 2 and p in clean_name:
                    score += 1
            
            # Additional bonus for exact substring match
            if req_clean in clean_name:
                score += 5
                
            if score > max_score:
                max_score = score
                best_req = req
                
        if best_req and max_score > 0:
            return best_req
            
        # Default fallback: return first unmatched required file, or "Unknown"
        return required_files[0] if required_files else "Unknown"


    async def analyze_uploaded_headers(
        self, 
        db: AsyncSession, 
        template_id: uuid.UUID, 
        customer_id: str, 
        files: List[UploadFile]
    ) -> Dict[str, Any]:
        """Orchestrates the entire multi-file header mapping pipeline."""
        logger.info(f"Starting header mapping analysis for template {template_id} (Customer: {customer_id})")
        
        # 1. Fetch template & AI configs
        template = await template_service.get_template(db, template_id)
        ai_config = await template_service.get_ai_config(db)
        
        # 2. Retrieve required logical fields of this template
        stmt_fields = select(TemplateField).where(TemplateField.template_id == template_id)
        res_fields = await db.execute(stmt_fields)
        req_fields = res_fields.scalars().all()
        req_field_names = [f.field_name for f in req_fields]
        
        if not req_field_names:
            raise ValidationException("Template has no required fields registered. Complete Step 2 manifest first.")

        response_files = []
        required_files_list = template.required_files or []

        # 3. Process each spreadsheet file
        for file in files:
            file_name = file.filename or "unknown.xlsx"
            file_content = await file.read()
            await file.seek(0)
            
            # Map file to expected document type
            expected_type = await self.match_file_to_expected_type(file_name, required_files_list)
            logger.info(f"File '{file_name}' matched to expected type: '{expected_type}'")

            # Extract Excel sheet names & headers
            extracted_data = excel_header_service.extract_headers(file_content, file_name)
            detected_sheets = [sheet["sheet_name"] for sheet in extracted_data]

            # Save Upload Session record
            upload_session = ExcelUploadSession(
                template_id=template_id,
                customer_id=customer_id,
                file_name=file_name,
                expected_file_type=expected_type,
                detected_sheet_names=detected_sheets,
                status="Analyzed"
            )
            db.add(upload_session)
            await db.commit()

            file_headers_result = []

            # We process headers on all sheets
            for sheet in extracted_data:
                sheet_name = sheet["sheet_name"]
                headers = sheet["headers"]
                
                header_names = [h["original_header"] for h in headers]
                if not header_names:
                    continue

                # Run similarity searches for this sheet's headers
                for header in headers:
                    header_name = header["original_header"]
                    
                    # A. Check Customer Mapping Cache
                    cached = await mapping_cache_service.get_cached_mapping(
                        db=db,
                        customer_id=customer_id,
                        template_id=template_id,
                        uploaded_header=header_name
                    )
                    
                    if cached:
                        # Cache Hit: Reuse mapping
                        file_headers_result.append({
                            "uploaded": header_name,
                            "mapped": cached.mapped_field,
                            "confidence": cached.confidence,
                            "status": cached.status,
                            "source": "Cache"
                        })
                        continue

                    # B. Generate Embeddings
                    vector = header_embedding_service.generate_header_embedding(header_name)

                    # C. Query Similarity DB
                    nearest = header_similarity_service.find_nearest_fields(
                        template_id=template_id,
                        header_name=header_name,
                        header_embedding=vector,
                        ai_config=ai_config
                    )
                    
                    if not nearest:
                        # No fields matched
                        file_headers_result.append({
                            "uploaded": header_name,
                            "mapped": None,
                            "confidence": 0.0,
                            "status": "NeedsReview",
                            "source": "Manual"
                        })
                        continue

                    best_match = nearest[0]
                    similarity = best_match["similarity"]
                    field_name = best_match["field_name"]

                    if best_match["status"] == "AutoMapped":
                        # High Confidence match
                        file_headers_result.append({
                            "uploaded": header_name,
                            "mapped": field_name,
                            "confidence": similarity,
                            "status": "AutoMapped",
                            "source": "Embedding"
                        })
                        # Cache results for future lookup
                        await mapping_cache_service.save_confirmed_mapping(
                            db=db,
                            customer_id=customer_id,
                            template_id=template_id,
                            uploaded_header=header_name,
                            mapped_field=field_name,
                            confidence=similarity,
                            source="Embedding",
                            status="AutoMapped"
                        )
                    
                    elif best_match["status"] == "NeedsLLM":
                        # Moderate Confidence match: Invoke LLM Verification
                        logger.info(f"Invoking LLM verification mapping for header '{header_name}'")
                        llm_map = await llm_mapping_service.verify_mapping(
                            required_fields=req_field_names,
                            uploaded_headers=[header_name],
                            ai_config=ai_config
                        )
                        
                        # Check if LLM confirmed the mapping
                        confirmed_field = None
                        for r_field, u_header in llm_map.items():
                            if u_header == header_name:
                                confirmed_field = r_field
                                break
                                
                        if confirmed_field:
                            # LLM confirmed the mapping
                            file_headers_result.append({
                                "uploaded": header_name,
                                "mapped": confirmed_field,
                                "confidence": similarity,
                                "status": "AutoMapped",
                                "source": "LLM"
                            })
                            # Save cache
                            await mapping_cache_service.save_confirmed_mapping(
                                db=db,
                                customer_id=customer_id,
                                template_id=template_id,
                                uploaded_header=header_name,
                                mapped_field=confirmed_field,
                                confidence=similarity,
                                source="LLM",
                                status="AutoMapped"
                            )
                        else:
                            # LLM rejected/could not confirm mapping
                            file_headers_result.append({
                                "uploaded": header_name,
                                "mapped": field_name,
                                "confidence": similarity,
                                "status": "NeedsReview",
                                "source": "Manual"
                            })
                            
                    else:
                        # Low Confidence match: Manual Review
                        file_headers_result.append({
                            "uploaded": header_name,
                            "mapped": field_name,
                            "confidence": similarity,
                            "status": "NeedsReview",
                            "source": "Manual"
                        })

            response_files.append({
                "file_name": file_name,
                "expected_type": expected_type,
                "headers": file_headers_result
            })

        return {
            "status": "completed",
            "files": response_files
        }

    async def confirm_manual_mappings(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        customer_id: str,
        mappings: List[Dict[str, Any]]
    ) -> None:
        """Saves user-confirmed manual mappings to the cache database."""
        logger.info(f"Confirming {len(mappings)} manual mappings for customer {customer_id}")
        
        for item in mappings:
            uploaded = item["uploaded_header"]
            mapped = item["mapped_field"]
            
            # Save to cache with "Confirmed" status and "Manual" source
            await mapping_cache_service.save_confirmed_mapping(
                db=db,
                customer_id=customer_id,
                template_id=template_id,
                uploaded_header=uploaded,
                mapped_field=mapped,
                confidence=1.0,
                source="Manual",
                status="Confirmed"
            )


header_mapping_coordinator = HeaderMappingCoordinator()
