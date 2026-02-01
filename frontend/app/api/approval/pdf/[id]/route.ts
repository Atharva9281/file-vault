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

    // Get the signed URL from backend
    const response = await fetch(`${BACKEND_URL}/approval/preview/${id}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${backendToken}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return NextResponse.json(
        { error: data.detail || "Failed to get preview" },
        { status: response.status }
      );
    }

    const data = await response.json();
    const signedUrl = data.signed_url;

    // Fetch the actual PDF from GCS
    const pdfResponse = await fetch(signedUrl);

    if (!pdfResponse.ok) {
      return NextResponse.json(
        { error: "Failed to fetch PDF from storage" },
        { status: pdfResponse.status }
      );
    }

    // Get the PDF as a buffer
    const pdfBuffer = await pdfResponse.arrayBuffer();

    // Return the PDF with proper headers
    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Length": pdfBuffer.byteLength.toString(),
        "Cache-Control": "private, max-age=900", // Cache for 15 minutes
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
