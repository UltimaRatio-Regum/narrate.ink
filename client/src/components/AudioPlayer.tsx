import { useState, useRef, useEffect } from "react";
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";

interface AudioPlayerProps {
  audioUrl: string | null;
  title: string;
  onDownload?: () => void;
}

export function AudioPlayer({ audioUrl, title, onDownload }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    if (audioUrl) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.addEventListener("loadedmetadata", () => {
        setDuration(audioRef.current?.duration || 0);
      });
      audioRef.current.addEventListener("timeupdate", () => {
        setCurrentTime(audioRef.current?.currentTime || 0);
      });
      audioRef.current.addEventListener("ended", () => {
        setIsPlaying(false);
        setCurrentTime(0);
      });
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (value: number[]) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = value[0];
    setCurrentTime(value[0]);
  };

  const skip = (seconds: number) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + seconds));
  };

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (!audioUrl) {
    return (
      <Card className="bg-muted/30">
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">
            <div className="flex items-center justify-center gap-1 mb-3">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-muted-foreground/30 rounded-full"
                  style={{ height: `${12 + Math.random() * 20}px` }}
                />
              ))}
            </div>
            <p className="text-sm">No audio generated yet</p>
            <p className="text-xs mt-1">Generate an audiobook to play it here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex flex-col gap-4">
          {/* Title */}
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-medium truncate" data-testid="text-audio-title">{title}</h3>
            {onDownload && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onDownload}
                data-testid="button-download-audio"
              >
                <Download className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Waveform visualization */}
          <div className="flex items-center justify-center gap-0.5 h-12">
            {[...Array(40)].map((_, i) => (
              <div
                key={i}
                className={`w-1 bg-primary/60 rounded-full transition-all ${
                  isPlaying ? "animate-waveform" : ""
                }`}
                style={{
                  height: `${8 + Math.sin(i * 0.5) * 20 + Math.random() * 10}px`,
                  animationDelay: `${i * 0.05}s`,
                  opacity: i / 40 < currentTime / duration ? 1 : 0.3,
                }}
              />
            ))}
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <Slider
              value={[currentTime]}
              max={duration || 100}
              step={0.1}
              onValueChange={handleSeek}
              className="cursor-pointer"
              data-testid="slider-audio-progress"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span data-testid="text-current-time">{formatTime(currentTime)}</span>
              <span data-testid="text-duration">{formatTime(duration)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between gap-4">
            {/* Volume */}
            <div className="flex items-center gap-2 w-32">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsMuted(!isMuted)}
                data-testid="button-toggle-mute"
              >
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>
              <Slider
                value={[isMuted ? 0 : volume]}
                max={1}
                step={0.01}
                onValueChange={([v]) => {
                  setVolume(v);
                  setIsMuted(false);
                }}
                className="w-20"
                data-testid="slider-volume"
              />
            </div>

            {/* Playback controls */}
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => skip(-10)}
                data-testid="button-skip-back"
              >
                <SkipBack className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                onClick={togglePlay}
                className="h-12 w-12 rounded-full"
                data-testid="button-play-pause"
              >
                {isPlaying ? (
                  <Pause className="h-5 w-5" />
                ) : (
                  <Play className="h-5 w-5 ml-0.5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => skip(10)}
                data-testid="button-skip-forward"
              >
                <SkipForward className="h-4 w-4" />
              </Button>
            </div>

            {/* Spacer */}
            <div className="w-32" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
