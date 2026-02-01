/**
 * Document Rejection API Route - Proxy to FastAPI backend
 *
 * Handles rejecting a document.
 */

import { auth } from "@/lib/auth";
import { createBackendToken } from "@/lib/jwt";
import { ratelimit } from "@/lib/rate-limit";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

// Validation schema for rejection reason
const RejectReasonSchema = z.object({
  reason: z.string().max(500).optional(),
});

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Get the authenticated session
    const session = await auth();

    if (!session || !session.user?.email) {
      return NextResponse.json(
        { error: "Unauthorized - Please sign in" },
        { status: 401 }
      );
    }

    // Rate limiting - 10 requests per 10 seconds
    const { success } = await ratelimit.limit(session.user.email);

    if (!success) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    const { id } = await params;

    // Get the rejection reason from request body (if provided) with validation
    let body = undefined;
    try {
      const requestBody = await request.json();
      // Validate the input
      const validated = RejectReasonSchema.parse(requestBody);
      if (validated.reason) {
        body = JSON.stringify({ reason: validated.reason });
      }
    } catch (error) {
      if (error instanceof z.ZodError) {
        return NextResponse.json(
          { error: "Invalid input", details: error.issues },
          { status: 400 }
        );
      }
      // No body provided, which is fine
    }

    // Create properly signed JWT token for backend authentication
    const backendToken = createBackendToken(session.user.email);

    // Forward the request to the FastAPI backend
    const response = await fetch(`${BACKEND_URL}/approval/${id}/reject`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${backendToken}`,
        "Content-Type": "application/json",
      },
      body,
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
