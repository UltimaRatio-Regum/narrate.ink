import { Loader2, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

interface GenerationProgressProps {
  status: "idle" | "processing" | "completed" | "error";
  progress: number;
  currentSegment: number;
  totalSegments: number;
  statusMessage: string;
}

export function GenerationProgress({
  status,
  progress,
  currentSegment,
  totalSegments,
  statusMessage,
}: GenerationProgressProps) {
  if (status === "idle") {
    return null;
  }

  const getStatusIcon = () => {
    switch (status) {
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      default:
        return <Sparkles className="h-5 w-5 text-primary" />;
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case "processing":
        return (
          <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
            Processing
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="secondary" className="bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20">
            Completed
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive">
            Error
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Card className={`transition-all ${
      status === "processing" ? "ring-2 ring-primary/20" : ""
    } ${status === "completed" ? "ring-2 ring-green-500/20" : ""}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="flex items-center gap-2 text-base">
            {getStatusIcon()}
            Audio Generation
          </CardTitle>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground" data-testid="text-status-message">
              {statusMessage}
            </span>
            <span className="font-mono text-xs" data-testid="text-progress-percent">
              {Math.round(progress)}%
            </span>
          </div>
          <Progress value={progress} className="h-2" data-testid="progress-bar" />
        </div>

        {totalSegments > 0 && status === "processing" && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Segment {currentSegment} of {totalSegments}
            </span>
            <span>
              ~{Math.ceil((totalSegments - currentSegment) * 2)} seconds remaining
            </span>
          </div>
        )}

        {status === "processing" && (
          <div className="flex gap-1 justify-center">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-2 h-8 bg-primary/60 rounded-full animate-waveform"
                style={{ animationDelay: `${i * 0.1}s` }}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
