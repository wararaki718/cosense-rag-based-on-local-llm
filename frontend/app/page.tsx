"use client";

import { useState } from 'react';
import { Search, Loader2, Link as LinkIcon, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchResult {
  chunk: {
    page_title: string;
    content: string;
    url: string;
  };
  score: number;
}

interface LLMResponse {
  answer: string;
  sources: string[];
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LLMResponse | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setSearchResults([]);

    const SEARCH_API_URL = process.env.NEXT_PUBLIC_SEARCH_API_URL || 'http://localhost:8002';
    const LLM_API_URL = process.env.NEXT_PUBLIC_LLM_API_URL || 'http://localhost:8003';

    try {
      // 1. Call api-search
      const searchResp = await fetch(`${SEARCH_API_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      if (!searchResp.ok) throw new Error('Search failed');
      const searchData: SearchResult[] = await searchResp.json();
      setSearchResults(searchData);

      // 2. Call api-llm
      const llmResp = await fetch(`${LLM_API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          context: searchData.map(r => r.chunk)
        }),
      });

      if (!llmResp.ok) throw new Error('Generation failed');
      const llmData: LLMResponse = await llmResp.json();
      setResult(llmData);

    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-base-200 py-10 px-4">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold flex items-center justify-center gap-2">
            <BookOpen className="text-primary" /> Scrapbox RAG
          </h1>
          <p className="text-base-content/60">Local LLM based Knowledge Assistant</p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            className="input input-bordered flex-1 text-lg h-14"
            placeholder="Ask anything about your Scrapbox..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button 
            className="btn btn-primary h-14 px-8" 
            disabled={loading || !query.trim()}
          >
            {loading ? <Loader2 className="animate-spin" /> : <Search />}
            Search
          </button>
        </form>

        {/* Results */}
        <AnimatePresence>
          {error && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="alert alert-error"
            >
              <span>{error}</span>
            </motion.div>
          )}

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-base-100 shadow-xl"
            >
              <div className="card-body">
                <h2 className="card-title text-secondary">Answer</h2>
                <div className="whitespace-pre-wrap leading-relaxed text-lg">
                  {result.answer}
                </div>
                
                <div className="divider">Sources</div>
                <div className="flex flex-wrap gap-2">
                  {result.sources.map((url, i) => (
                    <a 
                      key={i} 
                      href={url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-sm btn-ghost gap-2 border border-base-300"
                    >
                      <LinkIcon size={14} /> Source {i+1}
                    </a>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {searchResults.length > 0 && !result && loading && (
            <div className="text-center text-base-content/60 flex items-center justify-center gap-2">
              <Loader2 className="animate-spin" />
              Generating answer with Gemma 3...
            </div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
