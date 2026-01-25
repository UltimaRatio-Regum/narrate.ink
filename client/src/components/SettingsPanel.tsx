import { Settings, Sliders } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

interface SettingsPanelProps {
  exaggeration: number;
  pauseDuration: number;
  onExaggerationChange: (value: number) => void;
  onPauseDurationChange: (value: number) => void;
}

export function SettingsPanel({
  exaggeration,
  pauseDuration,
  onExaggerationChange,
  onPauseDurationChange,
}: SettingsPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          Generation Settings
        </CardTitle>
        <CardDescription className="mt-1">
          Fine-tune the audio output
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="flex items-center gap-2">
                <Sliders className="h-4 w-4 text-muted-foreground" />
                Emotion Intensity
              </Label>
              <p className="text-xs text-muted-foreground">
                Controls how expressive the voice is
              </p>
            </div>
            <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
              {exaggeration.toFixed(2)}
            </span>
          </div>
          <Slider
            value={[exaggeration]}
            min={0}
            max={1}
            step={0.05}
            onValueChange={([v]) => onExaggerationChange(v)}
            data-testid="slider-exaggeration"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Monotone</span>
            <span>Dramatic</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="flex items-center gap-2">
                <Settings className="h-4 w-4 text-muted-foreground" />
                Pause Between Segments
              </Label>
              <p className="text-xs text-muted-foreground">
                Silence duration between text segments
              </p>
            </div>
            <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
              {pauseDuration}ms
            </span>
          </div>
          <Slider
            value={[pauseDuration]}
            min={0}
            max={3000}
            step={100}
            onValueChange={([v]) => onPauseDurationChange(v)}
            data-testid="slider-pause-duration"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>No pause</span>
            <span>3 seconds</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
