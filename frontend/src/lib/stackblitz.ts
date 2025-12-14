/**
 * StackBlitz Integration for AlphaWave Vibe Dashboard
 * 
 * Provides interactive Next.js previews directly in the browser
 * using StackBlitz's WebContainer technology.
 */

import sdk from '@stackblitz/sdk';
import type { VibeFile } from '@/lib/hooks/useVibeProject';

// Base Next.js 14 configuration files
const BASE_FILES: Record<string, string> = {
  'package.json': JSON.stringify({
    name: 'alphawave-preview',
    version: '0.1.0',
    private: true,
    scripts: {
      dev: 'next dev',
      build: 'next build',
      start: 'next start',
    },
    dependencies: {
      next: '14.2.0',
      react: '^18.2.0',
      'react-dom': '^18.2.0',
    },
    devDependencies: {
      '@types/node': '^20',
      '@types/react': '^18',
      '@types/react-dom': '^18',
      typescript: '^5',
      tailwindcss: '^3.4.0',
      autoprefixer: '^10',
      postcss: '^8',
    },
  }, null, 2),
  
  'tsconfig.json': JSON.stringify({
    compilerOptions: {
      lib: ['dom', 'dom.iterable', 'esnext'],
      allowJs: true,
      skipLibCheck: true,
      strict: true,
      noEmit: true,
      esModuleInterop: true,
      module: 'esnext',
      moduleResolution: 'bundler',
      resolveJsonModule: true,
      isolatedModules: true,
      jsx: 'preserve',
      incremental: true,
      plugins: [{ name: 'next' }],
      paths: { '@/*': ['./*'] },
    },
    include: ['next-env.d.ts', '**/*.ts', '**/*.tsx', '.next/types/**/*.ts'],
    exclude: ['node_modules'],
  }, null, 2),
  
  'next.config.js': `/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};
module.exports = nextConfig;
`,
  
  'postcss.config.js': `module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
`,
  
  'next-env.d.ts': `/// <reference types="next" />
/// <reference types="next/image-types/global" />
`,
};

/**
 * Converts our VibeFile array to StackBlitz file format
 */
export function convertFilesToStackBlitz(
  files: VibeFile[],
  design?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    headingFont?: string;
    bodyFont?: string;
  }
): Record<string, string> {
  const sbFiles: Record<string, string> = { ...BASE_FILES };
  
  // Add tailwind config with design tokens
  sbFiles['tailwind.config.ts'] = `import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '${design?.primaryColor || '#8B9D83'}',
        secondary: '${design?.secondaryColor || '#F4E4BC'}',
        accent: '${design?.accentColor || '#D4A574'}',
        sage: '${design?.primaryColor || '#8B9D83'}',
        cream: '${design?.secondaryColor || '#F4E4BC'}',
        'warm-brown': '${design?.accentColor || '#D4A574'}',
      },
      fontFamily: {
        heading: ['${design?.headingFont || 'Playfair Display'}', 'serif'],
        body: ['${design?.bodyFont || 'Source Sans Pro'}', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
`;
  
  // Convert our files to StackBlitz format
  for (const file of files) {
    let path = file.file_path;
    
    // Normalize path - remove leading slash if present
    if (path.startsWith('/')) {
      path = path.slice(1);
    }
    
    // Skip config files we're providing our own version of
    if (path === 'package.json' || path === 'tsconfig.json') {
      continue;
    }
    
    sbFiles[path] = file.content;
  }
  
  // Ensure globals.css has Tailwind directives
  if (!sbFiles['app/globals.css']) {
    sbFiles['app/globals.css'] = `@tailwind base;
@tailwind components;
@tailwind utilities;
`;
  } else if (!sbFiles['app/globals.css'].includes('@tailwind')) {
    sbFiles['app/globals.css'] = `@tailwind base;
@tailwind components;
@tailwind utilities;

${sbFiles['app/globals.css']}`;
  }
  
  return sbFiles;
}

/**
 * Opens project in a new StackBlitz tab
 */
export async function openInStackBlitz(
  projectName: string,
  files: VibeFile[],
  design?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    headingFont?: string;
    bodyFont?: string;
  }
): Promise<void> {
  const sbFiles = convertFilesToStackBlitz(files, design);
  
  await sdk.openProject(
    {
      title: projectName,
      description: `${projectName} - Built with AlphaWave Vibe`,
      template: 'node',
      files: sbFiles,
    },
    {
      newWindow: true,
      openFile: 'app/page.tsx',
    }
  );
}

/**
 * Embeds project in a container element
 */
export async function embedInStackBlitz(
  elementId: string,
  projectName: string,
  files: VibeFile[],
  design?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    headingFont?: string;
    bodyFont?: string;
  }
): Promise<void> {
  const sbFiles = convertFilesToStackBlitz(files, design);
  
  await sdk.embedProject(
    elementId,
    {
      title: projectName,
      description: `${projectName} - Built with AlphaWave Vibe`,
      template: 'node',
      files: sbFiles,
    },
    {
      openFile: 'app/page.tsx',
      height: '100%',
      hideExplorer: false,
      hideNavigation: false,
      hideDevTools: false,
    }
  );
}

/**
 * Generates a StackBlitz URL for sharing
 */
export function getStackBlitzUrl(
  projectName: string,
  files: VibeFile[],
  design?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    headingFont?: string;
    bodyFont?: string;
  }
): string {
  // Convert files to StackBlitz format (validates the files are usable)
  convertFilesToStackBlitz(files, design);
  
  // Return a StackBlitz URL for forking a Next.js project
  // Note: For persistent projects, you'd use their API to create and store the project
  return `https://stackblitz.com/fork/nextjs?title=${encodeURIComponent(projectName)}`;
}

