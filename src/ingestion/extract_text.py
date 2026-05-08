import pymupdf4llm
import os
import time
import json
from pathlib import Path


def _serialize_page_chunks(page_chunks):
    serialized = []
    for item in page_chunks or []:
        metadata = dict(item.get("metadata") or {})
        page_number = int(metadata.get("page_number") or 1)
        boxes = []
        for box in item.get("page_boxes") or []:
            pos = box.get("pos") or [None, None]
            bbox = box.get("bbox") or [0, 0, 0, 0]
            boxes.append(
                {
                    "index": box.get("index"),
                    "class": box.get("class"),
                    "bbox": [float(v) for v in bbox],
                    "pos": [int(pos[0]) if pos[0] is not None else None, int(pos[1]) if pos[1] is not None else None],
                }
            )

        serialized.append(
            {
                "page_number": page_number,
                "text": str(item.get("text") or ""),
                "page_boxes": boxes,
            }
        )
    return serialized

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
    provenance_path = doc_out_dir / f"{pdf_file.stem}_provenance.json"

    # --- SKIP LOGIC ---
    if md_filepath.exists() and provenance_path.exists():
        return "skipped"
    # ------------------

    os.makedirs(doc_out_dir, exist_ok=True)
    os.makedirs(image_out_dir, exist_ok=True)
    
    try:
        # Keep the original markdown generation path for compatibility with the image pipeline.
        if not md_filepath.exists():
            md_text = pymupdf4llm.to_markdown(
                doc=str(pdf_path),
                write_images=True,
                image_path=str(image_out_dir),
                image_format="png",
            )

            with open(md_filepath, "w", encoding="utf-8") as f:
                f.write(md_text)

        # Export page-level text and bounding boxes for deterministic provenance mapping.
        if not provenance_path.exists():
            page_chunks = pymupdf4llm.to_markdown(
                doc=str(pdf_path),
                page_chunks=True,
            )
            serialized = {
                "source_id": pdf_file.stem,
                "pages": _serialize_page_chunks(page_chunks),
            }
            provenance_path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
            
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
    # Resolve paths relative to this script so the script works regardless of cwd
    script_dir = Path(__file__).resolve().parent
    INPUT_DIRECTORY = script_dir.joinpath("../../articles/").resolve()
    OUTPUT_DIRECTORY = script_dir.joinpath("extracted_markdowns").resolve()

    batch_process_folder(str(INPUT_DIRECTORY), str(OUTPUT_DIRECTORY))
