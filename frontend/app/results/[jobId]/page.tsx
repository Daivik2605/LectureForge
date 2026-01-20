'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { Download, CheckCircle, Loader2 } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useJobResult } from '@/hooks/useJobResult';
import { SlideViewer } from '@/components/results/SlideViewer';
import { VideoPlayer } from '@/components/results/VideoPlayer';
import { QuizMode } from '@/components/results/QuizMode';
import { DownloadPanel } from '@/components/results/DownloadPanel';

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;
  
  const { result, isLoading, error } = useJobResult(jobId);
  const [activeTab, setActiveTab] = useState('slides');

  if (isLoading) {
    return (
      <div className="container mx-auto py-10 px-4">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="container mx-auto py-10 px-4">
        <Card className="max-w-2xl mx-auto">
          <CardContent className="py-10 text-center">
            <h2 className="text-xl font-semibold mb-2">Failed to Load Results</h2>
            <p className="text-muted-foreground mb-4">{error || 'Results not found'}</p>
            <Button onClick={() => router.push('/upload')}>
              Upload New File
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  Processing Complete
                </CardTitle>
                <CardDescription>
                  {result.filename} • {result.slides.length} slides • {result.language.toUpperCase()}
                  {result.processing_time_seconds && ` • ${Math.round(result.processing_time_seconds)}s`}
                </CardDescription>
              </div>
              <Button variant="outline" className="gap-2">
                <Download className="h-4 w-4" />
                Download All
              </Button>
            </div>
          </CardHeader>
        </Card>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="slides">Slides</TabsTrigger>
            <TabsTrigger value="video">Video</TabsTrigger>
            <TabsTrigger value="quiz">Quiz</TabsTrigger>
            <TabsTrigger value="export">Export</TabsTrigger>
          </TabsList>

          <TabsContent value="slides" className="mt-6">
            <SlideViewer slides={result.slides} />
          </TabsContent>

          <TabsContent value="video" className="mt-6">
            <VideoPlayer
              videoPath={result.final_video_path || result.finalVideoPath}
              slides={result.slides}
            />
          </TabsContent>

          <TabsContent value="quiz" className="mt-6">
            <QuizMode slides={result.slides} />
          </TabsContent>

          <TabsContent value="export" className="mt-6">
            <DownloadPanel result={result} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
