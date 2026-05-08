import json
import re
import time
from pathlib import Path

# ==========================================
# 1. Core Chunking Logic
# ==========================================
def chunk_markdown_to_json(md_text, source_id):
    chunks = []
    current_header = "Abstract/Metadata" # Default starting header
    search_cursor = 0
    
    # Split the markdown into blocks based on double newlines
    blocks = md_text.split('\n\n')
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Track provenance in the extracted markdown. This is deterministic and
        # survives re-chunking because it is derived from the markdown text itself.
        block_start = md_text.find(block, search_cursor)
        if block_start < 0:
            block_start = md_text.find(block)
        block_end = block_start + len(block) if block_start >= 0 else -1
        if block_start >= 0:
            search_cursor = block_end

        line_start = md_text.count('\n', 0, block_start) + 1 if block_start >= 0 else None
        line_end = md_text.count('\n', 0, block_end) + 1 if block_end >= 0 else None
            
        # 1. Detect Headers (Update the current section metadata)
        if block.startswith('#'):
            match = re.match(r'^#+\s+\*?\*?(.*?)\*?\*?$', block)
            if match:
                current_header = match.group(1).strip()
            chunks.append(create_chunk(source_id, "text", block, current_header, block_start, block_end, line_start, line_end))
            continue

        # 2. Detect Tables
        if block.startswith('|') and '-|' in block:
            chunks.append(create_chunk(source_id, "table", block, current_header, block_start, block_end, line_start, line_end))
            continue
            
        # 3. Detect AI Visual Analysis
        if block.startswith('> [!IMPORTANT]'):
            chunks.append(create_chunk(source_id, "image_analysis", block, current_header, block_start, block_end, line_start, line_end))
            continue

        # 4. Standard Text
        if len(block) > 20: 
            chunks.append(create_chunk(source_id, "text", block, current_header, block_start, block_end, line_start, line_end))

    return chunks

def create_chunk(source_id, content_type, content, header, markdown_start=None, markdown_end=None, line_start=None, line_end=None):
    """Helper to format the JSON exactly to your contract."""
    return {
        "source_id": source_id,
        "page_number": 1,
        "content_type": content_type,
        "raw_content": content,
        "metadata": {
            "section_header": header,
            "coordinates": [0, 0, 0, 0],
            "markdown_start": markdown_start,
            "markdown_end": markdown_end,
            "markdown_line_start": line_start,
            "markdown_line_end": line_end,
        }
    }

# ==========================================
# 2. Batch Processing & Skip Logic
# ==========================================
def process_single_md(md_path: Path):
    """
    Processes a single MD file. Returns:
    - "success" if chunked
    - "skipped" if JSON already exists
    - "error" if failed
    """
    source_id = md_path.stem
    json_out_path = md_path.parent / f"{source_id}_chunks.json"

    # --- SKIP LOGIC ---
    if json_out_path.exists():
        try:
            existing = json.loads(json_out_path.read_text(encoding="utf-8"))
            has_provenance = bool(
                existing
                and isinstance(existing, list)
                and isinstance(existing[0], dict)
                and isinstance(existing[0].get("metadata"), dict)
                and "markdown_start" in existing[0]["metadata"]
                and "markdown_end" in existing[0]["metadata"]
            )
            if has_provenance:
                return "skipped"
        except Exception:
            # If the file is malformed or unreadable, regenerate it.
            pass
    # ------------------

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        json_output = chunk_markdown_to_json(md_content, source_id)
        
        with open(json_out_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=4, ensure_ascii=False)
            
        return "success"
        
    except Exception as e:
        print(f"❌ Error processing {md_path.name}: {e}")
        return "error"

def batch_process_markdowns(base_dir="extracted_markdowns"):
    base_path = Path(base_dir)
    
    if not base_path.exists() or not base_path.is_dir():
        print(f"❌ Error: Directory '{base_dir}' does not exist.")
        return

    # Find all .md files. We target files matching the parent folder name 
    # to avoid accidentally chunking leftover temp files.
    # E.g., extracted_markdowns/Baloch_2022/Baloch_2022.md
    md_files = [
        p for p in base_path.rglob("*.md") 
        if p.stem == p.parent.name
    ]
    
    if not md_files:
        print(f"⚠️ No matching Markdown files found in '{base_dir}'.")
        return
        
    print(f"🔍 Found {len(md_files)} Markdown files. Starting batch chunking...\n")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    start_time = time.time()
    
    for i, md_path in enumerate(md_files, 1):
        status = process_single_md(md_path)
        
        if status == "skipped":
            print(f"[{i}/{len(md_files)}] ⏭️  Skipped: {md_path.name} (Chunks already exist)")
            skip_count += 1
        elif status == "success":
            print(f"[{i}/{len(md_files)}] ✅ Chunked: {md_path.name}")
            success_count += 1
        else:
            error_count += 1
            
    elapsed_time = round(time.time() - start_time, 2)
    
    # Print the final summary report
    print("\n" + "="*40)
    print("🎉 BATCH CHUNKING COMPLETE 🎉")
    print("="*40)
    print(f"Total MDs found:    {len(md_files)}")
    print(f"Newly Chunked:      {success_count}")
    print(f"Skipped (Existing): {skip_count}")
    print(f"Errors:             {error_count}")
    print(f"Time taken:         {elapsed_time} seconds")

# ==========================================
# Run the script
# ==========================================
if __name__ == "__main__":
    # Resolve target directory relative to this script so it works regardless of cwd
    script_dir = Path(__file__).resolve().parent
    TARGET_DIRECTORY = script_dir.joinpath("extracted_markdowns").resolve()
    batch_process_markdowns(str(TARGET_DIRECTORY))
