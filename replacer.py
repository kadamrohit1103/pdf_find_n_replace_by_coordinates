import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from exceptions import ErrorCode, UserFriendlyError
from utils import setup_logger

class PDFTextReplacer:
    def __init__(self, input_file: str, verbose: bool = False):
        self.input_file = input_file
        self.verbose = verbose
        self.logger = setup_logger(verbose)
        self.pdf = None
        self.replacements = []
        self.fonts = {}
        
        self._load_pdf()

    def _load_pdf(self):
        """Loads the PDF file."""
        try:
            self.pdf = fitz.open(self.input_file)
            self.logger.info(f"PDF loaded: {self.input_file} ({self.pdf.page_count} pages)")
        except Exception as e:
            raise UserFriendlyError(
                error_code=ErrorCode.FILE_NOT_FOUND,
                user_message=f"Failed to load PDF file: {self.input_file}",
                technical_details=str(e),
                suggested_fix="Check if the file exists and is a valid PDF."
            )

    def load_fonts(self, font_config: Dict):
        """Loads custom fonts from configuration."""
        # Placeholder for font loading logic
        pass

    def parse_page_ranges(self, page_str: str) -> List[int]:
        """Convert page range string to list of page numbers (1-based)."""
        try:
            pages = set()
            if page_str.strip() == "*":
                return list(range(1, self.pdf.page_count + 1))
            
            for part in page_str.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    pages.update(range(start, end + 1))
                else:
                    pages.add(int(part))
            
            valid_pages = sorted(pages)
            # basic validation
            if not valid_pages:
                 return []
            if valid_pages[-1] > self.pdf.page_count:
                 raise ValueError(f"Page {valid_pages[-1]} out of range (max {self.pdf.page_count})")
            
            return valid_pages
        except Exception as e:
            raise UserFriendlyError(
                error_code=ErrorCode.PAGE_OUT_OF_RANGE,
                user_message=f"Invalid page range: {page_str}",
                technical_details=str(e),
                suggested_fix="Use format '1', '1-5', or '1,3,5'"
            )

    def extract_text_in_bbox(self, page, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """Extracts text objects within a bounding box."""
        try:
            x0, y0, x1, y1 = bbox
            target_rect = fitz.Rect(x0, y0, x1, y1)
            
            text_objects = []
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block: continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        span_rect = fitz.Rect(span["bbox"])
                        
                        # Check strictly if span is inside or significantly overlaps
                        if target_rect.intersects(span_rect):
                            # Calculate intersection area
                            intersection = target_rect & span_rect
                            if intersection.is_empty:
                                continue
                                
                            text_objects.append({
                                "text": span["text"],
                                "bbox": span["bbox"],
                                "font": span.get("font", "Unknown"),
                                "size": span.get("size", 0),
                                "color": span.get("color", 0),
                                "origin": span.get("origin", (0, 0))
                            })
            return text_objects
            
        except Exception as e:
            raise UserFriendlyError(
                error_code=ErrorCode.TEXT_NOT_FOUND,
                user_message="Failed to extract text from region",
                technical_details=str(e),
                suggested_fix="Verify coordinates and page content."
            )

    def detect_overlapping_text(self, page, target_bbox: Tuple, find_text: str) -> List[Dict]:
        """Detects text that overlaps the target region but is NOT the text we want to replace."""
        x0, y0, x1, y1 = target_bbox
        target_rect = fitz.Rect(x0, y0, x1, y1)
        
        overlapping = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block: continue
            
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text: continue
                    
                    span_rect = fitz.Rect(span["bbox"])
                    
                    if target_rect.intersects(span_rect):
                        # If the text is NOT what we are looking for (allowing for some fuzzy match or strict inequality)
                        # We use strict inequality here as per requirement
                        if text != find_text:
                            overlapping.append({
                                "text": text,
                                "bbox": span["bbox"]
                            })
        return overlapping

    def _get_text_chars(self, page, target_span: Dict) -> List[fitz.Rect]:
        """Gets bounding boxes for individual characters in the span."""
        # We need to re-parse using rawdict to get characters, identifying the specific span is tricky.
        # So we look for the span that matches our target_span's bbox exactly.
        raw_dict = page.get_text("rawdict")
        target_bbox = fitz.Rect(target_span["bbox"])
        char_rects = []
        
        for block in raw_dict["blocks"]:
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    # Match span by bbox (approximate check due to floats)
                    span_bbox = fitz.Rect(span["bbox"])
                    if abs(span_bbox.x0 - target_bbox.x0) < 0.1 and \
                       abs(span_bbox.y0 - target_bbox.y0) < 0.1:
                           # Found the span, get chars
                           for char in span["chars"]:
                               char_rects.append(fitz.Rect(char["bbox"]))
                           return char_rects
        return [target_bbox] # Fallback to full bbox if not found

    def load_fonts(self, font_config: Dict):
        """Loads custom fonts from configuration."""
        try:
            custom_paths = font_config.get("custom_font_paths", {})
            self.default_font = font_config.get("default_font")
            
            for name, path in custom_paths.items():
                if Path(path).exists():
                    self.fonts[name] = path
                    self.logger.info(f"Registered custom font: {name} -> {path}")
                else:
                    self.logger.warning(f"Custom font file not found: {path}")
                    
        except Exception as e:
            raise UserFriendlyError(
                error_code=ErrorCode.FONT_LOAD_FAILED,
                user_message="Failed to load fonts configuration",
                technical_details=str(e),
                suggested_fix="Check font paths in JSON."
            )

    def _perform_replacement(self, page, text_objects: List[Dict], new_text: str, specific_font_key: str = None, lift_font_key: str = None):
        """Performs replacement on a group of text objects (deduplicated)."""
        # 1. Get precise character bboxes from ALL objects to create the Redaction Zone
        all_char_rects = []
        target_bboxes = [fitz.Rect(obj["bbox"]) for obj in text_objects]
        primary_object = text_objects[0] # Use first object for font props
        
        for obj in text_objects:
            chars = self._get_text_chars(page, obj)
            all_char_rects.extend(chars)
            
        if not all_char_rects:
             return
        
        # 2. Compute union rect
        union_rect = fitz.Rect(all_char_rects[0])
        for r in all_char_rects[1:]:
            union_rect.include_rect(r)
            
        # 3. LIFT: Identify overlapping text that needs preservation
        preserved_texts = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
             if "lines" not in block: continue
             for line in block["lines"]:
                 for span in line["spans"]:
                     span_rect = fitz.Rect(span["bbox"])
                     
                     if union_rect.intersects(span_rect):
                         # Check if this span is one of our targets (fuzzy match bbox)
                         is_target = False
                         for tb in target_bboxes:
                             # Overlap area with target > 90% of span area? Or simpler: strictly same text?
                             # Given "Bold" text is just slightly offset, bbox might not match exactly.
                             # But we know the TEXT content should match.
                             # If span is in our `text_objects` list?
                             # Let's check center distance or high IOA
                             if abs(span_rect.x0 - tb.x0) < 1.0 and abs(span_rect.y0 - tb.y0) < 1.0:
                                 is_target = True
                                 break
                         
                         if not is_target:
                             preserved_texts.append({
                                 "text": span["text"],
                                 "origin": span["origin"],
                                 "size": span["size"],
                                 "font": span["font"],
                                 "color": span["color"]
                             })
                             self.logger.info(f"Lifting overlapping text for restoration: '{span['text']}' at {span['bbox']}")

        # 4. REDACT
        page.add_redact_annot(union_rect)
        page.apply_redactions()
        
        # 5. RESTORE
        for p_text in preserved_texts:
            color = fitz.sRGB_to_pdf(p_text["color"]) if isinstance(p_text["color"], int) else (0,0,0)
            
            restore_fontname = "helv"
            restore_fontfile = None
            p_font_name = p_text["font"]
            
            # 1. Explicit Lift Font (Highest Priority)
            if lift_font_key and lift_font_key in self.fonts:
                 restore_fontfile = self.fonts[lift_font_key]
                 safe_key = lift_font_key.replace(" ", "_")
                 restore_fontname = f"cust_{safe_key}"
                 self.logger.debug(f"Restoring with explicit lift font: {lift_font_key}")
            
            # 2. Heuristic Matching (Fallback)
            else:
                for loaded_name, loaded_path in self.fonts.items():
                    if loaded_name.lower() in p_font_name.lower():
                        restore_fontname = loaded_name
                        restore_fontfile = loaded_path
                        self.logger.debug(f"Restoring with detected font: {p_font_name} -> {loaded_name}")
                        break
            
            try:
                page.insert_text(p_text["origin"], p_text["text"], fontsize=p_text["size"], color=color, fontname=restore_fontname, fontfile=restore_fontfile)
            except Exception as e:
                self.logger.warning(f"Failed to restore text '{p_text['text']}': {e}")
        
        # 6. INSERT
        font_size = primary_object["size"]
        color = fitz.sRGB_to_pdf(primary_object["color"]) if isinstance(primary_object["color"], int) else (0,0,0)
        
        # Determine font
        fontname = "helv"
        fontfile = None
        
        # Logic: Specific > Default > Fallback
        selected_font_key = None
        
        if specific_font_key and specific_font_key in self.fonts:
             selected_font_key = specific_font_key
        elif hasattr(self, 'default_font') and self.default_font in self.fonts:
             selected_font_key = self.default_font
             
        if selected_font_key:
             fontfile = self.fonts[selected_font_key]
             # Sanitize key for internal name (remove spaces)
             safe_key = selected_font_key.replace(" ", "_")
             fontname = f"cust_{safe_key}" # Unique internal name
        
        origin = primary_object.get("origin")
        if not origin:
             origin = (union_rect.x0, union_rect.y1)
        
        try:
            page.insert_text(origin, new_text, fontsize=font_size, color=color, fontname=fontname, fontfile=fontfile)
        except Exception as e:
            self.logger.warning(f"Font insertion failed: {e}. Falling back to default.")
            page.insert_text(origin, new_text, fontsize=font_size, color=color)
        
    def process(self):
        """Main processing loop."""
        self.logger.info("Starting text replacement process...")
        results = {"successful": 0, "failed": 0, "skipped": 0, "details": []}
        
        for rep in self.replacements:
             try:
                rep_id = rep.get("id", "unknown")
                self.logger.info(f"Processing replacement: {rep_id}")
                
                find_text = rep["find_text"]
                replace_text = rep["replace_text"]
                pages = self.parse_page_ranges(rep["pages"])
                coords = rep["coordinates"]
                
                if isinstance(coords, dict):
                    bbox = (coords["x0"], coords["y0"], coords["x1"], coords["y1"])
                else:
                    bbox = tuple(coords)
                
                # Default to True if not specified, unless match_mode is partial where it might be useful to be False
                case_sensitive = rep.get("case_sensitive", True)
                specific_font = rep.get("font") # Extract font key
                lift_font = rep.get("lift_font") # Extract lift font key

                for page_num in pages:
                    page = self.pdf[page_num - 1]
                    matches = self.extract_text_in_bbox(page, bbox)
                    
                    valid_matches = []
                    for m in matches:
                        current_text = m["text"]
                        check_current = current_text if case_sensitive else current_text.lower()
                        check_find = find_text if case_sensitive else find_text.lower()
                        
                        if check_current == check_find:
                            valid_matches.append({"object": m, "final_text": replace_text})
                        elif check_find in check_current:
                            if case_sensitive:
                                new_content = current_text.replace(find_text, replace_text)
                            else:
                                import re
                                pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                                new_content = pattern.sub(replace_text, current_text)
                            valid_matches.append({"object": m, "final_text": new_content})
                    
                    if not valid_matches:
                        self.logger.warning(f"Text '{find_text}' not found on page {page_num}")
                        results["failed"] += 1
                        results["details"].append({"id": rep_id, "page": page_num, "status": "FAILED", "reason": "Text not found"})
                        continue
                        
                    # GROUPING LOGIC (Deduplicate overlapping duplicates)
                    groups = []
                    for match in valid_matches:
                        match_rect = fitz.Rect(match["object"]["bbox"])
                        added_to_group = False
                        for group in groups:
                            # If intersect, join group
                            # Or if very close (handling bold/shadow)
                            group_rect = fitz.Rect(group[0]["object"]["bbox"])
                            if match_rect.intersects(group_rect) or \
                               (abs(match_rect.x0 - group_rect.x0) < 5 and abs(match_rect.y0 - group_rect.y0) < 5):
                                group.append(match)
                                added_to_group = True
                                break
                        if not added_to_group:
                            groups.append([match])
                    
                    # Process Groups
                    for group in groups:
                        # Collect all objects in group
                        group_objects = [g["object"] for g in group]
                        final_text = group[0]["final_text"] # Assume all in group become same text
                        
                        self._perform_replacement(page, group_objects, final_text, specific_font, lift_font)
                        
                    results["successful"] += len(groups) # Count distinct regions replaced
                    results["details"].append({"id": rep_id, "page": page_num, "status": "SUCCESS", "count": len(groups)})
                    
             except Exception as e:
                 self.logger.error(f"Error processing replacement {rep.get('id')}: {e}")
                 results["failed"] += 1
                 results["details"].append({"id": rep.get('id'), "status": "ERROR", "error": str(e)})
        
        return results

    def save(self, output_file: str):
        """Saves the modified PDF."""
        try:
            self.pdf.save(output_file)
            self.logger.info(f"PDF saved to: {output_file}")
        except Exception as e:
             raise UserFriendlyError(
                error_code=ErrorCode.PERMISSION_DENIED,
                user_message=f"Failed to save output PDF: {output_file}",
                technical_details=str(e),
                suggested_fix="Check file permissions and ensure target directory exists."
            )
