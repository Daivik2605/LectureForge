'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Upload } from 'lucide-react';
import toast from 'react-hot-toast';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DropZone } from '@/components/upload/DropZone';
import { LanguageSelector } from '@/components/upload/LanguageSelector';
import { SlideSlider } from '@/components/upload/SlideSlider';
import { OptionSwitch } from '@/components/upload/OptionSwitch';
import { uploadPresentation } from '@/lib/api';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState('en');
  const [maxSlides, setMaxSlides] = useState(5);
  const [generateVideo, setGenerateVideo] = useState(true);
  const [generateMcqs, setGenerateMcqs] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [mode, setMode] = useState<'ppt' | 'policy'>('ppt');

  const handleFileSelect = (selected: File) => {
    setFile(selected);
    const extension = selected.name.split('.').pop()?.toLowerCase();
    if (extension === 'pdf' || extension === 'txt') {
      // TODO: Confirm whether PDFs should use mode="pdf" (per-page summaries) or "policy" (chunked).
      setMode('policy');
    } else {
      setMode('ppt');
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      toast.error('Please select a file');
      return;
    }

    setIsUploading(true);

    try {
      const result = await uploadPresentation({
        file,
        language: language as 'en' | 'fr' | 'hi',
        mode,
        maxSlides,
        generateVideo,
        generateMcqs,
      });

      toast.success('Processing started!');
      router.push(`/processing/${result.job_id}`);
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error?.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-6 w-6" />
              Upload Your Presentation
            </CardTitle>
            <CardDescription>
              Upload a PowerPoint file to generate narration, video, and quiz questions.
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* File Drop Zone */}
            <DropZone
              file={file}
              onFileSelect={handleFileSelect}
              onFileRemove={() => setFile(null)}
            />

            {/* Language Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Language</label>
              <LanguageSelector value={language} onChange={setLanguage} />
            </div>

            {/* Max Slides Slider */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Maximum Slides: {maxSlides}
              </label>
              <SlideSlider value={maxSlides} onChange={setMaxSlides} />
            </div>

            {/* Options */}
            <div className="space-y-4">
              <OptionSwitch
                label="Generate Video"
                description="Create a video lecture with TTS narration"
                checked={generateVideo}
                onChange={setGenerateVideo}
              />
              <OptionSwitch
                label="Generate MCQs"
                description="Create multiple-choice quiz questions"
                checked={generateMcqs}
                onChange={setGenerateMcqs}
              />
            </div>

            {/* Submit Button */}
            <Button
              className="w-full"
              size="lg"
              onClick={handleSubmit}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Start Processing
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
