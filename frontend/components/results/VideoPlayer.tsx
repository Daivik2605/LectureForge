'use client';

import { useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { getFileUrl, SlideResult } from '@/lib/api';
import { formatDuration } from '@/lib/utils';

interface VideoPlayerProps {
  videoPath?: string;
  slides: SlideResult[];
}

export function VideoPlayer({ videoPath, slides }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);

  const fallbackVideo = slides.find((slide) => slide.video_path)?.video_path;
  const resolvedVideoPath = videoPath || fallbackVideo;

  if (!resolvedVideoPath) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-muted-foreground">
            Video was not generated for this presentation.
          </p>
        </CardContent>
      </Card>
    );
  }

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (value: number[]) => {
    if (videoRef.current) {
      videoRef.current.currentTime = value[0];
      setCurrentTime(value[0]);
    }
  };

  const handleVolumeChange = (value: number[]) => {
    if (videoRef.current) {
      videoRef.current.volume = value[0];
      setVolume(value[0]);
      setIsMuted(value[0] === 0);
    }
  };

  const handleFullscreen = () => {
    if (videoRef.current) {
      videoRef.current.requestFullscreen();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Video Lecture</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Video Element */}
        <div className="aspect-video bg-black rounded-lg overflow-hidden">
          <video
            ref={videoRef}
            src={getFileUrl(resolvedVideoPath)}
            className="w-full h-full"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={() => setIsPlaying(false)}
          />
        </div>

        {/* Controls */}
        <div className="space-y-2">
          {/* Progress */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground w-12">
              {formatDuration(currentTime)}
            </span>
            <Slider
              value={[currentTime]}
              onValueChange={handleSeek}
              max={duration}
              step={0.1}
              className="flex-1"
            />
            <span className="text-xs text-muted-foreground w-12">
              {formatDuration(duration)}
            </span>
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={togglePlay}>
                {isPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={toggleMute}>
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>
              <div className="w-24">
                <Slider
                  value={[isMuted ? 0 : volume]}
                  onValueChange={handleVolumeChange}
                  max={1}
                  step={0.1}
                />
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={handleFullscreen}>
              <Maximize className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
