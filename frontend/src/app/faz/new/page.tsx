'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, Sparkles, Loader2, ImagePlus, X, Info, 
  Lightbulb, Layout, Palette
} from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { fazApi } from '@/lib/faz/api';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface InspirationImage {
  file: File;
  preview: string;
  notes: string;
}

export default function CreateProjectPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [creating, setCreating] = useState(false);
  const [inspirationImages, setInspirationImages] = useState<InspirationImage[]>([]);
  const [activeStep, setActiveStep] = useState<'describe' | 'inspire'>('describe');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    // Limit to 10 images total
    const remaining = 10 - inspirationImages.length;
    const toAdd = files.slice(0, remaining);

    const newImages: InspirationImage[] = toAdd.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      notes: ''
    }));

    setInspirationImages(prev => [...prev, ...newImages]);

    // Clear the input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeImage = (index: number) => {
    setInspirationImages(prev => {
      const removed = prev[index];
      URL.revokeObjectURL(removed.preview);
      return prev.filter((_, i) => i !== index);
    });
  };

  const updateImageNotes = (index: number, notes: string) => {
    setInspirationImages(prev =>
      prev.map((img, i) => i === index ? { ...img, notes } : img)
    );
  };

  const handleCreate = async () => {
    if (!prompt.trim() || creating) return;

    setCreating(true);
    try {
      // Extract a name from the prompt (first few words)
      const name = prompt.split(' ').slice(0, 4).join(' ') || 'New Project';

      // Create project with inspiration images metadata
      const inspirationData = inspirationImages.map((img, i) => ({
        filename: img.file.name,
        notes: img.notes,
        order: i
      }));

      const project = await fazApi.createProject(name, prompt, {
        inspiration_images: inspirationData
      });

      // Upload inspiration images if any (notes are included in inspirationData above)
      if (inspirationImages.length > 0) {
        try {
          const files = inspirationImages.map(img => img.file);
          await fazApi.uploadReferenceImages(project.project_id, files);
        } catch (uploadError) {
          console.error('Failed to upload images:', uploadError);
          // Continue anyway - project is created
        }
      }

      // Start pipeline in interactive mode
      await fazApi.runPipeline(project.project_id, prompt);

      // Navigate to workspace
      router.push(`/faz/projects/${project.project_id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
      setCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleCreate();
    }
  };

  // Cleanup previews on unmount
  React.useEffect(() => {
    return () => {
      inspirationImages.forEach(img => URL.revokeObjectURL(img.preview));
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-[#F1F5F9] flex flex-col">
      {/* Header */}
      <header className="h-16 border-b border-[#1E1E2E] flex items-center justify-between px-6">
        <Link href="/faz" className="flex items-center text-[#94A3B8] hover:text-white transition-colors">
          <ArrowLeft size={18} className="mr-2" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-2">
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
            activeStep === 'describe' 
              ? "bg-[#6366F1]/20 text-[#6366F1]" 
              : "text-[#64748B]"
          )}>
            <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-xs">1</span>
            Describe
          </div>
          <div className="w-8 h-px bg-[#2E2E3E]" />
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
            activeStep === 'inspire' 
              ? "bg-[#6366F1]/20 text-[#6366F1]" 
              : "text-[#64748B]"
          )}>
            <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-xs">2</span>
            Inspire
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-start py-12 px-6 overflow-y-auto">
        <div className="w-full max-w-4xl">
          {/* Step 1: Describe */}
          <AnimatePresence mode="wait">
            {activeStep === 'describe' && (
              <motion.div
                key="describe"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="w-full"
              >
                <div className="text-center mb-10">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[#6366F1]/20 to-[#818CF8]/10 mb-6">
                    <Lightbulb className="w-8 h-8 text-[#6366F1]" />
                  </div>
                  <h1 className="text-4xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
                    What would you like to build?
                  </h1>
                  <p className="text-[#94A3B8] max-w-lg mx-auto">
                    Describe your vision in detail. Nicole will analyze your requirements and create a 
                    comprehensive plan for your review before building begins.
                  </p>
                </div>

                <div className="bg-[#12121A] border border-[#1E1E2E] rounded-2xl p-2 shadow-2xl focus-within:border-[#6366F1] focus-within:ring-1 focus-within:ring-[#6366F1] transition-all">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Build a modern landing page for my AI startup called AlphaWave. Include a hero section with animated gradient, feature cards, testimonials section, and a contact form..."
                    className="w-full h-48 bg-transparent text-[#F1F5F9] placeholder-[#475569] p-4 text-lg resize-none outline-none font-medium"
                    autoFocus
                  />
                  <div className="flex justify-between items-center px-4 pb-2">
                    <span className="text-xs text-[#64748B]">
                      Be specific about layout, features, and style preferences
                    </span>
                    <button
                      onClick={() => prompt.trim() && setActiveStep('inspire')}
                      disabled={!prompt.trim()}
                      className="flex items-center gap-2 bg-[#6366F1] hover:bg-[#5659D8] disabled:opacity-50 disabled:hover:bg-[#6366F1] text-white px-6 py-2.5 rounded-xl font-medium transition-all"
                    >
                      Continue
                      <ArrowLeft size={18} className="rotate-180" />
                    </button>
                  </div>
                </div>

                {/* Quick Templates */}
                <div className="mt-8">
                  <p className="text-sm text-[#64748B] mb-4 text-center">Or start with a template</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {[
                      {
                        icon: <Layout size={20} />,
                        title: "Agency Landing",
                        desc: "Hero, services, team, portfolio",
                        prompt: "Build a modern creative agency website with a bold hero section, animated statistics counter, services grid with hover effects, team members section with social links, client logos marquee, and a contact form. Use a dark theme with orange accents."
                      },
                      {
                        icon: <Palette size={20} />,
                        title: "Portfolio",
                        desc: "Projects gallery, about, contact",
                        prompt: "Create a developer portfolio with a minimalist dark design. Include an animated hero with typing effect, filterable projects gallery with hover previews, about section with skills progress bars, blog preview cards, and contact form with social links."
                      },
                      {
                        icon: <Sparkles size={20} />,
                        title: "SaaS Product",
                        desc: "Features, pricing, testimonials",
                        prompt: "Design a SaaS product landing page with floating 3D illustrations, feature comparison cards, animated pricing tables with toggle for monthly/yearly, customer testimonials carousel, FAQ accordion, and newsletter signup. Modern gradient design."
                      }
                    ].map((template, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setPrompt(template.prompt);
                          setActiveStep('inspire');
                        }}
                        className="text-left p-4 bg-[#12121A] hover:bg-[#1E1E2E] border border-[#1E1E2E] rounded-xl transition-all hover:border-[#6366F1]/50 group"
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <div className="text-[#6366F1] group-hover:scale-110 transition-transform">
                            {template.icon}
                          </div>
                          <span className="font-medium text-[#F1F5F9] group-hover:text-[#6366F1]">
                            {template.title}
                          </span>
                        </div>
                        <p className="text-sm text-[#64748B]">{template.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Step 2: Inspire */}
            {activeStep === 'inspire' && (
              <motion.div
                key="inspire"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="w-full"
              >
                <div className="text-center mb-10">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[#F97316]/20 to-[#FB923C]/10 mb-6">
                    <ImagePlus className="w-8 h-8 text-[#F97316]" />
                  </div>
                  <h1 className="text-4xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
                    Add Inspiration
                  </h1>
                  <p className="text-[#94A3B8] max-w-lg mx-auto">
                    Upload screenshots or images of designs you love. Add notes about what elements 
                    you want Nicole to incorporate into your project.
                  </p>
                </div>

                {/* Project Summary */}
                <div className="bg-[#12121A] border border-[#1E1E2E] rounded-xl p-4 mb-6">
                  <div className="flex items-start gap-3">
                    <Info size={18} className="text-[#6366F1] mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-[#F1F5F9] mb-1">Your Project</p>
                      <p className="text-sm text-[#94A3B8] line-clamp-2">{prompt}</p>
                    </div>
                    <button
                      onClick={() => setActiveStep('describe')}
                      className="text-xs text-[#6366F1] hover:underline flex-shrink-0"
                    >
                      Edit
                    </button>
                  </div>
                </div>

                {/* Image Upload Area */}
                <div className="mb-8">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handleImageUpload}
                    className="hidden"
                  />

                  {inspirationImages.length === 0 ? (
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full h-48 border-2 border-dashed border-[#2E2E3E] rounded-2xl hover:border-[#6366F1] transition-colors flex flex-col items-center justify-center gap-3 group"
                    >
                      <div className="w-12 h-12 rounded-full bg-[#1E1E2E] flex items-center justify-center group-hover:bg-[#6366F1]/20 transition-colors">
                        <ImagePlus className="w-6 h-6 text-[#64748B] group-hover:text-[#6366F1]" />
                      </div>
                      <div className="text-center">
                        <p className="text-[#F1F5F9] font-medium">Drop images here or click to upload</p>
                        <p className="text-sm text-[#64748B] mt-1">Up to 10 inspiration images • PNG, JPG, WebP</p>
                      </div>
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {inspirationImages.map((img, idx) => (
                          <motion.div
                            key={img.preview}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="relative group"
                          >
                            <div className="aspect-video bg-[#1E1E2E] rounded-xl overflow-hidden relative">
                              <Image
                                src={img.preview}
                                alt={`Inspiration ${idx + 1}`}
                                fill
                                className="object-cover"
                              />
                              <button
                                onClick={() => removeImage(idx)}
                                className="absolute top-2 right-2 p-1.5 bg-black/70 rounded-full text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
                              >
                                <X size={14} />
                              </button>
                              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                                <span className="text-xs text-white/80">#{idx + 1}</span>
                              </div>
                            </div>
                            <textarea
                              value={img.notes}
                              onChange={(e) => updateImageNotes(idx, e.target.value)}
                              placeholder="What do you like about this? (colors, layout, style...)"
                              className="mt-2 w-full text-xs p-2 bg-[#12121A] border border-[#2E2E3E] rounded-lg text-[#94A3B8] placeholder-[#4a4a5a] focus:outline-none focus:border-[#6366F1] resize-none h-16"
                            />
                          </motion.div>
                        ))}

                        {inspirationImages.length < 10 && (
                          <button
                            onClick={() => fileInputRef.current?.click()}
                            className="aspect-video border-2 border-dashed border-[#2E2E3E] rounded-xl hover:border-[#6366F1] transition-colors flex flex-col items-center justify-center gap-2 group"
                          >
                            <ImagePlus className="w-6 h-6 text-[#64748B] group-hover:text-[#6366F1]" />
                            <span className="text-xs text-[#64748B]">Add more</span>
                          </button>
                        )}
                      </div>

                      <p className="text-xs text-[#64748B] text-center">
                        {inspirationImages.length}/10 images • Add notes to help Nicole understand what you like
                      </p>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-4">
                  <button
                    onClick={() => setActiveStep('describe')}
                    className="px-6 py-3 text-[#94A3B8] hover:text-white transition-colors"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={creating}
                    className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-[#6366F1] to-[#818CF8] hover:from-[#5659D8] hover:to-[#6366F1] text-white px-6 py-3 rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/25"
                  >
                    {creating ? (
                      <>
                        <Loader2 size={20} className="animate-spin" />
                        Setting up your project...
                      </>
                    ) : (
                      <>
                        <Sparkles size={20} />
                        Start Building with Nicole
                      </>
                    )}
                  </button>
                </div>

                {/* Skip option */}
                {inspirationImages.length === 0 && (
                  <p className="text-center text-sm text-[#64748B] mt-4">
                    <button
                      onClick={handleCreate}
                      disabled={creating}
                      className="text-[#6366F1] hover:underline"
                    >
                      Skip inspiration images
                    </button>
                    {' '}— Nicole will still create something amazing
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
