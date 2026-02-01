"use client";

import Link from 'next/link';
import { useSession, signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Shield, Brain, FileText, CheckCircle2 } from 'lucide-react';

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Auto-redirect authenticated users to dashboard
  useEffect(() => {
    if (status === "authenticated" && session) {
      router.push("/dashboard");
    }
  }, [status, session, router]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero Section - Bold & Centered */}
      <section className="pt-32 pb-40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-foreground text-sm font-medium mb-10">
              <div className="w-2 h-2 rounded-full bg-foreground" />
              Powered by Google Cloud AI
            </div>

            {/* Massive Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-foreground leading-[1.1] tracking-tight mb-8">
              Intelligent document processing for{' '}
              <span className="underline decoration-2 underline-offset-8">finance</span>
            </h1>

            {/* Subheadline */}
            <p className="text-xl sm:text-2xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed">
              <span className="font-semibold text-foreground">No complexity. No security risks.</span>{' '}
              Enterprise-grade document management built for financial services.
            </p>

            {/* Google Sign In Button */}
            {session ? (
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-3 bg-foreground text-background px-10 py-5 rounded-full font-semibold text-lg hover:bg-foreground/90 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Go to Dashboard
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Link>
            ) : (
              <button
                onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
                className="inline-flex items-center gap-3 bg-foreground text-background px-10 py-5 rounded-full font-semibold text-lg hover:bg-foreground/90 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Continue with Google
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Stats Section - Full Width Colored Cards */}
      <section className="py-24 bg-muted/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground mb-6 leading-tight">
              Everything you need to
              <br />
              manage documents
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Powerful features designed for modern financial services
            </p>
          </div>

          {/* Large Feature Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-[#e8f5e9] rounded-3xl p-10 min-h-[280px] flex flex-col justify-between hover:scale-[1.02] transition-transform duration-300">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold text-foreground leading-tight mb-4">
                  99.9%
                  <br />
                  Accuracy
                </h3>
                <p className="text-muted-foreground text-lg">
                  Industry-leading precision in document processing and data extraction
                </p>
              </div>
            </div>

            <div className="bg-[#fff3e0] rounded-3xl p-10 min-h-[280px] flex flex-col justify-between hover:scale-[1.02] transition-transform duration-300">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold text-foreground leading-tight mb-4">
                  &lt;2s
                  <br />
                  Processing
                </h3>
                <p className="text-muted-foreground text-lg">
                  Lightning-fast document analysis powered by Vertex AI
                </p>
              </div>
            </div>

            <div className="bg-[#e3f2fd] rounded-3xl p-10 min-h-[280px] flex flex-col justify-between hover:scale-[1.02] transition-transform duration-300">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold text-foreground leading-tight mb-4">
                  SOC 2
                  <br />
                  Certified
                </h3>
                <p className="text-muted-foreground text-lg">
                  Enterprise security with complete audit trails and compliance
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Showcase - Two Column Layout */}
      <section className="py-32">
        <div className="max-w-7xl mx-auto px-6">
          {/* Feature 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-32">
            <div>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm font-medium mb-6">
                Bank-Grade Security
              </div>
              <h3 className="text-4xl sm:text-5xl font-bold text-foreground leading-tight mb-6">
                Automatic PII
                <br />
                redaction
              </h3>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                Protect sensitive information with AI-powered automatic detection and redaction.
                All data encrypted at rest and in transit with enterprise security protocols.
              </p>
              <ul className="space-y-4">
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  SSN & tax ID detection
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Address & phone redaction
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Bank account protection
                </li>
              </ul>
            </div>
            <div className="bg-[#e8dfd0] rounded-3xl p-12 min-h-[500px] flex items-center justify-center">
              <div className="text-center">
                <Shield className="w-32 h-32 text-foreground/20 mx-auto mb-6" />
                <p className="text-muted-foreground text-lg">Document Security Preview</p>
              </div>
            </div>
          </div>

          {/* Feature 2 - Reversed */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-32">
            <div className="order-2 lg:order-1 bg-[#dfd8ec] rounded-3xl p-12 min-h-[500px] flex items-center justify-center">
              <div className="text-center">
                <Brain className="w-32 h-32 text-foreground/20 mx-auto mb-6" />
                <p className="text-muted-foreground text-lg">AI Extraction Preview</p>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm font-medium mb-6">
                AI-Powered
              </div>
              <h3 className="text-4xl sm:text-5xl font-bold text-foreground leading-tight mb-6">
                Intelligent data
                <br />
                extraction
              </h3>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                Vertex AI automatically extracts key financial data from tax documents, W-2s,
                1099s, and more with industry-leading accuracy.
              </p>
              <ul className="space-y-4">
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  W-2 wage extraction
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  1099 income parsing
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Tax form analysis
                </li>
              </ul>
            </div>
          </div>

          {/* Feature 3 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm font-medium mb-6">
                Compliance Ready
              </div>
              <h3 className="text-4xl sm:text-5xl font-bold text-foreground leading-tight mb-6">
                Complete audit
                <br />
                trails
              </h3>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                SOC 2 Type II certified with comprehensive audit trails. Meet regulatory
                requirements without the complexity.
              </p>
              <ul className="space-y-4">
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Document versioning
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Access logging
                </li>
                <li className="flex items-center gap-3 text-lg">
                  <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-background" />
                  </div>
                  Retention policies
                </li>
              </ul>
            </div>
            <div className="bg-[#d4ecd6] rounded-3xl p-12 min-h-[500px] flex items-center justify-center">
              <div className="text-center">
                <FileText className="w-32 h-32 text-foreground/20 mx-auto mb-6" />
                <p className="text-muted-foreground text-lg">Audit Trail Preview</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works - Large Cards */}
      <section className="py-24 bg-muted/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
              How it works
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Four simple steps to secure document processing
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-card border border-border rounded-3xl p-8 hover:shadow-lg transition-all duration-300">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                <span className="text-2xl font-bold text-primary-foreground">1</span>
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Upload</h3>
              <p className="text-muted-foreground leading-relaxed">
                Securely upload your tax documents and financial files via drag & drop
              </p>
            </div>

            <div className="bg-card border border-border rounded-3xl p-8 hover:shadow-lg transition-all duration-300">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                <span className="text-2xl font-bold text-primary-foreground">2</span>
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Automatic Redaction</h3>
              <p className="text-muted-foreground leading-relaxed">
                AI automatically detects and redacts sensitive PII in seconds
              </p>
            </div>

            <div className="bg-card border border-border rounded-3xl p-8 hover:shadow-lg transition-all duration-300">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                <span className="text-2xl font-bold text-primary-foreground">3</span>
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Review & Approve</h3>
              <p className="text-muted-foreground leading-relaxed">
                Review redacted documents and approve for processing
              </p>
            </div>

            <div className="bg-card border border-border rounded-3xl p-8 hover:shadow-lg transition-all duration-300">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                <span className="text-2xl font-bold text-primary-foreground">4</span>
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Extract Data</h3>
              <p className="text-muted-foreground leading-relaxed">
                Extract key financial data for downstream systems automatically
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground mb-8 leading-tight">
            Ready to streamline your
            <br />
            document processing?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Join leading financial institutions using File Vault for secure, automated document processing.
          </p>
          {session ? (
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-3 bg-foreground text-background px-10 py-5 rounded-full font-semibold text-lg hover:bg-foreground/90 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get started free
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
          ) : (
            <button
              onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
              className="inline-flex items-center gap-3 bg-foreground text-background px-10 py-5 rounded-full font-semibold text-lg hover:bg-foreground/90 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get started free
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-primary-foreground"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <span className="text-sm text-muted-foreground">
                © 2024 File Vault. All rights reserved.
              </span>
            </div>

            <div className="flex items-center gap-8">
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Privacy
              </a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Terms
              </a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Documentation
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
