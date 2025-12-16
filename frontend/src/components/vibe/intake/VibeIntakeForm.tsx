import React, { useState } from 'react';
import { useVibeProject } from '@/lib/hooks/useVibeProject';
import { VibeFileUploader } from './VibeFileUploader';
import { VibeCompetitorInput } from './VibeCompetitorInput';
import { Loader2, ArrowRight, Save } from 'lucide-react';

interface VibeIntakeFormProps {
  projectId: number;
  onComplete: () => void;
}

export function VibeIntakeForm({ projectId, onComplete }: VibeIntakeFormProps) {
  const { submitIntakeForm, uploadFileMetadata, addCompetitorURL } = useVibeProject();
  const [submitting, setSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    business_name: '',
    business_description: '',
    target_audience: '',
    project_type: 'business',
    page_count_estimate: 5,
    key_features: [] as string[],
    style_keywords: [] as string[],
    color_preferences: '',
    avoid_colors: '',
    inspiration_notes: '',
    needs_forms: false,
    needs_blog: false,
    needs_ecommerce: false,
    needs_cms: false,
    needs_authentication: false,
    needs_api: false,
    deadline: '',
    budget_range: '',
    additional_notes: ''
  });

  const [uploadedFiles, setUploadedFiles] = useState<Array<{ url: string; filename: string; type: string; size: number; mimeType: string }>>([]);
  const [competitors, setCompetitors] = useState<Array<{ url: string; notes?: string }>>([]);
  
  // Temporary input state for arrays
  const [featureInput, setFeatureInput] = useState('');
  const [styleInput, setStyleInput] = useState('');

  const handleInputChange = (field: string, value: string | number | boolean | string[]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleArrayAdd = (field: 'key_features' | 'style_keywords', value: string, setInput: (v: string) => void) => {
    if (!value.trim()) return;
    setFormData(prev => ({ ...prev, [field]: [...prev[field], value.trim()] }));
    setInput('');
  };

  const handleArrayRemove = (field: 'key_features' | 'style_keywords', index: number) => {
    setFormData(prev => {
      const newArray = [...prev[field]];
      newArray.splice(index, 1);
      return { ...prev, [field]: newArray };
    });
  };

  const handleFileUpload = async (fileData: { url: string; filename: string; type: string; size: number; mimeType: string }) => {
    // 1. Save metadata to backend
    const success = await uploadFileMetadata(projectId, {
      file_type: fileData.type.startsWith('image') ? 'image' : 'document',
      original_filename: fileData.filename,
      storage_url: fileData.url,
      file_size_bytes: fileData.size,
      mime_type: fileData.mimeType,
      description: 'Uploaded via Intake Form'
    });

    if (success) {
      setUploadedFiles(prev => [...prev, fileData]);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // 1. Submit competitors
      for (const comp of competitors) {
        await addCompetitorURL(projectId, comp.url, comp.notes);
      }

      // 2. Submit main form
      const success = await submitIntakeForm(projectId, formData);
      
      if (success) {
        onComplete();
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="vibe-intake-form max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Project Intake</h2>
        <p className="text-gray-500 mt-1">Provide the details to kickstart your project.</p>
      </div>

      <div className="space-y-8">
        {/* Section 1: Business Info */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">Business Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.business_name}
                onChange={(e) => handleInputChange('business_name', e.target.value)}
                placeholder="Acme Corp"
              />
            </div>
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Audience *</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.target_audience}
                onChange={(e) => handleInputChange('target_audience', e.target.value)}
                placeholder="Tech-savvy professionals..."
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Description *</label>
              <textarea
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none h-24"
                value={formData.business_description}
                onChange={(e) => handleInputChange('business_description', e.target.value)}
                placeholder="What does the business do?"
              />
            </div>
          </div>
        </section>

        {/* Section 2: Scope & Features */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">Scope & Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project Type</label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.project_type}
                onChange={(e) => handleInputChange('project_type', e.target.value)}
              >
                <option value="business">Business Website</option>
                <option value="portfolio">Portfolio</option>
                <option value="ecommerce">E-commerce</option>
                <option value="landing">Landing Page</option>
                <option value="blog">Blog</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Est. Page Count</label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.page_count_estimate}
                onChange={(e) => handleInputChange('page_count_estimate', parseInt(e.target.value))}
                min={1}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Key Features</label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                  value={featureInput}
                  onChange={(e) => setFeatureInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleArrayAdd('key_features', featureInput, setFeatureInput)}
                  placeholder="Add a feature (e.g. Contact Form, Gallery)"
                />
                <button
                  onClick={() => handleArrayAdd('key_features', featureInput, setFeatureInput)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.key_features.map((feat, idx) => (
                  <span key={idx} className="bg-purple-50 text-purple-700 px-2 py-1 rounded-md text-sm flex items-center border border-purple-100">
                    {feat}
                    <button onClick={() => handleArrayRemove('key_features', idx)} className="ml-2 hover:text-purple-900">×</button>
                  </span>
                ))}
              </div>
            </div>
            
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Technical Requirements</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  ['needs_forms', 'Forms'],
                  ['needs_blog', 'Blog / News'],
                  ['needs_ecommerce', 'E-commerce'],
                  ['needs_cms', 'CMS'],
                  ['needs_authentication', 'User Auth'],
                  ['needs_api', 'External API']
                ].map(([key, label]) => (
                  <label key={key} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData[key as keyof typeof formData] as boolean}
                      onChange={(e) => handleInputChange(key, e.target.checked)}
                      className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                    />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Design & Brand */}
        <section>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">Design & Brand</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Style Keywords</label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                  value={styleInput}
                  onChange={(e) => setStyleInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleArrayAdd('style_keywords', styleInput, setStyleInput)}
                  placeholder="e.g. Modern, Minimal, Dark Mode"
                />
                <button
                  onClick={() => handleArrayAdd('style_keywords', styleInput, setStyleInput)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.style_keywords.map((style, idx) => (
                  <span key={idx} className="bg-blue-50 text-blue-700 px-2 py-1 rounded-md text-sm flex items-center border border-blue-100">
                    {style}
                    <button onClick={() => handleArrayRemove('style_keywords', idx)} className="ml-2 hover:text-blue-900">×</button>
                  </span>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Color Preferences</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.color_preferences}
                onChange={(e) => handleInputChange('color_preferences', e.target.value)}
                placeholder="e.g. Blue and White"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Colors to Avoid</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
                value={formData.avoid_colors}
                onChange={(e) => handleInputChange('avoid_colors', e.target.value)}
                placeholder="e.g. Red"
              />
            </div>
            
            <div className="col-span-2">
              <VibeCompetitorInput 
                competitors={competitors}
                onChange={setCompetitors}
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Assets & Inspiration Uploads</label>
              <VibeFileUploader 
                onUploadComplete={handleFileUpload}
                maxFiles={10}
              />
              {uploadedFiles.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {uploadedFiles.map((file, idx) => (
                    <div key={idx} className="bg-gray-50 border border-gray-200 px-3 py-1 rounded text-xs flex items-center">
                      <span className="truncate max-w-[150px]">{file.filename}</span>
                      <span className="ml-2 text-green-500">✓</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        <div className="flex justify-end pt-6 border-t border-gray-100">
          <button
            onClick={handleSubmit}
            disabled={submitting || !formData.business_name || !formData.business_description}
            className="flex items-center px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            {submitting ? (
              <>
                <Loader2 className="animate-spin mr-2" size={20} />
                Submitting...
              </>
            ) : (
              <>
                <Save className="mr-2" size={20} />
                Save & Start Planning
                <ArrowRight className="ml-2" size={20} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

