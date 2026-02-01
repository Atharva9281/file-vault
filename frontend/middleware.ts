import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isAuthenticated = !!req.auth;

  // Protected routes
  const protectedRoutes = ["/dashboard", "/approval"];
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  );

  // Redirect unauthenticated users to landing page
  if (isProtectedRoute && !isAuthenticated) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  // Add CORS headers for API routes
  const response = NextResponse.next();

  // Only allow same-origin requests for security
  const origin = req.headers.get("origin");
  const allowedOrigins = [
    process.env.NEXTAUTH_URL,
    "http://localhost:3000",
  ].filter(Boolean);

  if (origin && allowedOrigins.includes(origin)) {
    response.headers.set("Access-Control-Allow-Origin", origin);
    response.headers.set("Access-Control-Allow-Credentials", "true");
    response.headers.set(
      "Access-Control-Allow-Methods",
      "GET, POST, PUT, DELETE, OPTIONS"
    );
    response.headers.set(
      "Access-Control-Allow-Headers",
      "Content-Type, Authorization"
    );
  }

  return response;
});

export const config = {
  matcher: ["/dashboard/:path*", "/approval/:path*", "/api/:path*"],
};
