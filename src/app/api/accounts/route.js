import { NextResponse } from "next/server";
import { getAllAccounts, upsertAccount, deleteAccount } from "@/lib/db";
import { encrypt } from "@/lib/encryption";
import { v4 as uuidv4 } from "uuid";

export async function GET() {
  try {
    const accounts = await getAllAccounts();
    // Parse JSON fields and mask passwords
    const parsed = accounts.map((a) => ({
      ...a,
      extra_fields: typeof a.extra_fields === "string" ? JSON.parse(a.extra_fields || "{}") : (a.extra_fields || {}),
      // Never send actual password to frontend
      has_password: !!a.encrypted_password,
      encrypted_password: undefined,
    }));
    return NextResponse.json(parsed);
  } catch (error) {
    console.error("Error fetching accounts:", error);
    return NextResponse.json({ error: "Failed to fetch accounts" }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    if (!body.platform) {
      return NextResponse.json({ error: "Platform is required" }, { status: 400 });
    }

    const encryptedPwd = body.password ? encrypt(body.password) : null;

    const account = {
      id: uuidv4(),
      platform: body.platform,
      username: body.username || null,
      encrypted_password: encryptedPwd,
      extra_fields: body.extra_fields || {},
      session_status: "unverified",
    };

    await upsertAccount(account);

    return NextResponse.json({ message: "Account saved successfully" }, { status: 201 });
  } catch (error) {
    console.error("Error saving account:", error);
    return NextResponse.json({ error: "Failed to save account" }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "Account ID is required" }, { status: 400 });
    }
    await deleteAccount(id);
    return NextResponse.json({ message: "Account deleted successfully" });
  } catch (error) {
    console.error("Error deleting account:", error);
    return NextResponse.json({ error: "Failed to delete account" }, { status: 500 });
  }
}
