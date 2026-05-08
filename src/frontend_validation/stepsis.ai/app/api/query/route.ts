import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execPromise = promisify(exec);

export async function POST(req: Request) {
  try {
    const { prompt } = await req.json();
    const rootDir = path.resolve(process.cwd(), "../../..");
    const runScript = path.join(rootDir, "run.sh");

    console.log("🚀 Triggering Pipeline...");
    
    // ADD THE { cwd: rootDir } OPTION HERE
    const { stdout, stderr } = await execPromise(`bash ${runScript} "${prompt}"`, { 
        cwd: rootDir 
    });
    
    console.log("Pipeline Output:", stdout);
    if (stderr) console.error("Pipeline Warnings:", stderr);

    // 3. Find the latest extraction JSON
    const extractionDir = path.join(rootDir, "output/extraction");
    const files = await fs.readdir(extractionDir);
    const latestFile = files
      .filter(f => f.startsWith("ui_payload") && f.endsWith(".json"))
      .sort((a, b) => {
         const numA = parseInt(a.replace(/\D/g, '')) || 0;
         const numB = parseInt(b.replace(/\D/g, '')) || 0;
         return numB - numA;
      })[0];

    const data = await fs.readFile(path.join(extractionDir, latestFile), 'utf-8');
    
    return NextResponse.json(JSON.parse(data));
  } catch (error: any) {
    console.error(error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}