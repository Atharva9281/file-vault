import { auth } from "@/lib/auth";
import { createBackendToken } from "@/lib/jwt";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const { id } = await params;
    const backendToken = createBackendToken(session.user.email);

    console.log(`Fetching download URL for document ${id} from backend: ${BACKEND_URL}/approval/download/${id}`);

    const response = await fetch(`${BACKEND_URL}/approval/download/${id}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${backendToken}`,
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      console.error(`Backend error for document ${id}:`, {
        status: response.status,
        statusText: response.statusText,
        error: data,
      });
      return NextResponse.json(
        { error: data.detail || "Failed to get download URL" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in download URL route:", error);
    return NextResponse.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}
