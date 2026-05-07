import pymupdf4llm
import os
import time
from pathlib import Path

def process_single_pdf(pdf_path, base_output_folder):
    """
    Processes a single PDF. Returns:
    - "success" if processed
    - "skipped" if file already exists
    - "error" if something went wrong
    """
    pdf_file = Path(pdf_path)
    
    # Create the folder structure
    doc_out_dir = Path(base_output_folder) / pdf_file.stem
    image_out_dir = doc_out_dir / "images"
    md_filepath = doc_out_dir / f"{pdf_file.stem}.md"

    # --- SKIP LOGIC ---
    if md_filepath.exists():
        return "skipped"
    # ------------------

    os.makedirs(doc_out_dir, exist_ok=True)
    os.makedirs(image_out_dir, exist_ok=True)
    
    try:
        md_text = pymupdf4llm.to_markdown(
            doc=str(pdf_path),
            write_images=True,
            image_path=str(image_out_dir),
            image_format="png",
            #page_chunks=True,
        )
        
        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write(md_text)
            
        return "success"
        
    except Exception as e:
        print(f"❌ Error processing {pdf_file.name}: {e}")
        return "error"

def batch_process_folder(input_folder, output_folder):
    input_dir = Path(input_folder)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"❌ Error: Input folder '{input_folder}' does not exist.")
        return

    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No PDFs found in '{input_folder}'.")
        return
        
    print(f"🔍 Found {len(pdf_files)} PDFs. Starting batch processing...\n")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    start_time = time.time()
    
    for i, pdf_path in enumerate(pdf_files, 1):
        status = process_single_pdf(pdf_path, output_folder)
        
        if status == "skipped":
            print(f"[{i}/{len(pdf_files)}] ⏭️  Skipped: {pdf_path.name}")
            skip_count += 1
        elif status == "success":
            print(f"[{i}/{len(pdf_files)}] ✅ Processed: {pdf_path.name}")
            success_count += 1
        else:
            error_count += 1
            
    elapsed_time = round(time.time() - start_time, 2)
    
    # Print the final summary report
    print("\n" + "="*40)
    print("🎉 BATCH PROCESSING COMPLETE 🎉")
    print("="*40)
    print(f"Total PDFs found:   {len(pdf_files)}")
    print(f"Newly Processed:    {success_count}")
    print(f"Skipped (Existing): {skip_count}")
    print(f"Errors:             {error_count}")
    print(f"Time taken:         {elapsed_time} seconds")
    print(f"Output location:    {Path(output_folder).absolute()}")

if __name__ == "__main__":
    INPUT_DIRECTORY = "../../articles/" 
    OUTPUT_DIRECTORY = "extracted_markdowns"
    
    batch_process_folder(INPUT_DIRECTORY, OUTPUT_DIRECTORY)
