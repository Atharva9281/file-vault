import jwt from "jsonwebtoken";

export function createBackendToken(userEmail: string): string {
  const secret = process.env.NEXTAUTH_SECRET;

  if (!secret) {
    throw new Error("NEXTAUTH_SECRET is not configured");
  }

  // Create JWT token with user email as 'sub' claim
  // Backend expects HS256 algorithm
  const token = jwt.sign(
    { sub: userEmail },
    secret,
    { algorithm: "HS256", expiresIn: "1h" }
  );

  return token;
}
