import os
import base64
import time
import re
from pathlib import Path
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor
from dotenv import load_dotenv

# 1. Setup Environment & Instructor
load_dotenv()
client = instructor.from_openai(OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
))

# 2. Schema (Same as before, optimized for injection)
class ImageContent(BaseModel):
    category: Literal["scientific_graph", "diagram_or_table", "portrait_or_face", "other"] = Field(
        description="Classify the primary content of the image."
    )
    title_or_caption: str = Field(description="A brief title or summary of what the image shows.")
    scientific_data: Optional[str] = Field(
        None, description="If a graph or table, extract key data points, units, and axis labels."
    )
    trends_or_findings: List[str] = Field(
        default_factory=list, description="List of specific observations identified."
    )
    visual_description: str = Field(
        description="Detailed description of visual elements (subjects, layout, colors)."
    )

# 3. Helper: Image Encoding
def encode_image(image_path: Path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# 4. AI Analysis Function
def analyze_image_with_ai(image_path: Path):
    base64_image = encode_image(image_path)
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=ImageContent,
        messages=[
            {
                "role": "system",
                "content": "You are a multimodal research assistant. Analyze images from documents and provide structured data."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image and provide a structured breakdown."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            }
        ],
    )

# 5. Helper: Format the AI Response for Injection
def format_injection_text(data: ImageContent, img_name: str) -> str:
    # We use an HTML comment as a unique "fingerprint" for skip logic
    md = f"\n\n> [!IMPORTANT]\n> **AI Visual Analysis ({img_name})**\n"
    md += f"> **Category:** `{data.category.upper()}` | **Summary:** {data.title_or_caption}\n"
    md += f"> \n> {data.visual_description}\n"
    
    if data.scientific_data:
        md += f"> \n> **Data Points:** {data.scientific_data}\n"
    
    if data.trends_or_findings:
        md += "> \n> **Key Findings:**\n"
        for finding in data.trends_or_findings:
            md += f"> - {finding}\n"
            
    md += f"<!-- analyzed_{img_name} -->\n\n" # Fingerprint
    return md

# 6. Main Injection Loop
def run_contextual_vision(base_dir="extracted_markdowns"):
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"❌ Error: Folder '{base_dir}' not found.")
        return

    # Find all PNGs
    images = list(base_path.glob("**/images/*.png"))
    print(f"🔍 Found {len(images)} images. Checking for contextual injection...")

    for img_path in images:
        img_name = img_path.name
        
        # Determine the parent .md file
        # Pattern: extracted_markdowns/DocName/images/img.png -> extracted_markdowns/DocName/DocName.md
        parent_folder = img_path.parent.parent
        md_file = parent_folder / f"{parent_folder.name}.md"

        if not md_file.exists():
            print(f"⚠️ Could not find parent .md for {img_name}")
            continue

        # Read the current content of the .md file
        with open(md_file, "r", encoding="utf-8") as f:
            full_text = f.read()

        # --- SKIP LOGIC ---
        # Check if the unique fingerprint exists in the file
        if f"<!-- analyzed_{img_name} -->" in full_text:
            print(f"[{parent_folder.name}] ⏭️  Skipping {img_name} (Already analyzed)")
            continue

        print(f"[{parent_folder.name}] 👁️  Analyzing: {img_name}...")
        
        try:
            # 1. Get AI Analysis
            structured_result = analyze_image_with_ai(img_path)
            
            # 2. Format the analysis
            injection_text = format_injection_text(structured_result, img_name)

            # 3. Use Regex to find where this image is referenced and insert after it
            # Matches standard Markdown image syntax pointing to this specific file
            # This looks for something like ![](images/your_image.png)
            pattern = re.compile(rf'(!\[.*?\]\(.*?{re.escape(img_name)}\))')
            
            if pattern.search(full_text):
                # We replace the match with itself + the injection text
                new_text = pattern.sub(rf'\1{injection_text}', full_text)
                
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(new_text)
                print(f"   ✅ Injected analysis below {img_name}")
            else:
                print(f"   ⚠️ Found image file but no reference to it in the .md text.")

            time.sleep(0.5) # Courtesy pause

        except Exception as e:
            print(f"   ❌ Error analyzing {img_name}: {e}")

if __name__ == "__main__":
    # Resolve base folder relative to this script so cwd doesn't matter
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.joinpath("extracted_markdowns").resolve()
    run_contextual_vision(str(base_dir))
