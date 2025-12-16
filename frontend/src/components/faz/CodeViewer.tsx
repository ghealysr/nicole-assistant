import React from 'react';
import Prism from 'prismjs';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-json';
import 'prismjs/themes/prism-tomorrow.css';
import { Copy, Check } from 'lucide-react';

interface CodeViewerProps {
  code: string;
  language: string;
  path?: string;
}

export function CodeViewer({ code, language, path }: CodeViewerProps) {
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    Prism.highlightAll();
  }, [code, language]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative h-full flex flex-col bg-[#0A0A0F]">
      {path && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1E1E2E] bg-[#12121A]">
          <span className="text-sm text-[#94A3B8] font-mono">{path}</span>
          <button
            onClick={handleCopy}
            className="p-1.5 hover:bg-[#1E1E2E] rounded-md transition-colors text-[#94A3B8] hover:text-white"
            title="Copy code"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          </button>
        </div>
      )}
      <div className="flex-1 overflow-auto custom-scrollbar">
        <pre className="!m-0 !p-4 !bg-transparent !text-sm font-mono leading-relaxed">
          <code className={`language-${language}`}>
            {code}
          </code>
        </pre>
      </div>
    </div>
  );
}

