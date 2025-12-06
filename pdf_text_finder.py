import fitz
import json
import csv
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import math

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Find text in PDF and output coordinates/font stats to CSV.")
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def load_config(config_path: str) -> Dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        exit(1)

def parse_page_ranges(page_str: str, max_pages: int) -> List[int]:
    """Convert page range string to list of page numbers (1-based)."""
    try:
        pages = set()
        if page_str.strip() == "*":
            return list(range(1, max_pages + 1))
        
        for part in page_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
        return sorted(list(pages))
    except Exception as e:
        logger.error(f"Invalid page range '{page_str}': {e}")
        return []

class FontMapper:
    def __init__(self, doc):
        self.doc = doc
        self.font_cache = {} # {internal_name: real_name}
        self.xref_cache = {} # {xref: real_name}

    def get_real_font_name(self, page, internal_name: str) -> str:
        """
        Resolves the true font name from the PDF internal name (e.g., 'CIDFont+F1').
        """
        # 1. Check cache first
        if internal_name in self.font_cache:
            return self.font_cache[internal_name]

        # 2. Find font info in page resources
        # page.get_fonts() returns list of (xref, ext, type, basefont, name, identity)
        fonts = page.get_fonts()
        target_font = None
        
        for f in fonts:
            # f[4] is usually the internal name/alias used in text spans (e.g., 'F1')
            # f[3] is basefont (e.g., 'CIDFont+F1')
            # We match against the basefont name usually returned by get_text("dict")
            if f[3] == internal_name or f[4] == internal_name:
                target_font = f
                break
        
        # If we can't find it in the list, just return the messy name
        if not target_font:
            self.font_cache[internal_name] = internal_name
            return internal_name

        xref = target_font[0]
        
        # 3. Check xref cache
        if xref in self.xref_cache:
            real_name = self.xref_cache[xref]
            self.font_cache[internal_name] = real_name # Link internal name to result
            return real_name

        # 4. Deep Inspection: Extract binary to find true name
        try:
            font_data = self.doc.extract_font(xref)
            if font_data:
                font_binary = font_data[3]
                ff = fitz.Font(fontbuffer=font_binary)
                real_name = ff.name
                
                # Update caches
                self.xref_cache[xref] = real_name
                self.font_cache[internal_name] = real_name
                return real_name
        except Exception:
            pass # Fallback to basefont if extraction fails

        # Fallback: Clean up basefont name (remove + prefix)
        basefont = target_font[3]
        if "+" in basefont:
            basefont = basefont.split("+")[-1]
        
        self.xref_cache[xref] = basefont
        self.font_cache[internal_name] = basefont
        return basefont

def get_text_matches(page, search_text: str, match_mode: str, font_mapper: FontMapper) -> List[Dict]:
    """Finds text matches on a page with font details."""
    matches = []
    text_dict = page.get_text("dict")
    
    search_text_lower = search_text.lower()
    
    for block in text_dict["blocks"]:
        if "lines" not in block: continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_text = span["text"]
                span_text_lower = span_text.lower()
                
                is_match = False
                if match_mode == "exact":
                    if span_text_lower == search_text_lower:
                        is_match = True
                else: # partial
                    if search_text_lower in span_text_lower:
                        is_match = True
                
                if is_match:
                    # Resolve font name
                    raw_font_name = span["font"]
                    real_font_name = font_mapper.get_real_font_name(page, raw_font_name)
                    
                    matches.append({
                        "text": span_text,
                        "bbox": span["bbox"],
                        "font": real_font_name,
                        "size": span["size"],
                        "color": span["color"],
                        "origin": span["origin"],
                        "flags": span["flags"] # Contains bold/italic info
                    })
    return matches

import time

def save_csv_safe(output_file: str, matches: List[Dict]):
    """Saves CSV with retry logic for handling open files."""
    fieldnames = [
        'Search_Term', 'Page', 'Match_Text', 'Font_Name', 'Font_Size', 
        'Flags', 'BBox_x0', 'BBox_y0', 'BBox_x1', 'BBox_y1'
    ]
    
    target_file = output_file
    
    # Attempt to save
    for attempt in range(60): # 60 seconds (approx, assuming 1s sleep)
        try:
            with open(target_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for m in matches:
                    writer.writerow({
                        'Search_Term': m["search_term"],
                        'Page': m["page"],
                        'Match_Text': m["text"],
                        'Font_Name': m["font"],
                        'Font_Size': f"{m['size']:.2f}",
                        'Flags': m["flags"],
                        'BBox_x0': f"{m['bbox'][0]:.4f}",
                        'BBox_y0': f"{m['bbox'][1]:.4f}",
                        'BBox_x1': f"{m['bbox'][2]:.4f}",
                        'BBox_y1': f"{m['bbox'][3]:.4f}"
                    })
            logger.info(f"Successfully saved to {target_file}")
            return
        except PermissionError:
            if attempt == 0:
                 logger.warning(f"File {target_file} is open. Please close it within 60 seconds...")
            
            if attempt % 10 == 0:
                 print(f"Waiting for file to close... ({60 - attempt}s remaining)")
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
            return

    # If timeout reached
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{Path(target_file).stem}_{timestamp}.csv"
    logger.warning(f"Timeout reached. Saving to new file: {new_filename}")
    save_csv_safe(new_filename, matches) # Recursive call (should succeed as name is new)

def main():
    args = parse_arguments()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    config = load_config(args.config)
    input_file = config["input_file"]
    output_csv = config["output_csv"]
    
    if not Path(input_file).exists():
        logger.error(f"Input file not found: {input_file}")
        return

    doc = fitz.open(input_file)
    all_matches = []
    
    doc = fitz.open(input_file)
    font_mapper = FontMapper(doc)
    all_matches = []
    
    logger.info(f"Scanning {input_file} ({doc.page_count} pages)...")
    
    for search_cfg in config["searches"]:
        find_text = search_cfg["text"]
        match_mode = search_cfg.get("match_mode", "partial")
        page_range = search_cfg.get("pages", "*")
        
        pages = parse_page_ranges(page_range, doc.page_count)
        
        logger.info(f"Searching for '{find_text}' ({match_mode}) on pages {page_range}...")
        
        for p_num in pages:
            if p_num > doc.page_count: continue
            page = doc[p_num - 1]
            page_matches = get_text_matches(page, find_text, match_mode, font_mapper)
            
            for m in page_matches:
                m["page"] = p_num
                m["search_term"] = find_text 
                all_matches.append(m)
        
    # Write to CSV
    if not all_matches:
        logger.warning("No matches found.")
    else:
        logger.info(f"Writing {len(all_matches)} matches...")
        save_csv_safe(output_csv, all_matches)
    
    logger.info("Done.")

if __name__ == "__main__":
    main()
