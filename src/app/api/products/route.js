import { NextResponse } from "next/server";
import { getAllProducts, createProduct, deleteProduct } from "@/lib/db";
import { v4 as uuidv4 } from "uuid";

export async function GET() {
  try {
    const products = getAllProducts();
    // Parse JSON fields
    const parsed = products.map((p) => ({
      ...p,
      key_benefits: JSON.parse(p.key_benefits || "[]"),
      brand_colors: JSON.parse(p.brand_colors || "{}"),
      campaign_objectives: JSON.parse(p.campaign_objectives || "[]"),
    }));
    return NextResponse.json(parsed);
  } catch (error) {
    console.error("Error fetching products:", error);
    return NextResponse.json({ error: "Failed to fetch products" }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    if (!body.name) {
      return NextResponse.json({ error: "Product name is required" }, { status: 400 });
    }

    const product = {
      id: uuidv4(),
      ...body,
    };

    createProduct(product);

    return NextResponse.json({ id: product.id, message: "Product created successfully" }, { status: 201 });
  } catch (error) {
    console.error("Error creating product:", error);
    return NextResponse.json({ error: "Failed to create product" }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "Product ID is required" }, { status: 400 });
    }
    deleteProduct(id);
    return NextResponse.json({ message: "Product deleted successfully" });
  } catch (error) {
    console.error("Error deleting product:", error);
    return NextResponse.json({ error: "Failed to delete product" }, { status: 500 });
  }
}
