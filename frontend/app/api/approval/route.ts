import { auth } from "@/lib/auth";
import { createBackendToken } from "@/lib/jwt";
import { ratelimit } from "@/lib/rate-limit";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

// Validation schemas
const DocumentIdSchema = z.string().min(1).max(255);
const ActionSchema = z.enum(["approve", "reject"]);

export async function POST(req: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Rate limiting
    const { success } = await ratelimit.limit(session.user.email);

    if (!success) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    // Get URL path to determine document ID and action with validation
    const { searchParams } = new URL(req.url);
    const documentIdRaw = searchParams.get("documentId");
    const actionRaw = searchParams.get("action");

    if (!documentIdRaw || !actionRaw) {
      return NextResponse.json(
        { error: "Missing documentId or action" },
        { status: 400 }
      );
    }

    // Validate parameters
    let documentId: string;
    let action: "approve" | "reject";
    try {
      documentId = DocumentIdSchema.parse(documentIdRaw);
      action = ActionSchema.parse(actionRaw);
    } catch (error) {
      return NextResponse.json(
        { error: "Invalid documentId or action format" },
        { status: 400 }
      );
    }

    // Create proper JWT token for backend
    const backendToken = createBackendToken(session.user.email);

    // Get request body for reject reason
    let body = undefined;
    if (action === "reject") {
      const contentType = req.headers.get("content-type");
      if (contentType?.includes("application/json")) {
        body = JSON.stringify(await req.json());
      }
    }

    // Forward request to FastAPI backend
    const response = await fetch(`${BACKEND_URL}/approval/${documentId}/${action}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${backendToken}`,
        "Content-Type": "application/json",
      },
      body,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || `Failed to ${action} document` },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
