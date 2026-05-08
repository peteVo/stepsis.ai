import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execPromise = promisify(exec);

export async function POST(req: Request) {
  try {
    const { prompt } = await req.json();
    
    // Path to the root run.sh
    const rootDir = path.resolve(process.cwd(), "../../..");
    const runScript = path.join(rootDir, "run.sh");

    console.log(`🚀 Triggering Pipeline for prompt: "${prompt}"`);

    // THE FIX: 
    // 1. 'bash -l -c' forces a login shell so it loads ~/.bashrc and finds Conda!
    // 2. maxBuffer: 1024 * 1024 * 50 gives it 50MB of terminal output space so it never chokes.
    // 3. We pass process.env so it inherits your system's PATH variables.
    const command = `bash -l -c "${runScript} '${prompt}'"`;
    
    const { stdout, stderr } = await execPromise(command, { 
        cwd: rootDir,
        maxBuffer: 1024 * 1024 * 50, 
        env: { ...process.env } 
    });

    console.log("✅ Pipeline Output Log:\n", stdout);
    if (stderr) console.warn("⚠️ Pipeline Warnings:\n", stderr);

    // Find the newly generated UI Payload
    const extractionDir = path.join(rootDir, "output/extraction");
    const files = await fs.readdir(extractionDir);
    
    const latestFile = files
      .filter(f => f.startsWith("ui_payload") && f.endsWith(".json"))
      .sort((a, b) => {
         const numA = parseInt(a.replace(/\D/g, '')) || 0;
         const numB = parseInt(b.replace(/\D/g, '')) || 0;
         return numB - numA;
      })[0];

    if (!latestFile) throw new Error("Pipeline finished but no ui_payload.json was found.");

    const data = await fs.readFile(path.join(extractionDir, latestFile), 'utf-8');
    
    return NextResponse.json(JSON.parse(data));

  } catch (error: any) {
    console.error("🚨 Critical API Error:", error);
    return NextResponse.json({ error: error.message || "Pipeline execution failed" }, { status: 500 });
  }
}