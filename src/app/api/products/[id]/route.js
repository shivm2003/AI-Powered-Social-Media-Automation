import { NextResponse } from "next/server";
import { getProductById, updateProduct, deleteProduct } from "@/lib/db";

export async function GET(request, { params }) {
  try {
    const { id } = await params;
    const product = await getProductById(id);
    if (!product) {
      return NextResponse.json({ error: "Product not found" }, { status: 404 });
    }

    return NextResponse.json({
      ...product,
      key_benefits: typeof product.key_benefits === "string" ? JSON.parse(product.key_benefits || "[]") : (product.key_benefits || []),
      brand_colors: typeof product.brand_colors === "string" ? JSON.parse(product.brand_colors || "{}") : (product.brand_colors || {}),
      campaign_objectives: typeof product.campaign_objectives === "string" ? JSON.parse(product.campaign_objectives || "[]") : (product.campaign_objectives || []),
    });
  } catch (error) {
    console.error("Error fetching product:", error);
    return NextResponse.json({ error: "Failed to fetch product" }, { status: 500 });
  }
}

export async function PUT(request, { params }) {
  try {
    const { id } = await params;
    const body = await request.json();

    if (!body.name) {
      return NextResponse.json({ error: "Product name is required" }, { status: 400 });
    }

    await updateProduct(id, body);
    return NextResponse.json({ message: "Product updated successfully" });
  } catch (error) {
    console.error("Error updating product:", error);
    return NextResponse.json({ error: "Failed to update product" }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  try {
    const { id } = await params;
    await deleteProduct(id);
    return NextResponse.json({ message: "Product deleted successfully" });
  } catch (error) {
    console.error("Error deleting product:", error);
    return NextResponse.json({ error: "Failed to delete product" }, { status: 500 });
  }
}
