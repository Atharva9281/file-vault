'use client'

import { useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

// Set worker path using CDN
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface PDFViewerProps {
  fileUrl: string
  className?: string
}

export default function PDFViewer({ fileUrl, className = '' }: PDFViewerProps) {

  const [numPages, setNumPages] = useState<number>(0)
  const [pageWidth, setPageWidth] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
  }

  const onDocumentLoadError = (error: Error) => {
    setError('Failed to load PDF. The preview URL may have expired.')
    setLoading(false)
  }

  // Calculate page width based on container
  const updatePageWidth = (container: HTMLDivElement | null) => {
    if (container) {
      setPageWidth(container.offsetWidth - 40) // 40px for padding
    }
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center min-h-[600px] ${className}`}>
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-xl font-semibold text-foreground mb-2">Unable to Load PDF</h3>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={updatePageWidth}
      className={`relative ${className}`}
    >
      {/* Loading overlay - shows on top while Document loads */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50 z-50 min-h-[600px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading PDF...</p>
          </div>
        </div>
      )}

      {/* Always render Document - don't conditionally hide it */}
      <Document
        file={fileUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
      >
        <div className="space-y-4">
          {/* Render all pages - this allows continuous scrolling like SmallPDF */}
          {Array.from(new Array(numPages), (el, index) => (
            <div key={`page_${index + 1}`} className="relative">
              {/* Page number indicator */}
              <div className="absolute top-2 right-2 bg-black bg-opacity-60 text-white px-3 py-1 rounded-full text-sm font-medium z-10">
                Page {index + 1} of {numPages}
              </div>

              <Page
                pageNumber={index + 1}
                width={pageWidth || undefined}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                className="shadow-lg rounded-lg overflow-hidden bg-white"
              />
            </div>
          ))}
        </div>
      </Document>
    </div>
  )
}
