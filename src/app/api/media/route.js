import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const filePathParam = searchParams.get("path") || searchParams.get("file");

    if (!filePathParam) {
      return NextResponse.json({ error: "Missing file or path parameter" }, { status: 400 });
    }

    const projectRoot = process.cwd();
    let resolvedPath = "";

    // If it's just a filename or relative path
    if (filePathParam.includes(":") || filePathParam.startsWith("/") || filePathParam.startsWith("\\")) {
      resolvedPath = path.resolve(filePathParam);
    } else {
      // Look in data/media/images first, then data/media/videos, then data/media
      const candidates = [
        path.join(projectRoot, "data", "media", "images", filePathParam),
        path.join(projectRoot, "data", "media", "videos", filePathParam),
        path.join(projectRoot, "data", "media", filePathParam),
        path.join(projectRoot, filePathParam),
      ];
      resolvedPath = candidates.find((c) => fs.existsSync(c)) || candidates[0];
    }

    if (!fs.existsSync(resolvedPath)) {
      return NextResponse.json({ error: "Media file not found on disk" }, { status: 404 });
    }

    const ext = path.extname(resolvedPath).toLowerCase();
    const mimeTypes = {
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".webp": "image/webp",
      ".gif": "image/gif",
      ".mp4": "video/mp4",
      ".webm": "video/webm",
    };

    const contentType = mimeTypes[ext] || "application/octet-stream";
    const fileBuffer = fs.readFileSync(resolvedPath);

    return new Response(fileBuffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Disposition": `inline; filename="${path.basename(resolvedPath)}"`,
      },
    });
  } catch (error) {
    console.error("Media serving error:", error);
    return NextResponse.json({ error: error.message || "Failed to serve media" }, { status: 500 });
  }
}
