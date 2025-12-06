import argparse
import sys
from pathlib import Path
from replacer import PDFTextReplacer
from config import ConfigLoader
from exceptions import UserFriendlyError
import json

def main():
    parser = argparse.ArgumentParser(description="PDF Engineering Drawing Text Replacement Tool")
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = ConfigLoader.load(args.config)
        ConfigLoader.validate(config)
        
        # Initialize replacer
        replacer = PDFTextReplacer(config["input_file"], verbose=args.verbose)
        
        # Load fonts
        if "fonts" in config:
            replacer.load_fonts(config["fonts"])

        # Setup replacements list
        replacer.replacements = config["replacements"]
        
        # Process (Placeholders for now)
        results = replacer.process()
        
        # Save output
        replacer.save(config["output_file"])
        
        # Validation
        if config.get("validation", {}).get("verify_after_replacement", True):
             print("\nVerifying replacements...")
             verify_replacer = PDFTextReplacer(config["output_file"], verbose=False) # Inspect output
             for rep in config["replacements"]:
                 pages = verify_replacer.parse_page_ranges(rep["pages"])
                 coords = rep["coordinates"]
                 
                 # Handle varying coordinate formats
                 if isinstance(coords, dict):
                     bbox = (coords["x0"], coords["y0"], coords["x1"], coords["y1"])
                 else:
                     bbox = tuple(coords)
                 
                 replace_text = rep["replace_text"]
                 
                 for page_num in pages:
                     page = verify_replacer.pdf[page_num - 1]
                     extracted = verify_replacer.extract_text_in_bbox(page, bbox)
                     found_texts = [t["text"] for t in extracted]
                     
                     if any(replace_text in t for t in found_texts):
                         print(f"  [PASS] Replacement '{rep['id']}' verified on page {page_num}.")
                     else:
                         print(f"  [WARN] Replacement '{rep['id']}' NOT found in output on page {page_num}. Found: {found_texts}")
        
        print("\nProcessing Complete.")
        
    except UserFriendlyError as e:
        print(e.format_message())
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
