import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
          scope: "openid email profile",
        },
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours - session expires after 1 day
    updateAge: 12 * 60 * 60, // 12 hours - session refreshes if older than 12 hours
  },
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === "production"
        ? `__Secure-next-auth.session-token`
        : `next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production", // HTTPS only in production
      },
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async signIn() {
      // Allow all sign-ins
      return true;
    },
    async jwt({ token, account, profile }) {
      // On first sign in, add user info to token
      if (account && profile) {
        token.sub = profile.email ?? undefined; // Use email as user ID for backend
        token.email = profile.email ?? undefined;
        token.name = profile.name ?? undefined;
        token.picture = profile.picture ?? undefined;
      }
      return token;
    },
    async session({ session, token }) {
      // Add user info to session object
      if (session.user && token) {
        session.user.id = (token.sub as string) ?? "";
        session.user.email = (token.email as string) ?? "";
        session.user.name = (token.name as string) ?? "";
        session.user.image = (token.picture as string) ?? "";
      }
      return session;
    },
  },
});
