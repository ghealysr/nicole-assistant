'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Github, 
  ExternalLink, 
  CheckCircle2, 
  Loader2, 
  AlertCircle,
  Globe
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProjectSetupStatusProps {
  githubRepo?: string | null;
  productionUrl?: string | null;
  vercelProjectId?: string | null;  // Reserved for future use
  isConnecting?: boolean;
  className?: string;
}

interface ConnectionItemProps {
  label: string;
  value?: string | null;
  icon: React.ReactNode;
  isConnecting?: boolean;
  href?: string;
}

function ConnectionItem({ label, value, icon, isConnecting, href }: ConnectionItemProps) {
  const isConnected = !!value;
  
  const content = (
    <div className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors",
      isConnected 
        ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" 
        : isConnecting 
          ? "bg-amber-500/5 border-amber-500/20 text-amber-400"
          : "bg-zinc-800/50 border-zinc-700/50 text-zinc-500"
    )}>
      <div className="flex-shrink-0">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-zinc-400">{label}</p>
        <p className={cn(
          "text-sm truncate",
          isConnected ? "text-white" : "text-zinc-500"
        )}>
          {isConnecting ? 'Connecting...' : value || 'Not connected'}
        </p>
      </div>
      <div className="flex-shrink-0">
        {isConnecting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isConnected ? (
          <CheckCircle2 className="w-4 h-4" />
        ) : (
          <AlertCircle className="w-4 h-4" />
        )}
      </div>
      {href && isConnected && (
        <ExternalLink className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
      )}
    </div>
  );

  if (href && isConnected) {
    return (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer"
        className="block hover:opacity-80 transition-opacity"
      >
        {content}
      </a>
    );
  }

  return content;
}

// Vercel logo icon
function VercelIcon({ className }: { className?: string }) {
  return (
    <svg 
      viewBox="0 0 24 24" 
      fill="currentColor" 
      className={className}
    >
      <path d="M12 1L24 22H0L12 1Z" />
    </svg>
  );
}

export function ProjectSetupStatus({ 
  githubRepo, 
  productionUrl, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  vercelProjectId,  // Reserved for future Vercel dashboard link
  isConnecting = false,
  className 
}: ProjectSetupStatusProps) {
  // Extract repo name from full URL or path
  const displayGithubRepo = githubRepo 
    ? githubRepo.replace('https://github.com/', '').replace('.git', '')
    : null;

  // Construct URLs
  const githubUrl = githubRepo 
    ? (githubRepo.startsWith('http') ? githubRepo : `https://github.com/${githubRepo}`)
    : undefined;

  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("space-y-2", className)}
    >
      <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-1 mb-2">
        Project Connections
      </h3>
      
      <div className="grid gap-2">
        <ConnectionItem
          label="GitHub Repository"
          value={displayGithubRepo}
          icon={<Github className="w-4 h-4" />}
          isConnecting={isConnecting && !githubRepo}
          href={githubUrl}
        />
        
        <ConnectionItem
          label="Vercel Deployment"
          value={productionUrl ? 'Connected' : null}
          icon={<VercelIcon className="w-4 h-4" />}
          isConnecting={isConnecting && !productionUrl}
          href={productionUrl || undefined}
        />
        
        {productionUrl && (
          <ConnectionItem
            label="Live Site"
            value={productionUrl.replace('https://', '')}
            icon={<Globe className="w-4 h-4" />}
            href={productionUrl}
          />
        )}
      </div>

      {/* All connected indicator */}
      {githubRepo && productionUrl && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 rounded-lg text-emerald-400 text-xs"
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Project fully connected and ready for deployment</span>
        </motion.div>
      )}
    </motion.div>
  );
}

export default ProjectSetupStatus;

