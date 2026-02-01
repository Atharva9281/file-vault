import { auth } from "@/lib/auth";
import { createBackendToken } from "@/lib/jwt";
import { uploadRatelimit } from "@/lib/rate-limit";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Rate limiting - 3 uploads per minute
    const { success, limit, remaining, reset } = await uploadRatelimit.limit(
      session.user.email
    );

    if (!success) {
      return NextResponse.json(
        {
          error: "Too many upload requests. Please try again later.",
          limit,
          remaining,
          resetAt: new Date(reset).toISOString(),
        },
        {
          status: 429,
          headers: {
            "X-RateLimit-Limit": limit.toString(),
            "X-RateLimit-Remaining": remaining.toString(),
            "X-RateLimit-Reset": reset.toString(),
          },
        }
      );
    }

    // Create proper JWT token for backend
    const backendToken = createBackendToken(session.user.email);

    // Get form data from request
    const formData = await req.formData();

    // Forward request to FastAPI backend
    const response = await fetch(`${BACKEND_URL}/upload/`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${backendToken}`,
      },
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Upload failed" },
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
