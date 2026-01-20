'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getFileUrl, SlideResult } from '@/lib/api';

interface SlideViewerProps {
  slides: SlideResult[];
}

export function SlideViewer({ slides }: SlideViewerProps) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});

  useEffect(() => {
    setSelectedAnswers({});
  }, [currentSlide]);

  if (!slides || slides.length === 0) {
    return <div>No slides generated</div>;
  }

  const slide = slides[currentSlide];
  const slideMcqs = slide?.qa
    ? [
        ...(slide.qa.easy || []),
        ...(slide.qa.medium || []),
        ...(slide.qa.hard || []),
      ]
    : [];

  const handleSelectAnswer = (index: number, option: string) => {
    setSelectedAnswers((prev) => ({ ...prev, [index]: option }));
  };

  const goToPrevious = () =>
    setCurrentSlide((prev) => Math.max(0, prev - 1));

  const goToNext = () =>
    setCurrentSlide((prev) => Math.min(slides.length - 1, prev + 1));

  const playNarration = () => {
    if (slide?.audio_path) {
      const audio = new Audio(getFileUrl(slide.audio_path));
      audio.play();
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Slide {currentSlide + 1}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={goToPrevious}
                disabled={currentSlide === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                {currentSlide + 1} / {slides.length}
              </span>
              <Button
                variant="outline"
                size="icon"
                onClick={goToNext}
                disabled={currentSlide === slides.length - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {slide?.image_path && (
            <div className="aspect-video bg-muted rounded-lg overflow-hidden">
              <img
                src={getFileUrl(slide.image_path)}
                alt={`Slide ${currentSlide + 1}`}
                className="w-full h-full object-contain"
              />
            </div>
          )}

          <div>
            <h4 className="font-medium">Content</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {slide?.text || 'No text content'}
            </p>
          </div>

          {slide?.bullets && slide.bullets.length > 0 ? (
            <div>
              <h4 className="font-medium">Key Points</h4>
              <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
                {slide.bullets.map((bullet, index) => (
                  <li key={index}>{bullet}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div>
              <h4 className="font-medium">Key Points</h4>
              <p className="text-sm text-muted-foreground">No bullet points extracted.</p>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Narration</h4>
              {slide?.audio_path && (
                <Button variant="ghost" size="sm" onClick={playNarration}>
                  <Volume2 className="h-4 w-4 mr-2" />
                  Play Audio
                </Button>
              )}
            </div>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {slide?.narration || 'No narration generated'}
            </p>
          </div>

          <div>
            <h4 className="font-medium">MCQs</h4>
            {slideMcqs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No MCQs generated.</p>
            ) : (
              <div className="space-y-4">
                {slideMcqs.map((mcq, index) => {
                  const selected = selectedAnswers[index];
                  const isCorrect = selected && selected === mcq.answer;
                  return (
                    <div key={index} className="space-y-2">
                      <p className="text-sm font-medium">{mcq.question}</p>
                      <div className="space-y-1">
                        {mcq.options.map((option, optIndex) => (
                          <button
                            key={optIndex}
                            onClick={() => handleSelectAnswer(index, option)}
                            className={`w-full text-left text-sm p-2 rounded border ${
                              selected === option
                                ? isCorrect
                                  ? 'border-green-500 bg-green-500/10'
                                  : 'border-red-500 bg-red-500/10'
                                : 'border-muted'
                            }`}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                      {selected && (
                        <p className="text-xs text-muted-foreground">
                          Correct answer: {mcq.answer}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
