import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET() {
  try {
    // 1. Navigate up to the root where the 'articles' folder lives
    const rootDir = path.resolve(process.cwd(), "../../.."); 
    const articlesDir = path.join(rootDir, "articles");

    // 2. Read the folder and count only .pdf files
    const files = await fs.readdir(articlesDir);
    const pdfCount = files.filter(f => f.toLowerCase().endsWith('.pdf')).length;

    return NextResponse.json({ count: pdfCount });
  } catch (error) {
    console.error("Failed to read articles directory:", error);
    // Fallback to 30 if the folder isn't found
    return NextResponse.json({ count: 30 }); 
  }
}