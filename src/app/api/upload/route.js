import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { v4 as uuidv4 } from "uuid";

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    const uploadsDir = path.join(process.cwd(), "public", "uploads");
    await fs.mkdir(uploadsDir, { recursive: true });

    const mediaImagesDir = path.join(process.cwd(), "data", "media", "images");
    await fs.mkdir(mediaImagesDir, { recursive: true });

    const ext = path.extname(file.name) || ".png";
    const cleanFileName = `skill_${uuidv4().slice(0, 8)}${ext}`;
    
    // Save to public/uploads
    const publicFilePath = path.join(uploadsDir, cleanFileName);
    await fs.writeFile(publicFilePath, buffer);

    // Also mirror to data/media/images for automation engine access
    const mediaFilePath = path.join(mediaImagesDir, cleanFileName);
    await fs.writeFile(mediaFilePath, buffer);

    return NextResponse.json({
      success: true,
      fileName: cleanFileName,
      fileUrl: `/uploads/${cleanFileName}`,
      filePath: mediaFilePath,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json({ error: error.message || "Failed to upload file" }, { status: 500 });
  }
}
