import { useState, useRef } from "react";
import { Mic, Play, Pause, Trash2, Upload, Plus, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { VoiceSample } from "@shared/schema";

interface VoiceSampleManagerProps {
  samples: VoiceSample[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onUpload: (name: string, file: File) => Promise<void>;
  onDelete: (id: string) => void;
}

export function VoiceSampleManager({
  samples,
  selectedId,
  onSelect,
  onUpload,
  onDelete,
}: VoiceSampleManagerProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!selectedFile || !newName.trim()) return;
    
    setIsUploading(true);
    try {
      await onUpload(newName.trim(), selectedFile);
      setIsDialogOpen(false);
      setNewName("");
      setSelectedFile(null);
    } finally {
      setIsUploading(false);
    }
  };

  const togglePlay = (sample: VoiceSample) => {
    if (playingId === sample.id) {
      audioRef.current?.pause();
      setPlayingId(null);
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      audioRef.current = new Audio(sample.audioUrl);
      audioRef.current.onended = () => setPlayingId(null);
      audioRef.current.play();
      setPlayingId(sample.id);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Mic className="h-5 w-5 text-primary" />
              Voice Samples
            </CardTitle>
            <CardDescription className="mt-1">
              Upload audio clips for voice cloning
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" data-testid="button-add-voice">
                <Plus className="h-4 w-4 mr-2" />
                Add Voice
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Voice Sample</DialogTitle>
                <DialogDescription>
                  Upload a 7-20 second audio clip for voice cloning. Clear recordings work best.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="voice-name">Voice Name</Label>
                  <Input
                    id="voice-name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g., Narrator, Character 1"
                    data-testid="input-voice-name"
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Audio File</Label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    className="hidden"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    data-testid="input-voice-file"
                  />
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => fileInputRef.current?.click()}
                    data-testid="button-select-voice-file"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {selectedFile ? selectedFile.name : "Select audio file..."}
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleUpload}
                  disabled={!selectedFile || !newName.trim() || isUploading}
                  data-testid="button-upload-voice"
                >
                  {isUploading ? "Uploading..." : "Upload Voice"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {samples.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Volume2 className="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No voice samples yet</p>
            <p className="text-xs mt-1">Add a voice sample to get started</p>
          </div>
        ) : (
          <ScrollArea className="h-[200px]">
            <div className="space-y-2">
              {samples.map((sample) => (
                <div
                  key={sample.id}
                  className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors hover-elevate ${
                    selectedId === sample.id
                      ? "border-primary bg-primary/5"
                      : "border-transparent bg-muted/50"
                  }`}
                  onClick={() => onSelect(sample.id)}
                  data-testid={`voice-sample-${sample.id}`}
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    className="shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePlay(sample);
                    }}
                    data-testid={`button-play-voice-${sample.id}`}
                  >
                    {playingId === sample.id ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate" data-testid={`text-voice-name-${sample.id}`}>
                      {sample.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDuration(sample.duration)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="shrink-0 text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(sample.id);
                    }}
                    data-testid={`button-delete-voice-${sample.id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
