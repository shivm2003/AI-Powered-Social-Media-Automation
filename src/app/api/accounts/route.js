import { NextResponse } from "next/server";
import { getAllChromeAccounts, updateChromeAccount, getChromeAccountById } from "@/lib/db";

export async function GET() {
  try {
    const accounts = await getAllChromeAccounts();
    return NextResponse.json(accounts);
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function PUT(request) {
  try {
    const body = await request.json();
    const { id, updates } = body;
    if (!id) {
      return NextResponse.json({ error: "Account ID is required" }, { status: 400 });
    }

    const updated = await updateChromeAccount(id, updates || {});
    return NextResponse.json({ success: true, account: updated });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
